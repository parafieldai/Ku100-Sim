// SPDX-License-Identifier: MIT
#include "release.hpp"
#include "receiver.hpp"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <string>
namespace fs=std::filesystem;
int main(int argc,char** argv){try {
    std::map<std::string,std::string> a;
    for(int i=1;i<argc;i+=2)if(i+1>=argc||!a.emplace(argv[i],argv[i+1]).second)throw std::invalid_argument("unique --key value pairs required");
    auto take=[&](std::string k,std::string fallback){auto it=a.find(k);if(it==a.end())return fallback;auto v=it->second;a.erase(it);return v;};
    auto num=[&](std::string k,double& x){auto it=a.find(k);if(it!=a.end()){size_t end;double v=std::stod(it->second,&end);if(end!=it->second.size()||!std::isfinite(v))throw std::invalid_argument("invalid number");x=v;a.erase(it);}};
    ku100::release::Params p; double rate=p.rate,gain=1,azimuth=90;
    num("--rate",rate);if(rate!=std::floor(rate)||rate<48000||rate>768000)throw std::invalid_argument("invalid rate");p.rate=unsigned(rate);
    num("--duration",p.duration);num("--volume",p.volume);num("--radius",p.radius);num("--length",p.length);
    num("--opening",p.opening_s);num("--displacement",p.displaced_volume);num("--period",p.period);num("--gain",gain);num("--azimuth",azimuth);
    auto control=take("--control","sealed");if(control!="sealed"&&control!="vented")throw std::invalid_argument("unknown control");p.vented=control=="vented";
    auto out=fs::path(take("--out","outputs/release")),bankpath=fs::path(take("--bank","data/ku100_bank.bin"));
    if(!a.empty()||gain<0||gain>100)throw std::invalid_argument("unsupported parameter");
    ku100::release::validate(p);ku100::decimation_delay_s(p.rate);
    if(fs::exists(out))throw std::invalid_argument("refusing to overwrite output");
    const auto bank=ku100::HrirBank::load(bankpath.string());bank.at(azimuth,.25);
    const auto result=ku100::release::simulate(p);
    auto src=ku100::decimate(result.source,p.rate);auto stereo=ku100::render_airborne(src,bank,azimuth,.25);
    for(auto*channel:{&stereo.left,&stereo.right})for(auto&x:*channel)x*=gain;
    const fs::path tmp=out.string()+".partial";if(fs::exists(tmp))throw std::invalid_argument("partial output exists");fs::create_directories(tmp);
    ku100::write_float_wav((tmp/"audio.wav").string(),stereo,48000);
    ku100::write_float_wav((tmp/"source-mono-duplicated.wav").string(),{src,src},48000);
    std::ofstream tr(tmp/"trace.csv");tr<<std::setprecision(17)<<"time_s,pocket_pressure_pa,flow_m3_s,opening_radius_m,displaced_volume_m3,free_field_025m_pa,energy_j,work_j,loss_j\n";
    for(const auto&r:result.trace)tr<<r.t<<','<<r.p<<','<<r.q<<','<<r.opening<<','<<r.volume<<','<<r.source<<','<<r.energy<<','<<r.work<<','<<r.loss<<'\n';
    std::ofstream j(tmp/"native.json");j<<std::setprecision(17)<<"{\"schema\":\"release-source-probe/1\",\"rate\":"<<p.rate<<",\"duration\":"<<p.duration<<",\"volume_m3\":"<<p.volume<<",\"neck_radius_m\":"<<p.radius<<",\"neck_length_m\":"<<p.length<<",\"opening_s\":"<<p.opening_s<<",\"displaced_volume_m3\":"<<p.displaced_volume<<",\"period_s\":"<<p.period<<",\"vented\":"<<(p.vented?"true":"false")<<",\"gain_per_pa\":"<<gain<<",\"azimuth_deg\":"<<azimuth<<",\"distance_m\":0.25,\"work_j\":"<<result.work<<",\"loss_j\":"<<result.loss<<",\"final_energy_j\":"<<result.energy<<",\"max_energy_residual_j\":"<<result.max_residual<<",\"max_pressure_pa\":"<<result.max_pressure<<",\"peak_aperture_mach\":"<<result.max_mach<<",\"peak_aperture_reynolds\":"<<result.max_reynolds<<",\"source_to_audio_latency_s\":"<<ku100::decimation_delay_s(p.rate)+31./48000+.25/343<<",\"wet_contact_calibrated\":false,\"source_mechanism_identified_in_target\":false,\"radiation\":\"equivalent sphere; fixed neck plus variable resistive aperture\"}\n";
    tr.close();j.close();if(!tr||!j)throw std::runtime_error("write failed");fs::rename(tmp,out);std::cout<<out<<'\n';
}catch(const std::exception&e){std::cerr<<"ERROR: "<<e.what()<<'\n';return 2;}}
