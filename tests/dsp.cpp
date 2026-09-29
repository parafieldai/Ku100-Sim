#define main inherited_cli_main
#include "../src/sim.cpp"
#undef main
// Independent invariants on native components, separate from CLI channel mirroring.
void expect(bool ok,const char*name){if(!ok)throw std::runtime_error(name);std::cout<<"PASS "<<name<<"\n";}
int main(){
 try {
  V x={0,1,-2,.5},h={1,.5};V y=convolve(x,h);
  expect(y==V({0,1,-1.5,-.5,.25}),"known full convolution tail");
  V impulse(100);impulse[0]=1;auto dy=decimate(impulse,8);
  expect(std::max_element(dy.begin(),dy.end())-dy.begin()==48,"1 ms causal decimator latency");
  Config c;c.modes=2;c.seconds=.03;c.oversample=8;Model left(c);c.side=1;Model right(c);
  double diff=0,scale=0;
  for(int i=0;i<15000;i++){auto l=left.step(i*left.dt),r=right.step(i*right.dt);diff=std::max(diff,std::abs(l[0]-r[1]));scale=std::max(scale,std::abs(l[0]));}
  expect(diff/std::max(scale,1e-15)<1e-9,"independently actuated physical side symmetry");
  expect(left.max_residual<1e-15,"moving patch work included in energy identity");
  for(double a:{-1e-5,0.,1e-5})for(double b:{-2e-5,0.,3e-5}){
   double delta=left.gradient(a,b)*(a-b)-(left.potential(a)-left.potential(b));
   expect(std::abs(delta)<1e-20,"discrete contact gradient identity");
  }
  std::cout<<"13 native invariants passed\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
