#include "physics.hpp"
#include "viscous.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <utility>

namespace ku100 {
namespace {
constexpr double pi = 3.141592653589793238462643383279502884;
double sq(double x) { return x * x; }
double positive(double x) { return std::max(0.0, x); }

struct Mode {
    double omega2, b, t, area, normal_amplitude;
};

// Jacobi diagonalization of the symmetric, mass-normalized Mindlin block.
// Each (m,n) has one transverse and two rotational coordinates. Keeping the
// eigenvectors, rather than merely fitting frequencies, preserves port work.
std::array<Mode, 3> mindlin_block(const PhysicsParams& p, unsigned m, unsigned n) {
    const double alpha = m*pi/p.plate_width_m, beta = n*pi/p.plate_height_m;
    const double h = p.plate_thickness_m;
    const double area4 = p.plate_width_m*p.plate_height_m/4.0;
    const double mass_w = p.density_kg_m3*h*area4;
    const double mass_r = p.density_kg_m3*h*h*h*area4/12.0;
    const double D = p.young_modulus_pa*h*h*h/(12.0*(1.0-sq(p.poisson_ratio)));
    const double S = (5.0/6.0)*p.young_modulus_pa*h/(2.0*(1.0+p.poisson_ratio));
    const std::array<double, 3> mass = {mass_w, mass_r, mass_r};
    double a[3][3] = {
        {S*(sq(alpha)+sq(beta)), -S*alpha, -S*beta},
        {-S*alpha, D*(sq(alpha)+(1-p.poisson_ratio)*sq(beta)/2)+S,
         D*(1+p.poisson_ratio)*alpha*beta/2},
        {-S*beta, D*(1+p.poisson_ratio)*alpha*beta/2,
         D*(sq(beta)+(1-p.poisson_ratio)*sq(alpha)/2)+S}
    };
    double e[3][3] = {{1,0,0},{0,1,0},{0,0,1}};
    for (unsigned i=0;i<3;++i) for (unsigned j=0;j<3;++j)
        a[i][j] *= area4/std::sqrt(mass[i]*mass[j]);
    for (unsigned sweep=0;sweep<32;++sweep) {
        unsigned r=0,s=1;
        if (std::abs(a[0][2])>std::abs(a[r][s])) {r=0;s=2;}
        if (std::abs(a[1][2])>std::abs(a[r][s])) {r=1;s=2;}
        if (std::abs(a[r][s]) < 1e-15*(std::abs(a[0][0])+std::abs(a[1][1])+std::abs(a[2][2]))) break;
        const double angle = 0.5*std::atan2(2*a[r][s], a[s][s]-a[r][r]);
        const double c=std::cos(angle), sn=std::sin(angle);
        const double arr=a[r][r], ass=a[s][s], ars=a[r][s];
        for(unsigned k=0;k<3;++k) if(k!=r && k!=s) {
            const double kr=a[k][r], ks=a[k][s];
            a[k][r]=a[r][k]=c*kr-sn*ks;
            a[k][s]=a[s][k]=sn*kr+c*ks;
        }
        a[r][r]=c*c*arr-2*c*sn*ars+sn*sn*ass;
        a[s][s]=sn*sn*arr+2*c*sn*ars+c*c*ass;
        a[r][s]=a[s][r]=0;
        for(unsigned k=0;k<3;++k) {
            const double er=e[k][r], es=e[k][s];
            e[k][r]=c*er-sn*es; e[k][s]=sn*er+c*es;
        }
    }
    // A fixed finite Gaussian traction footprint. The centre and spatial
    // standard deviation are geometry, never functions of retained mode count.
    const double x=0.43*p.plate_width_m, y=0.47*p.plate_height_m;
    const double sigma=p.contact_radius_m/2;
    const double patch=std::exp(-0.5*sq(sigma)*(sq(alpha)+sq(beta)));
    std::array<Mode,3> out{};
    for(unsigned j=0;j<3;++j) {
        const double w=e[0][j]/std::sqrt(mass_w), rx=e[1][j]/std::sqrt(mass_r);
        out[j]={a[j][j], w*std::sin(alpha*x)*std::sin(beta*y)*patch,
            -h/2*rx*std::cos(alpha*x)*std::sin(beta*y)*patch,
            w*(1-std::cos(m*pi))*(1-std::cos(n*pi))/(alpha*beta),w};
    }
    return out;
}

std::vector<Mode> make_modes(const PhysicsParams& p,double& reference_compliance) {
    std::vector<Mode> modes;
    // Fixed candidate space makes count refinements nested. The exposed count
    // is capped at 1024, well within this fixed analytic candidate space for
    // the supported plate aspect ratios. Driver calibration uses this same
    // reference compliance even when the runtime basis is truncated.
    modes.reserve(3*96*96);
    reference_compliance=0;
    for(unsigned m=1;m<=96;++m) for(unsigned n=1;n<=96;++n) {
        const auto block=mindlin_block(p,m,n);
        modes.insert(modes.end(),block.begin(),block.end());
        for(const auto& mode:block) reference_compliance+=mode.b*mode.b/mode.omega2;
    }
    std::stable_sort(modes.begin(),modes.end(),[](const Mode& x,const Mode& y){return x.omega2<y.omega2;});
    modes.resize(p.modes_per_plate);
    return modes;
}

// Constant symmetric positive-definite tridiagonal acoustic Schur complement.
struct Tridiagonal {
    std::vector<double> diag, off, factor;
    Tridiagonal(std::vector<double> d, std::vector<double> o):diag(std::move(d)),off(std::move(o)) {
        factor.resize(off.size());
        for(std::size_t i=0;i<off.size();++i) {
            if(!(diag[i]>0)) throw std::runtime_error("Nonpositive acoustic pivot");
            factor[i]=off[i]/diag[i]; diag[i+1]-=factor[i]*off[i];
        }
        if(!(diag.back()>0)) throw std::runtime_error("Nonpositive final acoustic pivot");
    }
    void solve(std::vector<double>& b) const {
        for(std::size_t i=1;i<b.size();++i) b[i]-=factor[i-1]*b[i-1];
        b.back()/=diag.back();
        for(std::size_t i=b.size()-1;i-->0;) b[i]=(b[i]-off[i]*b[i+1])/diag[i];
    }
};

std::uint64_t splitmix(std::uint64_t& x) {
    std::uint64_t z=(x+=0x9e3779b97f4a7c15ULL);
    z=(z^(z>>30))*0xbf58476d1ce4e5b9ULL;
    z=(z^(z>>27))*0x94d049bb133111ebULL;
    return z^(z>>31);
}

struct Driver {
    const PhysicsParams& p;
    std::array<double,32> phase{}, k{}, amplitude{};
    double preload, clearance;
    Driver(const PhysicsParams& params,double compliance):p(params) {
        preload=std::pow(p.load_n/p.contact_stiffness_n_m15,2.0/3.0)+p.load_n*compliance;
        clearance=std::max(2e-4,0.4*preload);
        std::uint64_t rng=p.seed;
        double power=0;
        for(unsigned i=0;i<32;++i) {
            phase[i]=2*pi*(splitmix(rng)>>11)*0x1.0p-53;
            const double wavelength=p.texture_max_wavelength_m*std::pow(p.texture_min_wavelength_m/p.texture_max_wavelength_m,static_cast<double>(i)/31);
            k[i]=2*pi/wavelength;
            amplitude[i]=std::pow(wavelength/p.texture_max_wavelength_m,p.texture_amplitude_exponent);
            power+=sq(amplitude[i])/2;
        }
        for(double& a:amplitude) a*=p.roughness_rms_m/std::sqrt(power);
    }
    double envelope(double t) const {
        if(p.action=="silence" || p.load_n==0) return 0;
        if(p.action=="tap") {
            const double start=std::min(0.04,p.duration_s*0.08);
            const double span=std::min(0.08,p.duration_s*0.3);
            if(t<=start || t>=start+span) return 0;
            return sq(std::sin(pi*(t-start)/span));
        }
        const double end=p.duration_s*0.75;
        const double ramp=std::min(0.08,p.duration_s*0.15);
        if(t<=0 || t>=end) return 0;
        if(t<ramp) return 0.5-0.5*std::cos(pi*t/ramp);
        if(t>end-ramp) return 0.5-0.5*std::cos(pi*(end-t)/ramp);
        return 1;
    }
    double height(double t,double position) const {
        double roughness=0;
        if(p.action=="stroke") for(unsigned i=0;i<32;++i)
            roughness+=amplitude[i]*std::sin(k[i]*position+phase[i]);
        return -clearance+envelope(t)*(preload+clearance+roughness);
    }
    double velocity(double t) const {return p.action=="stroke" ? p.speed_m_s*envelope(t) : 0;}
};

double potential(double delta,double stiffness) {return stiffness*std::pow(positive(delta),2.5)/2.5;}
double spring_gradient(double a,double b,double stiffness) {
    if(a<=0 && b<=0) return 0;
    if(a>0 && b>0) {
        const double x=std::sqrt(a),y=std::sqrt(b);
        // Algebraically exact divided difference, safe at a==b.
        return stiffness*(sq(sq(x))+x*x*x*y+sq(x*y)+x*y*y*y+sq(sq(y)))/(2.5*(x+y));
    }
    return (potential(b,stiffness)-potential(a,stiffness))/(b-a);
}

struct ContactSolution {double normal=0,tangent=0,vn=0,vt=0,delta=0,loss_rate=0,residual=0;unsigned iterations=0;};

ContactSolution contact_solve(double d0,double driver_vn,double driver_vt,double bn,double bt,
        double ynn,double ynt,double ytt,double dt,const PhysicsParams& p,double previous_force) {
    const double mu=p.friction_coefficient;
    const double film_normal=p.wetness*3*pi*p.film_viscosity_pa_s*std::pow(p.contact_radius_m,4)/
        (2*std::pow(p.film_thickness_m,3));
    const double film_tangent=p.wetness*p.film_viscosity_pa_s*pi*sq(p.contact_radius_m)/p.film_thickness_m;
    auto evaluate=[&](double force) {
        ContactSolution c;c.normal=force;
        const double u=driver_vt-bt-ynt*force;
        const double viscous=force>0 ? film_tangent : 0;
        const double bound=mu*force+viscous*std::abs(u);
        double lower=-bound,upper=bound,ft=0;
        for(unsigned it=0;it<40 && bound>0;++it) {
            const double vr=u-ytt*ft,th=std::tanh(vr/p.friction_velocity_m_s);
            const double g=ft-mu*force*th-viscous*vr;
            if(std::abs(g)<1e-13*(1+bound)) break;
            if(g>0) upper=ft;else lower=ft;
            const double dg=1+ytt*(mu*force*(1-th*th)/p.friction_velocity_m_s+viscous);
            const double next=ft-g/dg;
            ft=(next>lower && next<upper) ? next : 0.5*(lower+upper);
        }
        c.tangent=ft;c.vt=u-ytt*ft;
        c.vn=driver_vn-bn-ynn*force-ynt*ft;
        c.delta=d0+dt*c.vn;
        const double damping=std::max(d0,c.delta)>0 ? p.contact_damping_n_s_m+film_normal : 0;
        const double damping_force=damping*positive(c.vn);
        c.residual=force-spring_gradient(d0,c.delta,p.contact_stiffness_n_m15)-damping_force;
        c.loss_rate=damping_force*c.vn+ft*c.vt;
        return c;
    };
    auto zero=evaluate(0);
    if(zero.residual>=0) return zero;
    double lo=0,hi=std::max(1.0,-2*zero.residual);
    auto high=evaluate(hi);
    for(unsigned i=0;high.residual<0 && i<48;++i){hi*=2;high=evaluate(hi);}
    if(high.residual<0 || !std::isfinite(hi)) throw std::runtime_error("Could not bracket contact force");
    double f=std::clamp(previous_force,lo,hi);
    ContactSolution current;
    for(unsigned iteration=0;iteration<64;++iteration) {
        current=evaluate(f);current.iterations=iteration+1;
        if(std::abs(current.residual)<=1e-11*(1+f)) return current;
        if(current.residual>0) hi=f;else lo=f;
        // A safeguarded numerical Newton derivative only evaluates the two
        // contact ports; no O(number of modes) operation occurs in this solve.
        const double step=1e-6*(1+f);
        const double derivative=(evaluate(f+step).residual-current.residual)/step;
        const double next=f-current.residual/derivative;
        f=(derivative>0 && next>lo && next<hi) ? next : 0.5*(lo+hi);
    }
    throw std::runtime_error("Contact solve failed to converge; reduce time step or revise parameters");
}
} // namespace

void validate_physics_params(const PhysicsParams& p) {
    auto positive_value=[](double x,const char* name){if(!std::isfinite(x)||x<=0) throw std::invalid_argument(std::string(name)+" must be positive and finite");};
    auto nonnegative=[](double x,const char* name){if(!std::isfinite(x)||x<0) throw std::invalid_argument(std::string(name)+" must be nonnegative and finite");};
    if(p.sample_rate<48000 || p.sample_rate>1536000) throw std::invalid_argument("sample_rate must be 48000..1536000");
    positive_value(p.duration_s,"duration_s");if(p.duration_s>120) throw std::invalid_argument("duration_s exceeds 120 s");
    if(p.duration_s*p.sample_rate<1 || p.duration_s*p.sample_rate>24000000)
        throw std::invalid_argument("render must contain 1..24000000 integration samples");
    if(p.modes_per_plate<1 || p.modes_per_plate>1024) throw std::invalid_argument("modes_per_plate must be 1..1024");
    if(p.duct_cells<1 || p.duct_cells>256) throw std::invalid_argument("duct_cells must be 1..256");
    if(p.trace_stride==0) throw std::invalid_argument("trace_stride must be positive");
    if(p.action!="stroke"&&p.action!="press"&&p.action!="tap"&&p.action!="silence") throw std::invalid_argument("unknown action");
    if(p.side!="left"&&p.side!="right") throw std::invalid_argument("side must be left or right");
    nonnegative(p.load_n,"load_n");nonnegative(p.speed_m_s,"speed_m_s");nonnegative(p.roughness_rms_m,"roughness_rms_m");
    if(!std::isfinite(p.wetness)||p.wetness<0||p.wetness>1) throw std::invalid_argument("wetness must be 0..1");
    if(p.unsteady_viscous_losses>1) throw std::invalid_argument("unsteady_viscous_losses must be 0 or 1");
    if(!std::isfinite(p.texture_min_wavelength_m)||!std::isfinite(p.texture_max_wavelength_m)||
       p.texture_min_wavelength_m<1e-6||p.texture_max_wavelength_m>0.1||
       p.texture_min_wavelength_m>=p.texture_max_wavelength_m)
        throw std::invalid_argument("texture wavelengths must satisfy 1 um <= minimum < maximum <= 0.1 m");
    if(!std::isfinite(p.texture_amplitude_exponent)||p.texture_amplitude_exponent<0||p.texture_amplitude_exponent>2)
        throw std::invalid_argument("texture_amplitude_exponent must be 0..2");
    if(p.action=="stroke" && p.speed_m_s/p.texture_min_wavelength_m>p.sample_rate/16.)
        throw std::invalid_argument("texture advection needs at least 16 integration samples per shortest cycle");
    positive_value(p.contact_radius_m,"contact_radius_m");positive_value(p.plate_width_m,"plate_width_m");
    positive_value(p.plate_height_m,"plate_height_m");positive_value(p.plate_thickness_m,"plate_thickness_m");
    const double aspect=p.plate_width_m/p.plate_height_m;
    if(aspect<0.25 || aspect>4) throw std::invalid_argument("plate aspect ratio must be 0.25..4");
    if(p.contact_radius_m>0.15*std::min(p.plate_width_m,p.plate_height_m)) throw std::invalid_argument("contact footprint is too large for the finite-plate Gaussian approximation");
    positive_value(p.young_modulus_pa,"young_modulus_pa");positive_value(p.density_kg_m3,"density_kg_m3");
    if(!std::isfinite(p.poisson_ratio)||p.poisson_ratio<=-1||p.poisson_ratio>=0.5) throw std::invalid_argument("poisson_ratio must be between -1 and 0.5");
    nonnegative(p.modal_loss_ratio,"modal_loss_ratio");positive_value(p.cavity_volume_m3,"cavity_volume_m3");
    positive_value(p.duct_length_m,"duct_length_m");positive_value(p.duct_radius_m,"duct_radius_m");
    positive_value(p.vent_length_m,"vent_length_m");positive_value(p.vent_radius_m,"vent_radius_m");
    positive_value(p.contact_stiffness_n_m15,"contact_stiffness_n_m15");nonnegative(p.contact_damping_n_s_m,"contact_damping_n_s_m");
    nonnegative(p.friction_coefficient,"friction_coefficient");positive_value(p.friction_velocity_m_s,"friction_velocity_m_s");
    positive_value(p.film_thickness_m,"film_thickness_m");positive_value(p.film_viscosity_pa_s,"film_viscosity_pa_s");
    positive_value(p.air_density_kg_m3,"air_density_kg_m3");positive_value(p.sound_speed_m_s,"sound_speed_m_s");
    positive_value(p.air_viscosity_pa_s,"air_viscosity_pa_s");
}

PhysicsResult simulate(const PhysicsParams& p) {
    validate_physics_params(p);
    PhysicsResult result;result.sample_rate=p.sample_rate;
    const std::size_t samples=static_cast<std::size_t>(std::ceil(p.duration_s*p.sample_rate));
    result.local_pressure_left_pa.resize(samples);result.local_pressure_right_pa.resize(samples);
    result.airborne_pressure_left_at_025m_pa.resize(samples);result.airborne_pressure_right_at_025m_pa.resize(samples);
    result.trace.reserve(samples/p.trace_stride+1);
    double static_compliance=0;
    const auto modes=make_modes(p,static_compliance);const std::size_t nm=modes.size();
    const double dt=1.0/p.sample_rate,h=dt/2;
    const unsigned side=p.side=="left"?0:1;
    const std::size_t np=p.duct_cells+2,last=np-1,active=side==0?0:last;
    std::vector<double> q(2*nm,0),v(2*nm,0),vfree(2*nm),den(nm),damping(nm);
    double aa=0,ab=0,at=0,bb=0,bt=0,tt=0;
    for(std::size_t i=0;i<nm;++i) {
        const auto& m=modes[i];damping[i]=2*p.modal_loss_ratio*std::sqrt(m.omega2);
        den[i]=1/(1+h*damping[i]+h*h*m.omega2);
        aa+=m.area*m.area*den[i];ab+=m.area*m.b*den[i];at+=m.area*m.t*den[i];
        bb+=m.b*m.b*den[i];bt+=m.b*m.t*den[i];tt+=m.t*m.t*den[i];
    }
    Driver driver(p,static_compliance);
    const double rho=p.air_density_kg_m3,c=p.sound_speed_m_s;
    const double dx=p.duct_length_m/p.duct_cells,duct_area=pi*sq(p.duct_radius_m);
    std::vector<double> cap(np,duct_area*dx/(rho*c*c));
    cap[0]=cap[last]=p.cavity_volume_m3/(rho*c*c);
    std::vector<ViscousTube> tubes; tubes.reserve(np-1);
    std::vector<double> invz(np-1),tube_bias(np-1);
    for(std::size_t j=0;j<np-1;++j) {
        const double length=(j==0||j==np-2)?dx/2:dx;
        tubes.emplace_back(rho,p.air_viscosity_pa_s,p.duct_radius_m,length,h,p.unsteady_viscous_losses!=0);
        invz[j]=1/tubes[j].impedance;
    }
    const double vent_area=pi*sq(p.vent_radius_m);
    std::array<ViscousTube,2> vents={
        ViscousTube(rho,p.air_viscosity_pa_s,p.vent_radius_m,p.vent_length_m,h,p.unsteady_viscous_losses!=0),
        ViscousTube(rho,p.air_viscosity_pa_s,p.vent_radius_m,p.vent_length_m,h,p.unsteady_viscous_losses!=0)};
    const double rad_r=rho*c/(4*pi*sq(p.vent_radius_m)),rad_tau=p.vent_radius_m/c;
    const double rad_a=1/(1+h/rad_tau);
    const double vent_z=vents[0].impedance+rad_r*rad_a;
    std::vector<double> diag(np),off(np-1);
    for(std::size_t j=0;j<np;++j) diag[j]=cap[j]/h;
    for(std::size_t j=0;j<np-1;++j){diag[j]+=invz[j];diag[j+1]+=invz[j];off[j]=-invz[j];}
    diag[0]+=h*aa+1/vent_z;diag[last]+=h*aa+1/vent_z;
    Tridiagonal acoustic(diag,off);
    std::vector<double> response(np,0);response[active]=1;acoustic.solve(response);
    const double ynn=h*bb-h*h*ab*ab*response[active];
    const double ynt=h*bt-h*h*ab*at*response[active];
    const double ytt=h*tt-h*h*at*at*response[active];
    if(ynn<=0 || ytt<0 || ynn*ytt-ynt*ynt < -1e-14*ynn*ytt) throw std::runtime_error("Contact admittance is not passive");
    std::vector<double> pressure(np,0),pbar(np),qb(np-1);
    std::array<double,2> vent_flow{},radiation_state{},vent_bias{},vent_mid{},rad_mid{};
    double work=0,dissipation=0,previous_force=0,sliding=0;
    double y0=driver.height(0,0);
    result.stats.min_mode_hz=std::sqrt(modes.front().omega2)/(2*pi);
    result.stats.max_mode_hz=std::sqrt(modes.back().omega2)/(2*pi);
    result.stats.retained_modes_per_plate=static_cast<unsigned>(nm);
    for(std::size_t step=0;step<samples;++step) {
        const double time=step*dt,vt_driver=driver.velocity(time+h);
        const double sliding_new=sliding+dt*vt_driver,y1=driver.height(time+dt,sliding_new);
        std::array<double,2> avfree{};double bfree=0,tfree=0,contact_position=0;
        for(unsigned ear=0;ear<2;++ear) for(std::size_t i=0;i<nm;++i) {
            const std::size_t j=ear*nm+i;const auto& m=modes[i];
            vfree[j]=(v[j]-h*m.omega2*q[j])*den[i];avfree[ear]+=m.area*vfree[j];
            if(ear==side){bfree+=m.b*vfree[j];tfree+=m.t*vfree[j];contact_position+=m.b*q[j];}
        }
        for(std::size_t j=0;j<np;++j) pbar[j]=cap[j]/h*pressure[j];
        pbar[0]+=avfree[0];pbar[last]+=avfree[1];
        for(std::size_t j=0;j<np-1;++j) {
            tube_bias[j]=tubes[j].bias();
            const double bias=tube_bias[j]*invz[j];
            pbar[j]-=bias;pbar[j+1]+=bias;
        }
        for(unsigned ear=0;ear<2;++ear) {
            vent_bias[ear]=vents[ear].bias()+rad_r*rad_a*radiation_state[ear];
            pbar[ear==0?0:last]-=vent_bias[ear]/vent_z;
        }
        acoustic.solve(pbar);
        const double bn=bfree-h*ab*pbar[active],tn=tfree-h*at*pbar[active];
        const auto contact=contact_solve(y0-contact_position,(y1-y0)/dt,vt_driver,
            bn,tn,ynn,ynt,ytt,dt,p,previous_force);
        previous_force=contact.normal;
        const double source=h*(ab*contact.normal+at*contact.tangent);
        for(std::size_t j=0;j<np;++j) pbar[j]+=response[j]*source;
        double energy=0,loss_rate=contact.loss_rate,contact_displacement_end=0;
        std::array<double,2> plate_displacement_bound{};
        for(unsigned ear=0;ear<2;++ear) for(std::size_t i=0;i<nm;++i) {
            const auto& m=modes[i];const std::size_t j=ear*nm+i;
            const double forcing=(ear==side?m.b*contact.normal+m.t*contact.tangent:0)-m.area*pbar[ear==0?0:last];
            const double vm=vfree[j]+h*den[i]*forcing;
            q[j]+=dt*vm;v[j]=2*vm-v[j];
            if(ear==side) contact_displacement_end+=m.b*q[j];
            plate_displacement_bound[ear]+=std::abs(m.normal_amplitude*q[j]);
            energy+=0.5*(sq(v[j])+m.omega2*sq(q[j]));loss_rate+=damping[i]*sq(vm);
        }
        for(std::size_t j=0;j<np-1;++j) {
            qb[j]=(pbar[j]-pbar[j+1]+tube_bias[j])*invz[j];
            loss_rate+=tubes[j].advance(qb[j]);energy+=tubes[j].energy();
            const double speed=std::abs(tubes[j].flow)/duct_area;
            result.stats.max_duct_mach=std::max(result.stats.max_duct_mach,speed/c);
            result.stats.max_duct_reynolds=std::max(result.stats.max_duct_reynolds,
                2*rho*p.duct_radius_m*speed/p.air_viscosity_pa_s);
        }
        for(std::size_t j=0;j<np;++j){pressure[j]=2*pbar[j]-pressure[j];energy+=0.5*cap[j]*sq(pressure[j]);}
        for(unsigned ear=0;ear<2;++ear) {
            vent_mid[ear]=(pbar[ear==0?0:last]+vent_bias[ear])/vent_z;
            rad_mid[ear]=rad_a*radiation_state[ear]+(1-rad_a)*vent_mid[ear];
            const double rad_difference=vent_mid[ear]-rad_mid[ear];
            loss_rate+=vents[ear].advance(vent_mid[ear]);
            vent_flow[ear]=vents[ear].flow;radiation_state[ear]=2*rad_mid[ear]-radiation_state[ear];
            const double speed=std::abs(vent_flow[ear])/vent_area;
            result.stats.max_vent_mach=std::max(result.stats.max_vent_mach,speed/c);
            result.stats.max_vent_reynolds=std::max(result.stats.max_vent_reynolds,
                2*rho*p.vent_radius_m*speed/p.air_viscosity_pa_s);
            energy+=vents[ear].energy()+0.5*rad_r*rad_tau*sq(radiation_state[ear]);
            loss_rate+=rad_r*sq(rad_difference);
            auto& output=ear==0?result.airborne_pressure_left_at_025m_pa:result.airborne_pressure_right_at_025m_pa;
            // End-of-step observation, matching the cavity/structural states.
            output[step]=rad_r*(p.vent_radius_m/0.25)*(vent_flow[ear]-radiation_state[ear]);
        }
        energy+=potential(contact.delta,p.contact_stiffness_n_m15);
        work+=contact.normal*(y1-y0)+contact.tangent*vt_driver*dt;
        dissipation+=dt*loss_rate;
        const double residual=energy+dissipation-work;
        result.local_pressure_left_pa[step]=pressure[0];result.local_pressure_right_pa[step]=pressure[last];
        auto& stats=result.stats;
        stats.final_energy_j=energy;stats.actuator_work_j=work;stats.dissipated_energy_j=dissipation;
        stats.max_energy_residual_j=std::max(stats.max_energy_residual_j,std::abs(residual));
        stats.max_contact_solve_residual_n=std::max(stats.max_contact_solve_residual_n,std::abs(contact.residual));
        stats.max_normal_force_n=std::max(stats.max_normal_force_n,contact.normal);
        stats.max_indentation_m=std::max(stats.max_indentation_m,positive(contact.delta));
        stats.max_contact_point_displacement_m=std::max(stats.max_contact_point_displacement_m,std::abs(contact_displacement_end));
        stats.max_plate_displacement_bound_m=std::max(stats.max_plate_displacement_bound_m,
            std::max(plate_displacement_bound[0],plate_displacement_bound[1]));
        stats.max_solver_iterations=std::max(stats.max_solver_iterations,contact.iterations);
        if(!std::isfinite(energy)||!std::isfinite(residual)||!std::isfinite(pressure[0])||!std::isfinite(pressure[last]))
            throw std::runtime_error("Non-finite physical state");
        if(step%p.trace_stride==0 || step+1==samples) result.trace.push_back({time+dt,
            contact.normal,contact.tangent,contact.delta,energy,work,dissipation,residual,
            pressure[0],pressure[last],sliding_new});
        y0=y1;sliding=sliding_new;
    }
    auto& stats=result.stats;
    stats.max_displacement_thickness_ratio=stats.max_plate_displacement_bound_m/p.plate_thickness_m;
    auto warn=[&](bool violated,const char* reason) {if(violated){stats.regime_valid=false;stats.regime_warnings.emplace_back(reason);}};
    warn(stats.max_displacement_thickness_ratio>0.1,
        "Conservative global plate-displacement bound exceeds 0.1 thickness; linear plate approximation may require geometric nonlinearity");
    warn(stats.max_vent_mach>0.05 || stats.max_duct_mach>0.05,
        "Peak air-flow Mach number exceeds the conservative 0.05 small-signal screen");
    warn(stats.max_vent_reynolds>1000 || stats.max_duct_reynolds>1000,
        "Peak pipe Reynolds number exceeds the conservative 1000 laminar-flow screen");
    return result;
}
} // namespace ku100
