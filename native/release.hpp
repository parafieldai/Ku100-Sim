#pragma once
// SPDX-License-Identifier: MIT
// Falsifiable pressure-release SOURCE hypothesis, not a tongue/ear simulation.
// A prescribed cavity-wall displacement and resistive opening drive continuous
// air states. No recording, stochastic click schedule, or audio-rate noise.
#include "viscous.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>
#include <vector>

namespace ku100::release {
constexpr double pi=3.14159265358979323846;
struct Params {
    unsigned rate=768000;
    double duration=4.0, volume=0.8e-6, radius=0.0012, length=0.002;
    double seal_length=0.0001, leakage_radius=0.00001, displaced_volume=0.7e-9;
    double opening_s=0.001, period=0.9;
    double density=1.204, sound_speed=343, viscosity=1.81e-5, discharge=0.7;
    bool vented=false, nonlinear=true, unsteady=true;
};
inline void validate(const Params& p) {
    const double values[]={p.duration,p.volume,p.radius,p.length,p.seal_length,p.leakage_radius,
        p.displaced_volume,p.opening_s,p.period,p.density,p.sound_speed,p.viscosity,p.discharge};
    for(double x:values) if(!std::isfinite(x)) throw std::invalid_argument("nonfinite source parameter");
    if(p.rate<48000||p.rate>768000||p.rate%48000||p.duration<0.7||p.duration>8||
       p.volume<1e-8||p.volume>1e-5||p.radius<0.0001||p.radius>0.003||
       p.length<0.0001||p.length>0.02||p.seal_length<=0||p.seal_length>0.001||
       p.leakage_radius<1e-6||p.leakage_radius>p.radius||p.displaced_volume<0||
       p.displaced_volume>0.02*p.volume||p.opening_s<32./p.rate||p.opening_s>.08||
       p.period<.7||p.period>2||p.density<=0||p.sound_speed<=0||p.viscosity<=0||p.discharge<=0||p.discharge>1)
        throw std::invalid_argument("outside declared release-probe parameter domain");
}
inline Params checked(Params p) { validate(p); return p; }
inline double smooth(double x) {x=std::clamp(x,0.,1.);return x*x*x*(10+x*(-15+6*x));}
// Smooth prescribed kinematics; only the geometry/volume trajectory repeats.
// The pressure, flow and radiation memory never reset at a cycle boundary.
inline std::array<double,2> controls(double t,const Params& p) {
    if(t<.1||t>p.duration-.2) return {0,p.radius};
    const double u=std::fmod(t-.1,p.period);
    if(t-u+p.period>p.duration-.2) return {0,p.radius};
    const double seal=smooth((u-.04)/.08)*(1-smooth((u-.42)/p.opening_s));
    const double displacement=p.displaced_volume*smooth((u-.17)/.08)*(1-smooth((u-.56)/.08));
    const double radius=p.vented?p.radius:p.radius-(p.radius-p.leakage_radius)*seal;
    return {displacement,radius};
}
struct Row {double t,p,q,opening,volume,source,energy,work,loss;};
struct Result {std::vector<double> source;std::vector<Row> trace;double work=0,loss=0,energy=0,max_residual=0,max_pressure=0,max_mach=0,max_reynolds=0;};
class State {
public:
    Params params; double pressure=0,flow=0,radiation=0,work=0,loss=0;
    double C,L,R,Rrad,tau,dt;
    ViscousTube tube;
    explicit State(Params p):params(checked(p)),tube(params.density,params.viscosity,params.radius,params.length,.5/params.rate,params.unsteady) {
        validate(p);dt=1./p.rate;const double area=pi*p.radius*p.radius;
        C=p.volume/(p.density*p.sound_speed*p.sound_speed);
        L=p.density*p.length/area;
        R=8*p.viscosity*p.length/(pi*std::pow(p.radius,4));
        Rrad=p.density*p.sound_speed/(4*pi*p.radius*p.radius);tau=p.radius/p.sound_speed;
    }
    double energy()const{return .5*(C*pressure*pressure+Rrad*tau*radiation*radiation)+tube.energy();}
    // Discrete-gradient/midpoint equations: C pdot=-Q-Udot;
    // L Qdot=p-(R+Rseal)Q-K|Q|Q-Rrad(Q-z); tau zdot=Q-z.
    // Opening affects resistance only. Fixed neck/cavity stores deliberately
    // exclude moving-neck inertia, saliva, seal mechanics and membrane energy.
    double step(double delta_volume,double opening) {
        if(!std::isfinite(delta_volume)||!std::isfinite(opening)||opening<params.leakage_radius*.999||opening>params.radius*1.001)
            throw std::invalid_argument("invalid source control");
        const double v=delta_volume/dt,rs=8*params.viscosity*params.seal_length/(pi*std::pow(opening,4));
        const double k=params.nonlinear?params.density/(2*params.discharge*params.discharge*std::pow(pi*opening*opening,2)):0;
        const double a=1/(1+dt/(2*tau));
        const double d=tube.impedance+dt/(2*C)+rs+Rrad*a;
        const double b=tube.bias()+pressure-dt*v/(2*C)+Rrad*a*radiation;
        const double qm=2*b/(d+std::sqrt(d*d+4*k*std::abs(b)));
        const double pm=pressure-dt*(qm+v)/(2*C);
        const double zm=a*(radiation+dt*qm/(2*tau));
        work-=pm*delta_volume;
        loss+=dt*(tube.advance(qm)+rs*qm*qm+k*std::pow(std::abs(qm),3)+Rrad*(qm-zm)*(qm-zm));
        pressure=2*pm-pressure;flow=2*qm-flow;radiation=2*zm-radiation;
        return (params.radius/.25)*Rrad*(flow-radiation);
    }
};
inline Result simulate(const Params& p) {
    State s(p);Result r;const auto n=static_cast<size_t>(std::llround(p.duration*p.rate));r.source.resize(n);
    double previous=controls(0,p)[0];
    for(size_t i=0;i<n;++i) {
        const double t=(i+1.)/p.rate;const auto now=controls(t,p),mid=controls(t-.5/p.rate,p);
        const double source=s.step(now[0]-previous,mid[1]);previous=now[0];
        const double e=s.energy(); if(!std::isfinite(e)||!std::isfinite(source))throw std::runtime_error("nonfinite source state");
        r.source[i]=source;r.max_residual=std::max(r.max_residual,std::abs(e+s.loss-s.work));
        r.max_pressure=std::max(r.max_pressure,std::abs(s.pressure));
        const double speed=std::abs(s.flow)/(pi*mid[1]*mid[1]);
        r.max_mach=std::max(r.max_mach,speed/p.sound_speed);
        r.max_reynolds=std::max(r.max_reynolds,2*p.density*mid[1]*speed/p.viscosity);
        if(i%std::max(1U,p.rate/1000)==0)r.trace.push_back({t,s.pressure,s.flow,now[1],now[0],source,e,s.work,s.loss});
    }
    r.work=s.work;r.loss=s.loss;r.energy=s.energy();return r;
}
} // namespace ku100::release
