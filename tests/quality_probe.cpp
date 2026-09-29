#include "physics.hpp"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
std::filesystem::path directory;
void run(const std::string& name,const ku100::PhysicsParams& p) {
    const auto r=ku100::simulate(p);const auto& s=r.stats;
    std::ofstream f(directory/(name+".f64"),std::ios::binary);
    for(size_t i=0;i<r.local_pressure_left_pa.size();++i) {
        double frame[]={r.local_pressure_left_pa[i],r.local_pressure_right_pa[i]};
        f.write(reinterpret_cast<const char*>(frame),sizeof(frame));
    }
    if(!f)throw std::runtime_error("pressure write failed");
    std::cout<<std::setprecision(17)<<"{\"name\":\""<<name<<"\",\"sample_rate\":"<<p.sample_rate
      <<",\"frames\":"<<r.local_pressure_left_pa.size()<<",\"modes_per_plate\":"<<p.modes_per_plate
      <<",\"unsteady_viscous_losses\":"<<p.unsteady_viscous_losses<<",\"texture_min_wavelength_m\":"<<p.texture_min_wavelength_m
      <<",\"texture_advection_hz\":"<<p.speed_m_s/p.texture_min_wavelength_m<<",\"highest_mode_hz\":"<<s.max_mode_hz
      <<",\"work_j\":"<<s.actuator_work_j<<",\"loss_j\":"<<s.dissipated_energy_j<<",\"energy_j\":"<<s.final_energy_j
      <<",\"max_residual_j\":"<<s.max_energy_residual_j<<",\"regime_valid\":"<<(s.regime_valid?"true":"false")<<"}\n"<<std::flush;
}
int main(int argc,char**argv){try {
    if(argc!=2)throw std::runtime_error("Expected output directory");
    directory=argv[1];std::filesystem::create_directories(directory);
    ku100::PhysicsParams p;p.duration_s=.8;p.trace_stride=1920;
    run("legacy128",p);p.unsteady_viscous_losses=1;run("viscous128",p);
    p.side="right";run("mirror",p);p.side="left";p.action="silence";run("silence",p);p.action="stroke";
    p.modes_per_plate=256;run("viscous256",p);p.modes_per_plate=512;run("viscous512",p);
    p.modes_per_plate=256;p.texture_min_wavelength_m=1e-5;run("fine256",p);
    p.modes_per_plate=512;run("fine512",p);p.modes_per_plate=1024;run("fine1024",p);
    p.modes_per_plate=512;p.sample_rate=384000;run("fine512-r384",p);
    p.texture_min_wavelength_m=120e-6;p.modes_per_plate=128;run("viscous128-r384",p);
    return 0;
} catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 2;}}
