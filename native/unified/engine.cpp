// SPDX-License-Identifier: MIT
// Shared SI-coordinate mechanical graph; no object names or sound presets here.
#include <algorithm>
#include <cmath>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>
using V = std::vector<double>;
static thread_local std::string last_error;
struct Engine {
    int n, ne, frame=0; double h, work=0, loss=0, initial=0, residual_max=0;
    // Per-node: mass, k2, k4, viscous, memory_k, tau, drive_k, unilateral, q0, v0, limit.
    V p, K, q, v, r, u, f, linear_maps, edges, er;
    bool exact;
    Engine(int count,int rate,const double* params,const double* matrix,const double* drives,
           const double* forces,const double* maps,bool is_exact,int edge_count,const double* edge_params)
      : n(count), ne(edge_count), h(1./rate), p(params,params+11*count), K(matrix,matrix+count*count),
        q(count),v(count),r(count,0),u(drives,drives+count),f(forces,forces+count),exact(is_exact) {
        if(n<1 || n>32 || rate<96000 || rate>1536000) throw std::runtime_error("Invalid native dimensions");
        for(int i=0;i<n;i++){q[i]=P(i,8);v[i]=P(i,9);}
        if(ne<0 || ne>128 || (ne>0 && !edge_params) || (ne>0 && exact)) throw std::runtime_error("Invalid interaction graph");
        if(ne) edges.assign(edge_params,edge_params+10*ne);
        er.assign(ne,0.);
        for(int e=0;e<ne;e++) {
            for(int c=0;c<10;c++) if(!std::isfinite(E(e,c))) throw std::runtime_error("Nonfinite interaction parameter");
            int a=int(E(e,0)),b=int(E(e,1));
            if(E(e,0)!=a || E(e,1)!=b || a<0 || b<0 || a>=n || b>=n || a==b || std::abs(E(e,2))!=1
               || E(e,3)<0 || E(e,4)<0 || E(e,5)<0 || E(e,6)<0 || E(e,7)<=0
               || (E(e,9)!=0 && E(e,9)!=1)) throw std::runtime_error("Invalid interaction coefficients");
            if(E(e,9) && (E(e,4)!=0 || E(e,5)!=0 || E(e,6)!=0)) throw std::runtime_error("Contact supports elastic normal penalty only");
        }
        if(exact) linear_maps.assign(maps,maps+64*n); // four 4x4 transitions per node
        initial=energy(q,v,r,u);
    }
    double P(int i,int j)const{return p[i*11+j];}
    // Edge: node_a, node_b, normal sign, k2, k4, damping, memory_k, tau, gap, unilateral.
    double E(int e,int c)const{return edges[e*10+c];}
    double strain(int e,const V& x)const{return E(e,2)*(x[int(E(e,0))]-x[int(E(e,1))])-E(e,8);}
    void edge_gradient(int e,double a,double b,double& g,double& dg)const {
        if(E(e,9)){contact(a,b,E(e,3),true,g,dg);return;}
        double delta=a-b,den=1+h/(2*E(e,7));
        g=.5*E(e,3)*(a+b)+.25*E(e,4)*(a+b)*(a*a+b*b)+E(e,5)*delta/h+E(e,6)*(er[e]+delta/2)/den;
        dg=.5*E(e,3)+.25*E(e,4)*(3*a*a+2*a*b+b*b)+E(e,5)/h+E(e,6)/(2*den);
    }
    static double pos(double x){return std::max(x,0.);}
    double energy(const V& a,const V& b,const V& c,const V& d)const{
        double e=0;
        for(int i=0;i<n;i++){
            const double k=P(i,1), k4=P(i,2), delta=P(i,7)?pos(d[i]-a[i]):d[i]-a[i];
            e+=.5*P(i,0)*b[i]*b[i]+.5*k*a[i]*a[i]+.25*k4*std::pow(a[i],4)
               +.5*P(i,4)*c[i]*c[i]+.5*P(i,6)*delta*delta;
            if(k<0) e+=k*k/(4*k4); // reference at zero-energy well minima
            for(int j=0;j<n;j++)e+=.5*a[i]*K[i*n+j]*a[j];
        }
        for(int edge=0;edge<ne;edge++) {
            const double z=E(edge,9)?pos(strain(edge,a)):strain(edge,a);
            e+=.5*E(edge,3)*z*z+.25*E(edge,4)*z*z*z*z+.5*E(edge,6)*er[edge]*er[edge];
        }
        return e;
    }
    // Discrete potential gradient and derivative with respect to the NEW gap.
    static void contact(double a,double b,double k,bool unilateral,double& g,double& dg){
        if(!unilateral || (a>=0 && b>=0)){g=k*(a+b)/2;dg=k/2;return;}
        if(a<=0 && b<=0){g=dg=0;return;}
        const double diff=a-b, pa=pos(a), pb=pos(b);
        g=.5*k*(pa*pa-pb*pb)/diff;
        dg=(k*pa-g)/diff;
    }
    void solve(V& A,V& rhs)const{
        // SPD Cholesky; monotonic-step and coupling checks precede construction.
        for(int i=0;i<n;i++)for(int j=0;j<=i;j++){
            double x=A[i*n+j];for(int k=0;k<j;k++)x-=A[i*n+k]*A[j*n+k];
            if(i==j){if(!(x>0) || !std::isfinite(x))throw std::runtime_error("Nonpositive step Jacobian"); A[i*n+j]=std::sqrt(x);}
            else A[i*n+j]=x/A[j*n+j];
        }
        for(int i=0;i<n;i++){for(int j=0;j<i;j++)rhs[i]-=A[i*n+j]*rhs[j];rhs[i]/=A[i*n+i];}
        for(int i=n-1;i>=0;i--){for(int j=i+1;j<n;j++)rhs[i]-=A[j*n+i]*rhs[j];rhs[i]/=A[i*n+i];}
    }
    void step(const double* next_u,const double* next_f,double* out){
        V un(next_u,next_u+n),fn(next_f,next_f+n),qn(n),vn(n),rn(n);
        for(int i=0;i<n;i++)if(!std::isfinite(un[i]) || !std::isfinite(fn[i]))throw std::runtime_error("Nonfinite control");
        if(exact){
            // Exact first-order-hold transition for uncoupled linear nodes;
            // selected by graph structure, NEVER by an object/material name.
            const double roots[3]={.5-std::sqrt(15.)/10,.5,.5+std::sqrt(15.)/10};
            const double weights[3]={5./18,4./9,5./18};
            for(int i=0;i<n;i++){
                const double old_force=P(i,6)*u[i]+f[i], new_force=P(i,6)*un[i]+fn[i];
                double z[4]={q[i],v[i],old_force,(new_force-old_force)/h};
                for(int s=0;s<4;s++){
                    const double* T=&linear_maps[i*64+s*16];double a=0,b=0;
                    for(int j=0;j<4;j++){a+=T[j]*z[j];b+=T[4+j]*z[j];}
                    if(s==0){qn[i]=a;vn[i]=b;rn[i]=0;}
                    else {
                        const double t=roots[s-1],uu=u[i]+t*(un[i]-u[i]),ff=f[i]+t*(fn[i]-f[i]);
                        work+=h*weights[s-1]*(ff*b+P(i,6)*(uu-a)*(un[i]-u[i])/h);
                        loss+=h*weights[s-1]*P(i,3)*b*b;
                    }
                }
            }
        }else{
            V dq(n),res(n),J(n*n);double max_res=0;
            for(int i=0;i<n;i++)dq[i]=h*v[i];
            bool converged=false;
            for(int it=0;it<24;it++){
                max_res=0;
                for(int i=0;i<n;i++){
                    const double a=q[i]+dq[i],b=q[i], k=P(i,1),k4=P(i,2);
                    double gc,dc;contact(un[i]-a,u[i]-b,P(i,6),P(i,7)!=0,gc,dc);
                    const double den=1+h/(2*P(i,5));
                    res[i]=2*P(i,0)*(dq[i]/h-v[i])/h+P(i,3)*dq[i]/h
                        +.5*k*(a+b)+.25*k4*(a+b)*(a*a+b*b)
                        +P(i,4)*(r[i]+dq[i]/2)/den-gc-(fn[i]+f[i])/2;
                    for(int j=0;j<n;j++){res[i]+=K[i*n+j]*(q[j]+dq[j]/2);J[i*n+j]=K[i*n+j]/2;}
                    J[i*n+i]+=2*P(i,0)/(h*h)+P(i,3)/h+.5*k
                        +.25*k4*(3*a*a+2*a*b+b*b)+P(i,4)/(2*den)+dc;
                }
                // All internal interactions apply equal/opposite generalized forces.
                // They enter this SAME Newton system, not a post-render audio layer.
                for(int e=0;e<ne;e++) {
                    int a=int(E(e,0)),b=int(E(e,1));double sign=E(e,2),g,dg;
                    const double oldz=strain(e,q),newz=oldz+sign*(dq[a]-dq[b]);
                    edge_gradient(e,newz,oldz,g,dg);
                    res[a]+=sign*g;res[b]-=sign*g;
                    J[a*n+a]+=dg;J[b*n+b]+=dg;J[a*n+b]-=dg;J[b*n+a]-=dg;
                }
                for(double value:res) max_res=std::max(max_res,std::abs(value));
                if(max_res<1e-11){converged=true;break;}
                for(auto& x:res)x=-x;
                solve(J,res);
                for(int i=0;i<n;i++)dq[i]+=res[i];
            }
            if(!converged)throw std::runtime_error("Nonlinear step failed its fixed force residual tolerance");
            for(int i=0;i<n;i++){
                const double midv=dq[i]/h,den=1+h/(2*P(i,5));
                const double midr=(r[i]+dq[i]/2)/den;
                qn[i]=q[i]+dq[i];vn[i]=2*midv-v[i];rn[i]=2*midr-r[i];
                double gc,dc;contact(un[i]-qn[i],u[i]-q[i],P(i,6),P(i,7)!=0,gc,dc);
                work+=(fn[i]+f[i])/2*dq[i]+gc*(un[i]-u[i]);
                loss+=h*(P(i,3)*midv*midv+P(i,4)/P(i,5)*midr*midr);
            }
        }
        for(int e=0;e<ne;e++) {
            const double dz=strain(e,qn)-strain(e,q),den=1+h/(2*E(e,7));
            const double midr=(er[e]+dz/2)/den;
            if(!E(e,9)) {
                er[e]=2*midr-er[e];
                loss+=h*(E(e,5)*(dz/h)*(dz/h)+E(e,6)/E(e,7)*midr*midr);
            }
        }
        for(int i=0;i<n;i++)if(!std::isfinite(qn[i]) || !std::isfinite(vn[i]) || std::abs(qn[i])>P(i,10))
            throw std::runtime_error("State exceeds declared coordinate domain");
        q=qn;v=vn;r=rn;u=un;f=fn;frame++;
        const double e=energy(q,v,r,u),balance=e-initial+loss-work;
        if(!std::isfinite(e) || !std::isfinite(balance))throw std::runtime_error("Nonfinite energy");
        residual_max=std::max(residual_max,std::abs(balance));
        for(int i=0;i<n;i++){out[i]=q[i];out[n+i]=v[i];out[2*n+i]=r[i];}
        for(int edge=0;edge<ne;edge++)out[3*n+edge]=er[edge];
        out[3*n+ne]=e;out[3*n+ne+1]=work;out[3*n+ne+2]=loss;out[3*n+ne+3]=balance;
    }
};
extern "C" {
const char* unified_error(){return last_error.c_str();}
void* unified_create(int n,int rate,const double* p,const double* K,const double* u,const double* f,const double* maps,int exact,int ne,const double* edges){
    try {if(n<1 || n>32 || rate<96000 || rate>1536000 || !p || !K || !u || !f || !maps)throw std::runtime_error("Invalid native constructor"); return new Engine(n,rate,p,K,u,f,maps,exact!=0,ne,edges);}catch(const std::exception& e){last_error=e.what();return nullptr;}
}
int unified_process(void* handle,int count,const double* u,const double* f,double* output){
    if(!handle || count<0 || count>65536){last_error="Invalid process request";return 1;}
    try{auto& e=*static_cast<Engine*>(handle);for(int t=0;t<count;t++)e.step(u+t*e.n,f+t*e.n,output+t*(3*e.n+e.ne+4));return 0;}
    catch(const std::exception& e){last_error=e.what();return 1;}
}
void unified_destroy(void* handle){delete static_cast<Engine*>(handle);}
}
