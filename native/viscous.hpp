// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cmath>
#include <stdexcept>
namespace ku100 {
// Passive approximation to the exact no-slip circular-tube series impedance.
// Z(s)/M = s + 8 nu/a^2 + (nu/a^2) sum w_j*s/(s+pole_j*nu/a^2).
// First eight J2 zeros are exact; remaining zeros through 8192 are grouped
// using positive weights and harmonic-mean poles. The unresolved, fast tail
// contributes positive inertance. No thermal admittance is modeled here.
// Regenerate/verify with scripts/validate_viscous.py. See docs/VISCOUS_LOSSES.md.
struct ViscousTube {
    static constexpr unsigned count=32;
    inline static constexpr std::array<double,count> poles = {26.374616427163392,70.849998919095881,135.02070886597045,218.92018914566347,322.55511629254477,445.9275645373333,589.0383517134527,751.88785381011269,1117.0343052229653,1842.4630594420753,3046.5404829575691,5245.0003150277707,9131.1484604148282,16089.225186645344,27957.422213957252,49719.896427413434,88685.097330277174,156615.11678249127,277034.15990041755,490651.87742264732,871495.23666397331,1549043.5792067451,2753981.6342509217,4904166.2469286676,8729457.1295608208,15537201.820270773,27666590.323361389,49276789.901488863,87770899.521877974,156389467.22967196,278632218.49606025,496364283.07469153};
    inline static constexpr std::array<double,count> weights = {4,4,4,4,4,4,4,4,12,12,20,24,36,44,60,84,108,144,192,256,344,456,612,816,1088,1452,1940,2588,3456,4616,6156,8220};
    static constexpr double tail = 4.946568636754467e-05;
    unsigned terms=0;
    double mass=0, steady_resistance=0, half_step=0, impedance=0, flow=0;
    std::array<double,count> resistance{}, lambda{}, alpha{}, memory{};
    ViscousTube(double density,double viscosity,double radius,double length,double h,bool enabled)
      :terms(enabled?count:0),half_step(h) {
        constexpr double pi=3.14159265358979323846;
        const double base=density*length/(pi*radius*radius), scale=viscosity/(density*radius*radius);
        mass=base*(enabled?1+tail:1);steady_resistance=8*base*scale;
        impedance=mass/h+steady_resistance;
        for(unsigned j=0;j<terms;++j) {
            resistance[j]=base*scale*weights[j];lambda[j]=scale*poles[j];
            alpha[j]=1/(1+h*lambda[j]);impedance+=resistance[j]*alpha[j];
        }
        if(!(impedance>0)||!std::isfinite(impedance)) throw std::invalid_argument("Invalid viscous-tube impedance");
    }
    double bias() const {
        double b=mass/half_step*flow;
        for(unsigned j=0;j<terms;++j) b+=resistance[j]*alpha[j]*memory[j];
        return b;
    }
    // Commit midpoint flow. Return dissipated power; energy() includes every
    // memory's stored energy, so the coupled solver can audit interface work.
    double advance(double mid) {
        double loss=steady_resistance*mid*mid;
        for(unsigned j=0;j<terms;++j) {
            double zm=alpha[j]*memory[j]+(1-alpha[j])*mid;
            double difference=mid-zm;loss+=resistance[j]*difference*difference;
            memory[j]=2*zm-memory[j];
        }
        flow=2*mid-flow;return loss;
    }
    double energy() const {
        double e=.5*mass*flow*flow;
        for(unsigned j=0;j<terms;++j) e+=.5*resistance[j]/lambda[j]*memory[j]*memory[j];
        return e;
    }
};
} // namespace ku100
