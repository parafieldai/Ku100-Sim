#include "release.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
int main(int argc,char**argv){
 if(argc<3)return 2;
 ku100::release::Params p;p.rate=std::stoul(argv[2]);
 std::string mode=argv[1];
 if(mode=="linear"){
   p.nonlinear=false;p.unsteady=false;ku100::release::State s(p);s.pressure=80;
   const double initial=s.energy();
   for(unsigned i=0;i<p.rate/500;++i)s.step(0,p.radius);
   std::cout<<std::setprecision(17)<<s.pressure<<' '<<s.flow<<' '<<s.radiation<<' '<<s.energy()+s.loss-initial<<'\n';
 }else{
   if(argc<4)return 2;p.duration=2.0;
   if(mode=="silence")p.displaced_volume=0;
   if(mode=="vented")p.vented=true;
   if(mode=="slow")p.opening_s=.02;
   auto r=ku100::release::simulate(p);
   std::ofstream out(argv[3],std::ios::binary);out.write(reinterpret_cast<const char*>(r.source.data()),r.source.size()*sizeof(double));
   std::cout<<std::setprecision(17)<<r.max_residual<<' '<<r.work<<' '<<r.loss<<' '<<r.energy<<' '<<r.max_pressure<<' '<<r.max_mach<<' '<<r.max_reynolds<<'\n';
 }
}
