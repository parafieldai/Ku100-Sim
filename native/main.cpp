#include "physics.hpp"
#include "receiver.hpp"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>

namespace fs=std::filesystem;
namespace {
std::string quote(const std::string& s) {
    std::ostringstream o; o << '"';
    for(unsigned char c:s) {
        if(c=='"' || c=='\\') o << '\\' << c;
        else if(c=='\n') o << "\\n";
        else if(c=='\r') o << "\\r";
        else if(c=='\t') o << "\\t";
        else if(c<32) o << "\\u" << std::hex << std::setw(4) << std::setfill('0') << unsigned(c) << std::dec;
        else o << c;
    }
    o << '"'; return o.str();
}
double number(const std::string& s) {
    std::size_t used=0; const double d=std::stod(s,&used);
    if(used!=s.size() || !std::isfinite(d)) throw std::invalid_argument("expected finite numeric value");
    return d;
}
unsigned integer(const std::string& s) {
    const double d=number(s);
    if(d<0 || d>std::numeric_limits<unsigned>::max() || d!=std::floor(d)) throw std::invalid_argument("expected unsigned integer");
    return static_cast<unsigned>(d);
}
std::map<std::string,std::string> arguments(int argc,char** argv) {
    std::map<std::string,std::string> result;
    for(int i=1;i<argc;++i) {
        const std::string k=argv[i];
        if(k=="--help" || k=="--describe") {
            if(!result.emplace(k,"1").second) throw std::invalid_argument("duplicate option: "+k);
        } else {
            if(k.rfind("--",0)!=0 || i+1>=argc) throw std::invalid_argument("every option requires a value: "+k);
            if(!result.emplace(k,argv[++i]).second) throw std::invalid_argument("duplicate option: "+k);
        }
    }
    return result;
}
std::string take(std::map<std::string,std::string>& args,const std::string& key,const std::string& fallback) {
    auto it=args.find(key); if(it==args.end()) return fallback;
    auto value=it->second;args.erase(it);return value;
}
void field(std::map<std::string,std::string>& a,const char* key,double& value) {
    auto it=a.find(key);if(it!=a.end()){value=number(it->second);a.erase(it);}
}
void field(std::map<std::string,std::string>& a,const char* key,unsigned& value) {
    auto it=a.find(key);if(it!=a.end()){value=integer(it->second);a.erase(it);}
}
#define PHYS_DOUBLE_FIELDS(X) \
 X(duration_s) X(load_n) X(speed_m_s) X(wetness) X(contact_radius_m) X(roughness_rms_m) \
 X(plate_width_m) X(plate_height_m) X(plate_thickness_m) X(young_modulus_pa) X(poisson_ratio) \
 X(density_kg_m3) X(modal_loss_ratio) X(cavity_volume_m3) X(duct_length_m) X(duct_radius_m) \
 X(vent_length_m) X(vent_radius_m) X(contact_stiffness_n_m15) X(contact_damping_n_s_m) \
 X(friction_coefficient) X(friction_velocity_m_s) X(film_thickness_m) X(film_viscosity_pa_s) \
 X(air_density_kg_m3) X(sound_speed_m_s) X(air_viscosity_pa_s) \
 X(texture_min_wavelength_m) X(texture_max_wavelength_m) X(texture_amplitude_exponent)
std::string flag(std::string s) {std::replace(s.begin(),s.end(),'_','-');return "--"+s;}
void describe() {
    const ku100::PhysicsParams p;
    std::cout << std::setprecision(17) << "{\"version\":\"ku100-native/1\",\"physics_defaults\":{";
    bool first=true;
#define SHOW(name) if(!first)std::cout<<',';first=false;std::cout<<quote(#name)<<':'<<p.name;
    PHYS_DOUBLE_FIELDS(SHOW)
#undef SHOW
    std::cout << ",\"sample_rate\":" << p.sample_rate << ",\"modes_per_plate\":" << p.modes_per_plate
              << ",\"unsteady_viscous_losses\":" << p.unsteady_viscous_losses
              << ",\"seed\":" << p.seed << ",\"trace_stride\":" << p.trace_stride << ",\"duct_cells\":" << p.duct_cells
              << ",\"action\":" << quote(p.action) << ",\"side\":" << quote(p.side)
              << "},\"output_sample_rate_hz\":48000,\"receiver_modes\":[\"contact\",\"airborne\"]}\n";
}
void write_json(const fs::path& path,const std::string& content) {
    std::ofstream out(path);out<<content<<'\n';if(!out)throw std::runtime_error("cannot write "+path.string());
}
void equal_length(ku100::StereoSignal& s) {
    const auto n=std::max(s.left.size(),s.right.size());s.left.resize(n,0);s.right.resize(n,0);
}
}  // namespace

int main(int argc,char** argv) {
    try {
        auto args=arguments(argc,argv);
        if(args.count("--help")) {
            std::cout << "KU100 native physical research renderer\n"
                         "--describe  print complete SI-valued physics defaults\n"
                         "--out DIR --receiver contact|airborne [--bank FILE] [--azimuth-deg 90] [--distance-m .25]\n"
                         "--action stroke|press|tap|silence --side left|right --duration-s 4 --load-n .01\n"
                         "All physics defaults also accept --hyphen-separated-field-name VALUE.\n"
                         "Native mechanics/DSP only; no reference waveform input or playback.\n";
            return 0;
        }
        if(args.count("--describe")){if(args.size()!=1)throw std::invalid_argument("--describe cannot be combined with rendering");describe();return 0;}
        ku100::PhysicsParams p;
#define SET(name) field(args,flag(#name).c_str(),p.name);
        PHYS_DOUBLE_FIELDS(SET)
#undef SET
        field(args,"--sample-rate",p.sample_rate);field(args,"--modes-per-plate",p.modes_per_plate);
        field(args,"--unsteady-viscous-losses",p.unsteady_viscous_losses);
        field(args,"--trace-stride",p.trace_stride);field(args,"--duct-cells",p.duct_cells);
        const auto seed=take(args,"--seed",std::to_string(p.seed));
        p.seed=integer(seed); // exact browser-safe, portable 32-bit texture identity
        p.action=take(args,"--action",p.action);p.side=take(args,"--side",p.side);
        const auto out_path=fs::path(take(args,"--out","outputs/native-render"));
        const auto receiver=take(args,"--receiver","contact");
        const auto bank_path=take(args,"--bank","data/ku100_bank.bin");
        const double azimuth=number(take(args,"--azimuth-deg",p.side=="left"?"90":"270"));
        const double distance=number(take(args,"--distance-m","0.25"));
        const double sensitivity_mv_pa=number(take(args,"--sensitivity-mv-pa","20"));
        // One declared scalar is shared by both ears; no signal-dependent gain.
        const double preamp_db=number(take(args,"--preamp-gain-db","20"));
        const double full_scale_v=number(take(args,"--adc-full-scale-v","2"));
        if(!args.empty())throw std::invalid_argument("unknown option: "+args.begin()->first);
        if(receiver!="contact" && receiver!="airborne")throw std::invalid_argument("receiver must be contact or airborne");
        if(sensitivity_mv_pa<=0 || sensitivity_mv_pa>1000 || preamp_db<-120 || preamp_db>100 || full_scale_v<=0 || full_scale_v>100)
            throw std::invalid_argument("capture settings exceed supported physical/electrical ranges");
        ku100::validate_physics_params(p);
        ku100::decimation_delay_s(p.sample_rate);
        ku100::HrirBank bank;
        if(receiver=="airborne") {bank=ku100::HrirBank::load(bank_path);bank.at(azimuth,distance);}
        if(fs::exists(out_path) && !fs::is_empty(out_path))throw std::invalid_argument("output directory is not empty; refusing to overwrite an earlier render");
        fs::create_directories(out_path);
        const auto result=ku100::simulate(p);
        auto local=ku100::StereoSignal{ku100::decimate(result.local_pressure_left_pa,p.sample_rate),ku100::decimate(result.local_pressure_right_pa,p.sample_rate)};
        auto source=ku100::StereoSignal{ku100::decimate(result.airborne_pressure_left_at_025m_pa,p.sample_rate),ku100::decimate(result.airborne_pressure_right_at_025m_pa,p.sample_rate)};
        equal_length(local);equal_length(source);
        ku100::StereoSignal audio=local;
        if(receiver=="airborne") {
            // A single observed vent is the source. We do not collapse two
            // spatially separated sources into an unvalidated compact source.
            const auto& primary=p.side=="left"?source.left:source.right;
            audio=ku100::render_airborne(primary,bank,azimuth,distance,p.sound_speed_m_s);
        }
        const double gain=(sensitivity_mv_pa*1e-3)*std::pow(10.0,preamp_db/20.0)/full_scale_v;
        for(auto* channel:{&audio.left,&audio.right})for(double& x:*channel)x*=gain;
        ku100::write_float_wav((out_path/"render.wav").string(),audio,48000);
        ku100::write_float_wav((out_path/"cavity-pressure.wav").string(),local,48000);
        ku100::write_float_wav((out_path/"airborne-source.wav").string(),source,48000);
        std::ofstream trace(out_path/"trace.csv");
        trace << "time_s,normal_force_n,friction_force_n,indentation_m,cavity_left_pa,cavity_right_pa,stored_energy_j,input_work_j,dissipated_energy_j,balance_error_j,sliding_distance_m\n" << std::setprecision(17);
        for(const auto& t:result.trace) {
            trace << t.time_s << ',' << t.normal_force_n << ',' << t.tangential_force_n << ',' << t.indentation_m << ','
                  << t.local_pressure_left_pa << ',' << t.local_pressure_right_pa << ','
                  << t.stored_energy_j << ',' << t.actuator_work_j << ',' << t.dissipated_energy_j << ',' << t.energy_residual_j
                  << ',' << t.sliding_distance_m << '\n';
        }
        if(!trace)throw std::runtime_error("trace write failed");
        const auto& s=result.stats;
        std::ostringstream metadata; metadata << std::setprecision(17);
        metadata << "{\"version\":\"ku100-native/1\",\"renderer\":\"native-cpp-physics\",\"sample_rate_hz\":48000"
                 << ",\"integration_rate_hz\":" << p.sample_rate << ",\"frames\":" << audio.left.size()
                 << ",\"simulation_first_sample_s\":" << 1.0/p.sample_rate
                 << ",\"receiver\":" << quote(receiver) << ",\"absolute_device_calibration\":false"
                 << ",\"source_observation\":" << quote(receiver=="airborne"?"selected-vent monopole at measured source position":"generic bilateral cavity pressures")
                 << ",\"decimation_latency_s\":" << ku100::decimation_delay_s(p.sample_rate)
                 << ",\"fractional_delay_latency_s\":" << (receiver=="airborne"?31.0/48000:0)
                 << ",\"modeled_propagation_delay_s\":" << (receiver=="airborne"?distance/p.sound_speed_m_s:0)
                 << ",\"published_hrir_time_origin_preserved\":" << (receiver=="airborne"?"true":"false")
                 << ",\"capture_calibration\":\"nominal scalar only; target capsule pressure is not calibrated\""
                 << ",\"digital_gain_per_pa\":" << gain << ",\"physics\":{"
                 << "\"initial_energy_j\":" << s.initial_energy_j << ",\"final_energy_j\":" << s.final_energy_j
                 << ",\"actuator_work_j\":" << s.actuator_work_j << ",\"dissipated_energy_j\":" << s.dissipated_energy_j
                 << ",\"max_energy_residual_j\":" << s.max_energy_residual_j
                 << ",\"max_contact_solve_residual_n\":" << s.max_contact_solve_residual_n
                 << ",\"max_normal_force_n\":" << s.max_normal_force_n << ",\"max_indentation_m\":" << s.max_indentation_m
                 << ",\"max_contact_point_displacement_m\":" << s.max_contact_point_displacement_m
                 << ",\"max_plate_displacement_bound_m\":" << s.max_plate_displacement_bound_m
                 << ",\"max_displacement_thickness_ratio\":" << s.max_displacement_thickness_ratio
                 << ",\"max_vent_mach\":" << s.max_vent_mach << ",\"max_vent_reynolds\":" << s.max_vent_reynolds
                 << ",\"max_duct_mach\":" << s.max_duct_mach << ",\"max_duct_reynolds\":" << s.max_duct_reynolds
                 << ",\"min_mode_hz\":" << s.min_mode_hz << ",\"max_mode_hz\":" << s.max_mode_hz
                 << ",\"texture_max_advection_hz\":" << (p.action=="stroke"?p.speed_m_s/p.texture_min_wavelength_m:0)
                 << ",\"unsteady_viscous_losses\":" << p.unsteady_viscous_losses
                 << ",\"max_solver_iterations\":" << s.max_solver_iterations
                 << ",\"retained_modes_per_plate\":" << s.retained_modes_per_plate << ",\"finite\":" << (s.finite?"true":"false")
                 << ",\"regime_valid\":" << (s.regime_valid?"true":"false") << ",\"regime_warnings\":[";
        for(std::size_t i=0;i<s.regime_warnings.size();++i){if(i)metadata<<',';metadata<<quote(s.regime_warnings[i]);}
        metadata << "]}}";
        write_json(out_path/"native.json",metadata.str());
        std::cout << metadata.str() << '\n';
        return 0;
    } catch(const std::exception& e) {
        std::cerr << "{\"ok\":false,\"error\":" << quote(e.what()) << "}\n";
        return 2;
    }
}
