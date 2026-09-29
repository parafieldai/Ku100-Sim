// SPDX-License-Identifier: MIT
// Bounded, energy-accounted contact surrogate. NOT a calibrated KU100 digital twin.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <stdexcept>
#include <sstream>
#include <string>
#include <vector>
namespace fs = std::filesystem;
constexpr double pi=3.14159265358979323846;
using V=std::vector<double>; using A3=std::array<double,3>;
struct Config {
 double seconds=2, coupling=1, viscosity=.002, depth_um=40, speed=.02, roughness_um=2, initial_velocity=0, force=0, filter_gain=1;
 int modes=6, oversample=8, side=0; std::string action="stroke", receiver="contact", filter="", out="outputs/run";
};
double dot(const V&a,const V&b){return std::inner_product(a.begin(),a.end(),b.begin(),0.);}
A3 solve3(std::array<A3,3> a,A3 b){
 for(int k=0;k<3;k++){int p=k; for(int i=k+1;i<3;i++)if(std::abs(a[i][k])>std::abs(a[p][k]))p=i;
  if(std::abs(a[p][k])<1e-30){throw std::runtime_error("singular system");}
  std::swap(a[k],a[p]);std::swap(b[k],b[p]);
  for(int i=k+1;i<3;i++){double f=a[i][k]/a[k][k];for(int j=k;j<3;j++)a[i][j]-=f*a[k][j];b[i]-=f*b[k];}}
 A3 x{};for(int i=2;i>=0;i--){double s=b[i];for(int j=i+1;j<3;j++)s-=a[i][j]*x[j];x[i]=s/a[i][i];}return x;
}
struct Model {
 // Assumed test-coupon geometry and materials, SI units. These are not device measurements.
 const double lx=.03, ly=.04, thick=.001, young=1.2e6, nu=.49, rho_s=1100, rho=1.204, c=343;
 const double cavity_volume=1e-6, vent_radius=.0015, vent_length=.01, air_mu=1.81e-5, radiation_radius=.0015;
 const double indenter_k=(4./3.)*50000*std::sqrt(.005), film_floor=.0001, film_radius=.001;
 const double patch_sigma=.0015, loss_ratio=.04;
 int n; double dt,C,Mv,Rv,Rr,tau,vent_denom,vent_hcoef,energy0=0,work=0,loss=0,max_residual=0,max_force=0,max_q=0,max_pressure=0,max_film_re=0;
 double loss_solid=0,loss_film=0,loss_vent=0,loss_radiation=0;
 V mass,k,d,q,v,s,al,ar,invD,u0,u1,u2; std::array<A3,3> mat{}; A3 statep{},stateu{},stateh{}; Config cfg;
 Model(Config c0):n(2*c0.modes*c0.modes),dt(1./(48000*c0.oversample)),cfg(c0){
  C=cavity_volume/(rho*c*c); Mv=rho*vent_length/(pi*vent_radius*vent_radius);
  Rv=8*air_mu*vent_length/(pi*std::pow(vent_radius,4)); Rr=rho*c/(4*pi*radiation_radius*radiation_radius);tau=radiation_radius/c;
  vent_hcoef=(2*tau/dt)/(1+2*tau/dt);vent_denom=2*Mv/dt+Rv+Rr*vent_hcoef;
  for(V* z:{&mass,&k,&d,&q,&v,&s,&al,&ar,&invD,&u0,&u1,&u2})z->resize(n);
  const double D=young*std::pow(thick,3)/(12*(1-nu*nu));
  for(int ear=0;ear<2;ear++)for(int m=1;m<=cfg.modes;m++)for(int l=1;l<=cfg.modes;l++){
   int i=ear*cfg.modes*cfg.modes+(m-1)*cfg.modes+l-1;double kk=std::pow(m*pi/lx,2)+std::pow(l*pi/ly,2);
   mass[i]=rho_s*thick*lx*ly/4;k[i]=mass[i]*D*kk*kk/(rho_s*thick);d[i]=2*loss_ratio*std::sqrt(k[i]*mass[i]);
   double area=(m%2&&l%2)?4*lx*ly/(m*l*pi*pi):0; s[i]=(ear==0?1:-1)*area/(lx*ly);(ear==0?al:ar)[i]=area;
   invD[i]=1/(2*mass[i]/dt+d[i]+k[i]*dt/2);u0[i]=-cfg.coupling*s[i]*invD[i];u1[i]=-al[i]*invD[i];u2[i]=-ar[i]*invD[i];
  }
  const V* us[]={&u0,&u1,&u2};
  for(int j=0;j<3;j++){mat[0][j]=(j==0?1.:0)-dt/2*dot(s,*us[j]);mat[1][j]=(j==1?2*C/dt+1/vent_denom:0)-dot(al,*us[j]);mat[2][j]=(j==2?2*C/dt+1/vent_denom:0)-dot(ar,*us[j]);}
  v[0]=cfg.initial_velocity;energy0=energy();
 }
 double energy()const{double e=0;for(int i=0;i<n;i++)e+=(mass[i]*v[i]*v[i]+k[i]*q[i]*q[i])/2;e+=cfg.coupling*std::pow(dot(s,q),2)/2;
  for(int eidx=0;eidx<2;eidx++){e+=(C*statep[eidx]*statep[eidx]+Mv*stateu[eidx]*stateu[eidx]+Rr*tau*stateh[eidx]*stateh[eidx])/2;}
  return e;}
 static double positive(double x){return std::max(x,0.);}
 double potential(double delta)const{return indenter_k*std::pow(positive(delta),2.5)/2.5;}
 double gradient(double a,double b)const{double scale=std::max({std::abs(a),std::abs(b),1e-12});if(std::abs(a-b)<1e-7*scale)return indenter_k*std::pow(positive((a+b)/2),1.5);return (potential(a)-potential(b))/(a-b);}
 double envelope(double t)const{if(t<=0||t>=cfg.seconds)return 0;double ramp=std::min(.15,cfg.seconds/4);double x=std::min({1.,t/ramp,(cfg.seconds-t)/ramp});return x*x*x*(10+x*(-15+6*x));}
 std::pair<double,double> actuator(double t)const{
  double env=envelope(t),span=.006,rate=cfg.speed/(2*pi*span),x=lx/2+env*span*std::sin(2*pi*rate*t);
  if(cfg.action!="stroke")x=lx/2;
  double dep=cfg.depth_um*1e-6;
  if(cfg.action=="tap")dep*=std::pow(std::max(0.,std::sin(2*pi*2*t)),6);
  double tex=cfg.roughness_um*1e-6*(.6*std::sin(2*pi*x/.0007)+.3*std::sin(2*pi*x/.000113)+.1*std::sin(2*pi*x/.000037));
  if(cfg.action!="stroke")tex=0;
  return {x,env*(dep+20e-6+tex)-20e-6};
 }
 V shape(double x)const{V g(n,0);for(int m=1;m<=cfg.modes;m++)for(int l=1;l<=cfg.modes;l++){
  int i=cfg.side*cfg.modes*cfg.modes+(m-1)*cfg.modes+l-1;double kx=m*pi/lx,ky=l*pi/ly;
  g[i]=std::sin(kx*x)*std::sin(ky*ly*.47)*std::exp(-.5*patch_sigma*patch_sigma*(kx*kx+ky*ky));}return g;}
 // One step. A Schur complement solves all linear mechanical/acoustic couplings.
 // Hertz contact uses the discrete potential gradient, not a corrective energy clamp.
 std::array<double,7> step(double t){
  auto a0=actuator(t),a1=actuator(t+dt);V g0=shape(a0.first),g1=shape(a1.first),g(n),z(n),r(n),vb(n),vf(n);
  for(int i=0;i<n;i++){g[i]=(g0[i]+g1[i])/2;z[i]=(2*mass[i]*v[i]/dt-k[i]*q[i])*invD[i];r[i]=g[i]*invD[i];}
  double uc[2];for(int e=0;e<2;e++)uc[e]=(2*Mv*stateu[e]/dt+Rr*vent_hcoef*stateh[e])/vent_denom;
  A3 b={dot(s,q)+dt/2*dot(s,z),2*C*statep[0]/dt-uc[0]+dot(al,z),2*C*statep[1]/dt-uc[1]+dot(ar,z)};
  A3 bf={dt/2*dot(s,r),dot(al,r),dot(ar,r)},ab=solve3(mat,b),af=solve3(mat,bf);
  for(int i=0;i<n;i++){vb[i]=z[i]+u0[i]*ab[0]+u1[i]*ab[1]+u2[i]*ab[2];vf[i]=r[i]+u0[i]*af[0]+u1[i]*af[1]+u2[i]*af[2];}
  double de0=a0.second-dot(g0,q),aa=a1.second-dot(g1,q)-dt*dot(g1,vb),bb=dt*dot(g1,vf),F=0;
  double gap=film_floor+positive(-de0),cf=3*pi*cfg.viscosity*std::pow(film_radius,4)/(2*std::pow(gap,3));
  bool contact=cfg.action!="linear"&&cfg.action!="silence";
  if(contact){
   auto residual=[&](double f){double de1=aa-bb*f;return f-gradient(de1,de0)-cf*positive((de1-de0)/dt);};
   double lo=0,hi=std::max(.001,2*(gradient(aa,de0)+cf*positive((aa-de0)/dt)));
   int iter=0;while(residual(hi)<0&&iter++<30)hi*=2;
   if(residual(hi)<0||!std::isfinite(hi))throw std::runtime_error("contact root bracket failed");
   for(int j=0;j<48;j++){double mid=(lo+hi)/2;if(residual(mid)>0)hi=mid;else lo=mid;} F=(lo+hi)/2;
   if(gradient(aa,de0)==0&&cf*positive((aa-de0)/dt)==0)F=0;
  }else if(cfg.action=="linear")F=cfg.force;
  V vm(n),qnew(n);for(int i=0;i<n;i++){vm[i]=vb[i]+vf[i]*F;qnew[i]=q[i]+dt*vm[i];}
  double de1=a1.second-dot(g1,qnew),drive_delta=a1.second-a0.second;
  for(int i=0;i<n;i++)drive_delta-=(qnew[i]+q[i])/2*(g1[i]-g0[i]);
  if(contact)work+=F*drive_delta;else work+=F*dt*dot(g,vm);
  double lsolid=0;for(int i=0;i<n;i++)lsolid+=dt*d[i]*vm[i]*vm[i];
  double lfilm=contact?cf*positive((de1-de0)/dt)*(de1-de0):0,lvent=0,lrad=0;
  for(int e=0;e<2;e++){
   double pm=ab[e+1]+af[e+1]*F,um=pm/vent_denom+uc[e],hm=(2*tau*stateh[e]/dt+um)/(1+2*tau/dt);
   lvent+=dt*Rv*um*um;lrad+=dt*Rr*std::pow(um-hm,2);
   statep[e]=2*pm-statep[e];stateu[e]=2*um-stateu[e];stateh[e]=2*hm-stateh[e];
  }
  for(int i=0;i<n;i++){q[i]=qnew[i];v[i]=2*vm[i]-v[i];max_q=std::max(max_q,std::abs(q[i]));}
  loss_solid+=lsolid;loss_film+=lfilm;loss_vent+=lvent;loss_radiation+=lrad;loss+=lsolid+lfilm+lvent+lrad;
  double en=energy()+(contact?potential(de1):0);
  max_residual=std::max(max_residual,std::abs(en-energy0+loss-work));max_force=std::max(max_force,F);
  max_pressure=std::max({max_pressure,std::abs(statep[0]),std::abs(statep[1])});
  if(cfg.viscosity>0&&contact)max_film_re=std::max(max_film_re,1000*film_radius*positive((de1-de0)/dt)/(2*cfg.viscosity));
  double radiated=Rr*(stateu[cfg.side]-stateh[cfg.side])*radiation_radius/.25;
  return {statep[0],statep[1],radiated,F,en,a1.first,de1};
 }
};
// Explicit little-endian IEEE Float32 WAV. Never limit, normalize, or alter channel balance.
void u16(std::ostream&o,uint16_t x){char b[2]={char(x),char(x>>8)};o.write(b,2);}void u32(std::ostream&o,uint32_t x){char b[4]={char(x),char(x>>8),char(x>>16),char(x>>24)};o.write(b,4);}
void wav(const fs::path&p,const V&l,const V&r){if(l.size()!=r.size())throw std::runtime_error("channel length mismatch");std::ofstream o(p,std::ios::binary);uint32_t n=uint32_t(l.size()*8);o.write("RIFF",4);u32(o,n+36);o.write("WAVEfmt ",8);u32(o,16);u16(o,3);u16(o,2);u32(o,48000);u32(o,48000*8);u16(o,8);u16(o,32);o.write("data",4);u32(o,n);
 for(size_t i=0;i<l.size();i++){for(double x:{l[i],r[i]}){float f=float(x);if(!std::isfinite(x)||!std::isfinite(f))throw std::runtime_error("nonfinite audio");uint32_t b;std::memcpy(&b,&f,4);u32(o,b);}}
 if(!o)throw std::runtime_error("WAV write failed");}
V decimate(const V&x,int os){int taps=96*os+1;V h(taps);double sum=0;for(int j=0;j<taps;j++){double z=j-(taps-1)/2.,fc=21000./(48000*os);double sinc=z==0?2*fc:std::sin(2*pi*fc*z)/(pi*z);double w=.42-.5*std::cos(2*pi*j/(taps-1))+.08*std::cos(4*pi*j/(taps-1));h[j]=sinc*w;sum+=h[j];}for(auto&z:h)z/=sum;
 V y((x.size()+taps-2)/os+1);for(size_t n=0;n<y.size();n++){size_t at=n*os;for(int j=0;j<taps;j++)if(at>=size_t(j)&&at-j<x.size())y[n]+=h[j]*x[at-j];}return y;}
V convolve(const V&x,const V&h){V y(x.size()+h.size()-1);for(size_t i=0;i<x.size();i++)for(size_t j=0;j<h.size();j++)y[i+j]+=x[i]*h[j];return y;}
Config parse(int argc,char**argv){Config c;std::map<std::string,std::string>a;for(int i=1;i<argc;i+=2){if(i+1>=argc)throw std::runtime_error("arguments require --key value pairs");std::string k=argv[i];if(a.count(k))throw std::runtime_error("duplicate argument: "+k);a[k]=argv[i+1];}
 auto num=[&](const std::string&k,double&v,double lo,double hi){auto it=a.find(k);if(it==a.end())return;size_t used=0;double x=std::stod(it->second,&used);if(used!=it->second.size()||!std::isfinite(x)||x<lo||x>hi)throw std::runtime_error("invalid "+k);v=x;a.erase(it);};
 num("--seconds",c.seconds,.01,15);num("--coupling",c.coupling,0,1000);num("--viscosity",c.viscosity,0,.1);num("--depth-um",c.depth_um,0,200);num("--speed",c.speed,0,.08);num("--roughness-um",c.roughness_um,0,10);num("--initial-velocity",c.initial_velocity,-.01,.01);num("--force",c.force,-.1,.1);num("--filter-gain",c.filter_gain,0,10);
 double n=c.modes,os=c.oversample;num("--modes",n,1,24);num("--oversample",os,4,512);if(n!=std::floor(n)||(os!=4&&os!=8&&os!=16&&os!=32&&os!=64&&os!=128&&os!=256&&os!=512))throw std::runtime_error("invalid grid or oversample");c.modes=int(n);c.oversample=int(os);
 auto str=[&](const std::string&k,std::string&v){auto it=a.find(k);if(it!=a.end()){v=it->second;a.erase(it);}};
 str("--action",c.action);str("--receiver",c.receiver);str("--filter",c.filter);str("--out",c.out);std::string side="left";str("--side",side);if(side!="left"&&side!="right")throw std::runtime_error("invalid side");c.side=side=="right";
 if(c.action!="stroke"&&c.action!="press"&&c.action!="tap"&&c.action!="silence"&&c.action!="linear")throw std::runtime_error("invalid action");
 if(c.receiver!="contact"&&c.receiver!="measured"&&c.receiver!="sphere"){throw std::runtime_error("invalid receiver");}
 if(c.receiver!="contact"&&c.filter.empty()){throw std::runtime_error("receiver requires verified --filter");}
 if(!a.empty()){throw std::runtime_error("unknown argument: "+a.begin()->first);}
 return c;
}
int main(int argc,char**argv){try{
 if(argc==2&&std::string(argv[1])=="--help"){std::cout<<"KU100 research renderer: --out DIR --seconds 2 --action stroke|press|tap|silence|linear --side left|right --receiver contact|measured|sphere --filter FIR.txt --modes 6 --oversample 8\n";return 0;}
 Config c=parse(argc,argv);
 // Bound allocations and computation before starting a potentially expensive offline job.
 double proposed_steps=std::ceil((c.seconds+.2)*48000*c.oversample);
 if(proposed_steps>16000000 || proposed_steps*2*c.modes*c.modes>1000000000.)
  throw std::runtime_error("requested resolution exceeds this CLI resource budget; split the scene or reduce resolution");
 if(c.receiver=="contact"&&(!c.filter.empty()||c.filter_gain!=1))
  throw std::runtime_error("contact receiver does not accept an airborne filter or filter gain");
 fs::path out=c.out,tmp=c.out+".partial";if(fs::exists(out)||fs::exists(tmp))throw std::runtime_error("output already exists; use a new directory");
 V hl,hr;if(c.receiver!="contact"){std::ifstream f(c.filter);std::string line;while(std::getline(f,line)){if(line.empty()||line[0]=='#')continue;std::istringstream s(line);double l,r;std::string extra;if(!(s>>l>>r)||(s>>extra)||!std::isfinite(l)||!std::isfinite(r))throw std::runtime_error("invalid filter row");hl.push_back(l*c.filter_gain);hr.push_back(r*c.filter_gain);if(hl.size()>8192)throw std::runtime_error("filter too long");}if(hl.empty())throw std::runtime_error("filter missing or empty");}
 Config internal=c;internal.side=0;Model m(internal);int fsin=48000*c.oversample;size_t steps=size_t(std::llround((c.seconds+.2)*fsin));V l(steps),r(steps),rad(steps);std::vector<std::array<double,9>>trace;
 for(size_t i=0;i<steps;i++){auto s=m.step(double(i)/fsin);l[i]=s[c.side?1:0];r[i]=s[c.side?0:1];rad[i]=s[2];if(i%size_t(fsin/120)==0)trace.push_back({(i+1.)/fsin,l[i],r[i],s[3],s[4],m.work,m.loss,s[5],s[6]});}
 V dl,dr;if(c.receiver=="contact"){dl=decimate(l,c.oversample);dr=decimate(r,c.oversample);}else{V src=decimate(rad,c.oversample);dl=convolve(src,hl);dr=convolve(src,hr);}
 fs::create_directories(tmp);wav(tmp/"audio.wav",dl,dr);std::ofstream tr(tmp/"trace.csv");tr<<std::setprecision(17)<<"time_s,left_pa,right_pa,force_n,energy_j,work_j,loss_j,x_m,indentation_m\n";for(auto&a:trace){for(size_t i=0;i<a.size();i++)tr<<(i?",":"")<<a[i];tr<<"\n";}tr.close();
 double rmsl=std::sqrt(dot(dl,dl)/dl.size()),rmsr=std::sqrt(dot(dr,dr)/dr.size()),peak=0;for(auto*x:{&dl,&dr})for(double z:*x)peak=std::max(peak,std::abs(z));
 std::ofstream j(tmp/"manifest.json");j<<std::setprecision(17)<<"{\n\"schema\":1,\"engine\":\"contact-coupon-cpp\",\"calibrated_ku100_contact\":false,\"sample_rate\":48000,\"internal_sample_rate\":"<<fsin<<",\"frames\":"<<dl.size()<<",\"seconds\":"<<c.seconds<<",\"action\":\""<<c.action<<"\",\"receiver\":\""<<c.receiver<<"\",\"side\":\""<<(c.side?"right":"left")<<"\",\"modes_per_ear\":"<<c.modes*c.modes<<",\"coupling_n_per_m\":"<<c.coupling<<",\"viscosity_pa_s\":"<<c.viscosity<<",\"depth_um\":"<<c.depth_um<<",\"speed_m_per_s\":"<<c.speed<<",\"roughness_um\":"<<c.roughness_um<<",\"filter_gain\":"<<c.filter_gain<<",\"fir_latency_s\":0.001,\"initial_energy_j\":"<<m.energy0<<",\"work_j\":"<<m.work<<",\"loss_j\":"<<m.loss<<",\"final_energy_j\":"<<m.energy()<<",\"max_energy_residual_j\":"<<m.max_residual<<",\"relative_energy_residual\":"<<m.max_residual/std::max(m.energy0+std::abs(m.work),1e-18)<<",\"max_force_n\":"<<m.max_force<<",\"max_modal_displacement_m\":"<<m.max_q<<",\"max_pressure_pa\":"<<m.max_pressure<<",\"max_film_reynolds\":"<<m.max_film_re<<",\"solid_loss_j\":"<<m.loss_solid<<",\"film_loss_j\":"<<m.loss_film<<",\"vent_loss_j\":"<<m.loss_vent<<",\"radiation_loss_j\":"<<m.loss_radiation<<",\"rms\":["<<rmsl<<","<<rmsr<<"],\"peak\":"<<peak<<",\"units\":\""<<(c.receiver=="contact"?"Pa at modeled cavities":"relative acoustic receiver units")<<"\",\"final_state\":[";
 bool first=true;auto emit=[&](double x){j<<(first?"":",")<<x;first=false;};for(const V*vec:{&m.q,&m.v}){for(int e=0;e<2;e++){int internalear=c.side?1-e:e;for(int i=0;i<m.n/2;i++)emit((*vec)[internalear*m.n/2+i]);}}for(int e=0;e<2;e++)emit(m.statep[c.side?1-e:e]);for(int e=0;e<2;e++)emit(m.stateu[c.side?1-e:e]);for(int e=0;e<2;e++)emit(m.stateh[c.side?1-e:e]);j<<"]\n}\n";j.close();if(!j||!tr)throw std::runtime_error("report write failed");fs::rename(tmp,out);std::cout<<out.string()<<"\n";return 0;
 }catch(const std::exception&e){std::cerr<<"ERROR: "<<e.what()<<"\n";return 2;}}
