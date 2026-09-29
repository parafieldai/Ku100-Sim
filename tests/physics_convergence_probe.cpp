#include "physics.hpp"
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
std::filesystem::path output_path;
void run(const std::string& name,ku100::PhysicsParams p) {
  auto r=ku100::simulate(p);
  std::filesystem::create_directories(output_path);
  std::ofstream f(output_path/(name+".f64"),std::ios::binary);
  for(std::size_t i=0;i<r.local_pressure_left_pa.size();++i) {
    double frame[2]={r.local_pressure_left_pa[i],r.local_pressure_right_pa[i]};
    f.write(reinterpret_cast<const char*>(frame),sizeof(frame));
  }
  auto&s=r.stats;
  std::cout<<std::setprecision(17)<<"{\"name\":\""<<name<<"\",\"rate\":"<<p.sample_rate<<",\"load_n\":"<<p.load_n<<",\"modes_per_plate\":"<<p.modes_per_plate<<",\"duct_cells\":"<<p.duct_cells<<",\"wetness\":"<<p.wetness<<",\"action\":\""<<p.action<<"\",\"side\":\""<<p.side<<"\",\"seed\":"<<p.seed<<",\"frames\":"<<r.local_pressure_left_pa.size()<<",\"energy_residual_j\":"<<s.max_energy_residual_j<<",\"work_j\":"<<s.actuator_work_j<<",\"loss_j\":"<<s.dissipated_energy_j<<",\"remaining_energy_j\":"<<s.final_energy_j<<",\"max_force_n\":"<<s.max_normal_force_n<<",\"force_residual_n\":"<<s.max_contact_solve_residual_n<<",\"max_iterations\":"<<s.max_solver_iterations<<",\"min_mode_hz\":"<<s.min_mode_hz<<",\"max_mode_hz\":"<<s.max_mode_hz<<",\"displacement_thickness_ratio\":"<<s.max_displacement_thickness_ratio<<",\"vent_mach\":"<<s.max_vent_mach<<",\"vent_reynolds\":"<<s.max_vent_reynolds<<",\"duct_mach\":"<<s.max_duct_mach<<",\"duct_reynolds\":"<<s.max_duct_reynolds<<",\"regime_valid\":"<<(s.regime_valid?"true":"false")<<"}\n";
}
int main(int argc,char** argv) {
  if(argc!=2){std::cerr<<"expected output directory\n";return 2;}
  output_path=argv[1];
  ku100::PhysicsParams p;p.duration_s=0.8;const double default_load=p.load_n;
  run("base",p);p.side="right";run("mirror",p);p.side="left";
  p.action="silence";run("silence",p);p.action="stroke";
  p.load_n=0;run("zero-load",p);p.load_n=default_load;
  p.modes_per_plate=64;run("m64",p);p.modes_per_plate=256;run("m256",p);p.modes_per_plate=512;run("m512",p);p.modes_per_plate=1024;run("m1024",p);p.modes_per_plate=128;
  p.sample_rate=96000;run("r96",p);p.sample_rate=384000;run("r384",p);p.sample_rate=192000;
  p.duct_cells=16;run("d16",p);p.duct_cells=64;run("d64",p);p.duct_cells=128;run("d128",p);p.duct_cells=32;
  p.wetness=1;run("wet",p);p.wetness=0;
  p.action="tap";run("tap",p);
}
