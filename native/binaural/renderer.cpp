// SPDX-License-Identifier: MIT
// One measured binaural receiver for all source models. No object-name dispatch.
#include "../receiver.hpp"
#include <algorithm>
#include <cmath>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
namespace {
thread_local std::string error;
struct Receiver {
    std::vector<double> filters, history;
    std::size_t cursor=0;
    int taps=0;
    bool failed=false;
    Receiver(const char* path, double radius) {
        if(!path || !std::isfinite(radius)) throw std::invalid_argument("invalid bank/radius");
        const auto bank=ku100::HrirBank::load(path);
        // Same causal fractional delay and restored distance levels as the
        // existing static renderer; never apply a second 1/r gain.
        const auto propagation=ku100::delay_signal({1.0}, radius/343.0*48000.0);
        for(int angle=0;angle<360;++angle) {
            const auto h=bank.at(angle,radius);
            for(int ear=0;ear<2;++ear) {
                const auto full=ku100::convolve(propagation,h[ear]);
                if(!taps) taps=static_cast<int>(full.size());
                if(taps!=static_cast<int>(full.size())) throw std::runtime_error("inconsistent filters");
                filters.insert(filters.end(),full.begin(),full.end());
            }
        }
        history.resize(taps,0.0);
    }
    void process(int frames,const double* source,const double* angle,double* output) {
        if(failed || frames<1 || frames>65536 || !source || !angle || !output)
            throw std::invalid_argument("invalid receiver state/block");
        for(int i=0;i<frames;++i)
            if(!std::isfinite(source[i]) || !std::isfinite(angle[i]))
                throw std::invalid_argument("nonfinite receiver input");
        for(int i=0;i<frames;++i) {
            history[cursor]=source[i];
            double phi=std::fmod(angle[i],360.0);if(phi<0)phi+=360.0;if(phi>=360)phi=0;
            const int a=static_cast<int>(std::floor(phi)),b=(a+1)%360;
            const double w=phi-a;
            for(int ear=0;ear<2;++ear) {
                const double* h0=filters.data()+(a*2+ear)*taps;
                const double* h1=filters.data()+(b*2+ear)*taps;
                double y=0;
                // Interpolate the filters continuously at audio rate. No
                // block reset, hard switching, artificial L/R gain or Haas delay.
                int p=static_cast<int>(cursor);
                for(int k=0;k<taps;++k) {
                    y+=((1-w)*h0[k]+w*h1[k])*history[p];
                    if(--p<0)p=taps-1;
                }
                if(!std::isfinite(y)){failed=true;throw std::runtime_error("receiver overflow");}
                output[2*i+ear]=y;
            }
            if(++cursor==history.size())cursor=0;
        }
    }
};
}
extern "C" {
void* binaural_create(const char* path,double radius) {
    try{error.clear();return new Receiver(path,radius);}catch(const std::exception& e){error=e.what();return nullptr;}
}
int binaural_taps(void* ptr) {return ptr?static_cast<Receiver*>(ptr)->taps:0;}
int binaural_process(void* ptr,int n,const double* x,const double* a,double* y) {
    try{if(!ptr)throw std::invalid_argument("missing receiver");static_cast<Receiver*>(ptr)->process(n,x,a,y);return 0;}
    catch(const std::exception& e){error=e.what();return -1;}
}
void binaural_destroy(void* ptr){delete static_cast<Receiver*>(ptr);}
const char* binaural_error(){return error.c_str();}
}
