// SPDX-License-Identifier: MIT
// Shared tetrahedral finite-strain solids + compliant, driven sphere contacts.
// No material/object names, source recording, sampled noise or audio file I/O.
#include <array>
#include <vector>
#include <cmath>
#include <algorithm>
#include <stdexcept>
#include <string>
using V=std::array<double,3>; using M=std::array<double,9>;
static thread_local std::string error;
static V add(V a,V b){for(int j=0;j<3;j++)a[j]+=b[j];return a;}
static V sub(V a,V b){for(int j=0;j<3;j++)a[j]-=b[j];return a;}
static V mul(V a,double s){for(double&x:a)x*=s;return a;}
static double dot(V a,V b){double x=0;for(int j=0;j<3;j++)x+=a[j]*b[j];return x;}
static double norm(V a){return std::sqrt(dot(a,a));}
static M trans(M a){return {a[0],a[3],a[6],a[1],a[4],a[7],a[2],a[5],a[8]};}
static M mm(M a,M b){M o{};for(int i=0;i<3;i++)for(int j=0;j<3;j++)for(int k=0;k<3;k++)o[3*i+j]+=a[3*i+k]*b[3*k+j];return o;}
static M columns(V a,V b,V c){return {a[0],b[0],c[0],a[1],b[1],c[1],a[2],b[2],c[2]};}
static double det(M a){return a[0]*(a[4]*a[8]-a[5]*a[7])-a[1]*(a[3]*a[8]-a[5]*a[6])+a[2]*(a[3]*a[7]-a[4]*a[6]);}
static M inverse(M a){double d=det(a);if(std::abs(d)<1e-25)throw std::runtime_error("Singular deformation");M b{a[4]*a[8]-a[5]*a[7],a[2]*a[7]-a[1]*a[8],a[1]*a[5]-a[2]*a[4],a[5]*a[6]-a[3]*a[8],a[0]*a[8]-a[2]*a[6],a[2]*a[3]-a[0]*a[5],a[3]*a[7]-a[4]*a[6],a[1]*a[6]-a[0]*a[7],a[0]*a[4]-a[1]*a[3]};for(double&x:b)x/=d;return b;}
static double sq(M a){double s=0;for(double x:a)s+=x*x;return s;}
static M dev(M a){double t=(a[0]+a[4]+a[8])/3;for(int j=0;j<3;j++)a[4*j]-=t;return a;}
static M green(M F){M e=mm(trans(F),F);for(int j=0;j<3;j++)e[4*j]-=1;for(double&x:e)x*=.5;return dev(e);}
// parameters: mu, bulk, objective shear viscosity, objective bulk viscosity,
//            memory_mu_1,tau_1,memory_mu_2,tau_2
static double stress(M F,M Fdot,const double* p,M A1,M A2,M& P,double& rate){
 double J=det(F);if(!std::isfinite(J)||J<.45||J>1.55)throw std::runtime_error("Element outside declared positive-volume range");
 M inv=inverse(F),it=trans(inv);double i1=sq(F),jpow=std::pow(J,-2./3.);
 double energy=.5*p[0]*(jpow*i1-3)+.5*p[1]*(J-1)*(J-1);
 for(int k=0;k<9;k++)P[k]=p[0]*jpow*(F[k]-i1/3*it[k])+p[1]*J*(J-1)*it[k];
 M L=mm(Fdot,inv),D{};for(int i=0;i<3;i++)for(int j=0;j<3;j++)D[3*i+j]=.5*(L[3*i+j]+L[3*j+i]);
 double tr=D[0]+D[4]+D[8];D=dev(D);M visc=D;for(double&x:visc)x*=2*p[2];for(int j=0;j<3;j++)visc[4*j]+=p[3]*tr;
 visc=mm(visc,it);for(int k=0;k<9;k++)P[k]+=J*visc[k];
 rate=J*(2*p[2]*sq(D)+p[3]*tr*tr);
 M E=green(F);
 for(int arm=0;arm<2;arm++){
  M r=E,A=arm?A2:A1;for(int k=0;k<9;k++)r[k]-=A[k];double mu=p[4+2*arm],tau=p[5+2*arm];
  energy+=mu*sq(r);rate+=2*mu/tau*sq(r);M pr=mm(F,r);for(int k=0;k<9;k++)P[k]+=2*mu*pr[k];
 }
 return energy;
}
struct Tet{std::array<int,4> id;M inv;double vol;M A[2]{};};
struct QP{std::array<int,3> ids;V bary;double area;};
struct Actor{V x{},v{},a{},target{},targetv{};std::array<double,10> p;};
struct Engine{
 int n,na;double h,time=0,work=0,loss=0,initial=0,energy_now=0,minJ=1,maxJ=1;std::array<double,8> mat;bool averaged_volume;
 std::vector<V>x,v,acc,rest,force;std::vector<double>mass,area,cnorm;std::vector<int>fixed;std::vector<Tet>tets;std::vector<Actor>actors;
 std::vector<QP> points;std::vector<V>bristle;std::vector<double>loads,slips;double contact_energy=0,volume=0,maxpenetration=0;
 Engine(int N,int T,int NA,double dt,const double* X,const int* ti,const int* fix,const double* surf,const double* parameters,double rho,const double* actorp,const double* initial_targets,int nf,const int* faces,bool avol)
  :n(N),na(NA),h(dt),averaged_volume(avol),x(N),v(N),acc(N),rest(N),force(N),mass(N),area(surf,surf+N),fixed(fix,fix+N),actors(NA),loads(NA),slips(NA){
  if(n<4||n>3000||T<1||T>12000||na<1||na>8||h<=0||h>1./24000)throw std::runtime_error("Invalid native solid dimensions");
  std::copy(parameters,parameters+8,mat.begin());
  for(int i=0;i<n;i++)for(int d=0;d<3;d++)x[i][d]=rest[i][d]=X[3*i+d];
  for(int j=0;j<T;j++){Tet t;for(int d=0;d<4;d++){t.id[d]=ti[4*j+d];if(t.id[d]<0||t.id[d]>=n)throw std::runtime_error("Invalid tet index");}M dm=columns(sub(x[t.id[1]],x[t.id[0]]),sub(x[t.id[2]],x[t.id[0]]),sub(x[t.id[3]],x[t.id[0]]));t.vol=det(dm)/6;if(t.vol<=0)throw std::runtime_error("Inverted reference tet");t.inv=inverse(dm);for(int id:t.id)mass[id]+=rho*t.vol/4;tets.push_back(t);volume+=t.vol;}
  for(int j=0;j<nf;j++){
   std::array<int,3> ids{faces[3*j],faces[3*j+1],faces[3*j+2]};
   for(int i:ids)if(i<0||i>=n)throw std::runtime_error("Bad surface triangle");
   V a=sub(x[ids[1]],x[ids[0]]),b=sub(x[ids[2]],x[ids[0]]);
   double A=.5*std::sqrt(std::max(0.,dot(a,a)*dot(b,b)-dot(a,b)*dot(a,b)));
   for(int k=0;k<3;k++){V bary{1./6,1./6,1./6};bary[k]=2./3;points.push_back({ids,bary,A/3});}
  }
  bristle.resize(points.size()*na);
  for(double m:mass)if(m<=0)throw std::runtime_error("Unconnected vertex");
  for(int a=0;a<na;a++){std::copy(actorp+10*a,actorp+10*a+10,actors[a].p.begin());for(int d=0;d<3;d++)actors[a].x[d]=actors[a].target[d]=initial_targets[3*a+d];}
  evaluate(0);initial=energy_now;
 }
 M gradient(const std::vector<V>& values,const Tet&t)const{return mm(columns(sub(values[t.id[1]],values[t.id[0]]),sub(values[t.id[2]],values[t.id[0]]),sub(values[t.id[3]],values[t.id[0]])),t.inv);}
 void evaluate(double advance){
  for(V&f:force){f={0,0,0};}
  for(double&l:loads){l=0;}
  for(double&s:slips){s=0;}
  std::vector<V>reaction(na);double potential=0,lossrate=0,drvpower=0,fricloss=0;contact_energy=0;minJ=1e30;maxJ=0;maxpenetration=0;
  // Energy-derived average nodal volume method, single homogeneous material.
  // The nodal pressure is a mechanical constraint, NOT microphone pressure.
  std::vector<double> nodal0(n,0.),nodalV(n,0.),pressure(n,0.);
  std::vector<M> Fs;Fs.reserve(tets.size());
  for(auto&t:tets){M F=gradient(x,t);Fs.push_back(F);if(averaged_volume)for(int id:t.id){nodal0[id]+=t.vol/4;nodalV[id]+=t.vol*det(F)/4;}}
  if(averaged_volume)for(int i=0;i<n;i++){double j=nodalV[i]/nodal0[i];pressure[i]=mat[1]*(j-1);potential+=.5*mat[1]*nodal0[i]*(j-1)*(j-1);}
  size_t ti=0;
  for(auto&t:tets){M F=Fs[ti++],Fd=gradient(v,t),P{};double J=det(F);minJ=std::min(minJ,J);maxJ=std::max(maxJ,J);
   M E=green(F);if(advance>0)for(int arm=0;arm<2;arm++){double g=1-std::exp(-advance/mat[5+2*arm]);for(int k=0;k<9;k++)t.A[arm][k]+=g*(E[k]-t.A[arm][k]);}
   double rate;auto local=mat;if(averaged_volume)local[1]=0.;
   potential+=t.vol*stress(F,Fd,local.data(),t.A[0],t.A[1],P,rate);lossrate+=t.vol*rate;
   if(averaged_volume){double avg=0;for(int id:t.id)avg+=pressure[id]/4;M it=trans(inverse(F));for(int k=0;k<9;k++)P[k]+=avg*J*it[k];}
   M H=mm(P,trans(t.inv));V fsum{};for(int d=0;d<3;d++){V f{-t.vol*H[d],-t.vol*H[3+d],-t.vol*H[6+d]};force[t.id[d+1]]=add(force[t.id[d+1]],f);fsum=add(fsum,f);}force[t.id[0]]=sub(force[t.id[0]],fsum);
  }
  for(int a=0;a<na;a++){
   Actor&act=actors[a];const auto&p=act.p;
   // m,R,kdrive,cdrive,kn_per_area,cn_per_area,kt_per_area,mu_s,mu_d,v_stribeck
   for(size_t i=0;i<points.size();i++){
    const QP&cp=points[i];V cx{},cv{};for(int k=0;k<3;k++){cx=add(cx,mul(x[cp.ids[k]],cp.bary[k]));cv=add(cv,mul(v[cp.ids[k]],cp.bary[k]));}
    V d=sub(cx,act.x);double r=norm(d),delta=p[1]-r;V &z=bristle[a*points.size()+i];double kt=p[6]*cp.area,oldZ=.5*kt*dot(z,z);
    if(delta<=0){if(advance>0){fricloss+=oldZ;z={0,0,0};}continue;}
    if(r<1e-7)throw std::runtime_error("Contact reached fingertip center");
    V normal=mul(d,1/r),rv=sub(cv,act.v);double vn=dot(rv,normal);V vt=sub(rv,mul(normal,vn));
    double kn=p[4]*cp.area,cn=p[5]*cp.area;double fn=kn*delta+cn*std::max(-vn,0.);
    loads[a]+=fn;lossrate+=cn*std::pow(std::min(vn,0.),2);contact_energy+=.5*kn*delta*delta;maxpenetration=std::max(maxpenetration,delta);
    z=sub(z,mul(normal,dot(z,normal)));if(advance>0)z=add(z,mul(vt,advance));
    // Stribeck weakening is a constitutive PRIOR, not a fitted skin measurement.
    double speed=norm(vt),mu=p[8]+(p[7]-p[8])*std::exp(-std::pow(speed/p[9],2));double bound=mu*kn*delta;
    double trial=kt*norm(z);if(trial>bound&&trial>0){z=mul(z,bound/trial);slips[a]+=cp.area;}
    V tang=mul(z,-kt);V f=add(mul(normal,fn),tang);for(int k=0;k<3;k++){force[cp.ids[k]]=add(force[cp.ids[k]],mul(f,cp.bary[k]));}reaction[a]=sub(reaction[a],f);
    double zenergy=.5*kt*dot(z,z);contact_energy+=zenergy;
    if(advance>0){double removed=-dot(tang,vt)*advance-(zenergy-oldZ);if(removed<-1e-10)throw std::runtime_error("Nonpassive bristle update");fricloss+=std::max(0.,removed);}
   }
   V dx=sub(act.target,act.x),dv=sub(act.targetv,act.v),drive=add(mul(dx,p[2]),mul(dv,p[3]));
   potential+=.5*p[2]*dot(dx,dx);lossrate+=p[3]*dot(dv,dv);drvpower+=dot(drive,act.targetv);
   act.a=mul(add(drive,reaction[a]),1/p[0]);
  }
  double kinetic=0;for(int i=0;i<n;i++){if(fixed[i]){v[i]={0,0,0};acc[i]={0,0,0};}else acc[i]=mul(force[i],1/mass[i]);kinetic+=.5*mass[i]*dot(v[i],v[i]);}
  for(auto&a:actors)kinetic+=.5*a.p[0]*dot(a.v,a.v);
  energy_now=kinetic+potential+contact_energy;
  if(advance>0){work+=advance*drvpower;loss+=advance*lossrate+fricloss;}
 }
 void step(const double* target,const double* targetv){
  for(int i=0;i<n;i++)if(!fixed[i]){v[i]=add(v[i],mul(acc[i],.5*h));x[i]=add(x[i],mul(v[i],h));}
  for(int a=0;a<na;a++){auto&f=actors[a];f.v=add(f.v,mul(f.a,.5*h));f.x=add(f.x,mul(f.v,h));for(int d=0;d<3;d++){f.target[d]=target[3*a+d];f.targetv[d]=targetv[3*a+d];}}
  evaluate(h);
  // energy_now above uses half-step velocities; correct kinetic energy after kick.
  for(int i=0;i<n;i++)if(!fixed[i]){double old=dot(v[i],v[i]);v[i]=add(v[i],mul(acc[i],.5*h));energy_now+=.5*mass[i]*(dot(v[i],v[i])-old);if(norm(sub(x[i],rest[i]))>.03)throw std::runtime_error("Displacement outside scene range");}
  for(auto&a:actors){double old=dot(a.v,a.v);a.v=add(a.v,mul(a.a,.5*h));energy_now+=.5*a.p[0]*(dot(a.v,a.v)-old);}
  time+=h;
 }
};
extern "C" {
const char* solid_error(){return error.c_str();}
void* solid_create(int n,int nt,int na,double dt,const double*x,const int*t,const int*fixed,const double*area,const double*mat,double rho,const double*actor,const double*targets,int nf,const int*faces,int averaged){try{return new Engine(n,nt,na,dt,x,t,fixed,area,mat,rho,actor,targets,nf,faces,averaged!=0);}catch(const std::exception&e){error=e.what();return nullptr;}}
void solid_destroy(void*p){delete static_cast<Engine*>(p);}
// output: positions/velocities for all nodes+actors, forces+slip areas, energy/work/loss/balance,minJ,maxJ,maxpen
int solid_process(void*p,int frames,const double*targets,const double*velocities,double*out){try{auto&e=*static_cast<Engine*>(p);int d=6*(e.n+e.na)+2*e.na+7;for(int k=0;k<frames;k++){
 e.step(targets+3*e.na*k,velocities+3*e.na*k);double*r=out+d*k;int at=0;for(int i=0;i<e.n;i++)for(double x:e.x[i])r[at++]=x;for(auto&a:e.actors)for(double x:a.x)r[at++]=x;for(int i=0;i<e.n;i++)for(double v:e.v[i])r[at++]=v;for(auto&a:e.actors)for(double v:a.v)r[at++]=v;for(double x:e.loads)r[at++]=x;for(double x:e.slips)r[at++]=x;
 r[at++]=e.energy_now;r[at++]=e.work;r[at++]=e.loss;r[at++]=e.energy_now-e.initial+e.loss-e.work;r[at++]=e.minJ;r[at++]=e.maxJ;r[at++]=e.maxpenetration;
 }return 0;}catch(const std::exception&e){error=e.what();return 1;}}
// Pure material probe for independent gradient/objectivity/unit tests.
int solid_material(const double*f,const double*fd,const double*p,double*out){try{M F{},Fd{},P{};std::copy(f,f+9,F.begin());std::copy(fd,fd+9,Fd.begin());double rate;double e=stress(F,Fd,p,M{},M{},P,rate);out[0]=e;out[1]=rate;std::copy(P.begin(),P.end(),out+2);return 0;}catch(const std::exception&e){error=e.what();return 1;}}
// Pure volume-energy probe: dE/dJ_e = V_e times averaged nodal pressure.
int solid_volume_probe(int n,int nt,const int*ids,const double*vol,const double*J,double bulk,double*out){try{
 if(n<4||nt<1||bulk<0)throw std::runtime_error("Bad volume probe");
 std::vector<double> v0(n,0.),v(n,0.),p(n,0.);out[0]=0;
 for(int e=0;e<nt;e++)for(int j=0;j<4;j++){int id=ids[4*e+j];if(id<0||id>=n||vol[e]<=0)throw std::runtime_error("Bad volume connectivity");v0[id]+=vol[e]/4;v[id]+=vol[e]*J[e]/4;}
 for(int i=0;i<n;i++){if(v0[i]<=0)throw std::runtime_error("Disconnected volume node");double r=v[i]/v0[i]-1;p[i]=bulk*r;out[0]+=.5*bulk*v0[i]*r*r;}
 for(int e=0;e<nt;e++){double avg=0;for(int j=0;j<4;j++)avg+=p[ids[4*e+j]]/4;out[e+1]=vol[e]*avg;}
 return 0;}catch(const std::exception&e){error=e.what();return 1;}}

}
