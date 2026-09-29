#include "receiver.hpp"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <limits>
#include <stdexcept>

namespace ku100 {
namespace {
constexpr double pi = 3.141592653589793238462643383279502884;
std::uint32_t read_u32(std::istream& in) {
    unsigned char b[4];
    if (!in.read(reinterpret_cast<char*>(b), 4)) throw std::runtime_error("truncated HRIR bank");
    return std::uint32_t(b[0]) | (std::uint32_t(b[1]) << 8) |
           (std::uint32_t(b[2]) << 16) | (std::uint32_t(b[3]) << 24);
}
double read_f64(std::istream& in) {
    std::uint64_t bits = read_u32(in);
    bits |= std::uint64_t(read_u32(in)) << 32;
    double d; std::memcpy(&d, &bits, 8); return d;
}
void u16(std::ostream& out, std::uint16_t n) {
    for (unsigned i=0;i<2;++i) out.put(static_cast<char>((n >> (i*8)) & 255));
}
void u32(std::ostream& out, std::uint32_t n) {
    for (unsigned i=0;i<4;++i) out.put(static_cast<char>((n >> (i*8)) & 255));
}
void finite_signal(const std::vector<double>& signal) {
    for (double x : signal) if (!std::isfinite(x)) throw std::invalid_argument("signal contains non-finite samples");
}
double sinc(double x) { return std::abs(x) < 1e-14 ? 1.0 : std::sin(pi*x)/(pi*x); }
double i0(double x) {
    double sum=1, term=1;
    for (unsigned k=1;k<100;++k) { term *= x*x/(4.0*k*k); sum += term; if(term<sum*1e-16) break; }
    return sum;
}
}  // namespace

HrirBank HrirBank::load(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) throw std::runtime_error("cannot open HRIR bank: " + path);
    char magic[8];
    if (!in.read(magic, 8) || std::memcmp(magic,"KUHRIR01",8)) throw std::runtime_error("invalid HRIR bank magic");
    HrirBank b;
    b.rate_=read_u32(in); const auto rings=read_u32(in);
    b.directions_=read_u32(in); b.taps_=read_u32(in);
    if (b.rate_ != 48000 || rings<1 || rings>32 || b.directions_ != 360 || b.taps_<1 || b.taps_>8192)
        throw std::runtime_error("unsupported HRIR bank dimensions");
    const auto count=std::uint64_t(rings)*b.directions_*2*b.taps_;
    if (count > 16*1024*1024) throw std::runtime_error("HRIR bank exceeds resource limit");
    b.radii_.reserve(rings);
    for(unsigned r=0;r<rings;++r) {
        const double radius=read_f64(in);
        if(!std::isfinite(radius) || radius<=0 || (!b.radii_.empty() && radius<=b.radii_.back()))
            throw std::runtime_error("HRIR radii must be positive and strictly increasing");
        b.radii_.push_back(radius);
    }
    b.ir_.reserve(static_cast<std::size_t>(count));
    for(std::uint64_t k=0;k<count;++k) {
        const auto bits=read_u32(in); float f; std::memcpy(&f,&bits,4);
        if(!std::isfinite(f)) throw std::runtime_error("non-finite HRIR sample");
        b.ir_.push_back(f);
    }
    if (in.peek()!=std::char_traits<char>::eof()) throw std::runtime_error("trailing bytes in HRIR bank");
    return b;
}

std::array<std::vector<double>,2> HrirBank::at(double azimuth_deg, double radius_m) const {
    if (!std::isfinite(azimuth_deg) || !std::isfinite(radius_m) || radii_.empty())
        throw std::invalid_argument("finite source coordinates and a loaded bank are required");
    if(radius_m < radii_.front()-1e-12 || radius_m > radii_.back()+1e-12)
        throw std::invalid_argument("source distance is outside measured KU100 range; extrapolation is forbidden");
    radius_m=std::max(radii_.front(),std::min(radii_.back(),radius_m));
    double angle=std::fmod(azimuth_deg,360.0); if(angle<0) angle+=360.0;
    // Adding 360 to a tiny negative remainder can round to exactly 360.
    // Keep the half-open interval before indexing the measured direction grid.
    if(angle>=360.0) angle=0.0;
    const auto a0=static_cast<unsigned>(std::floor(angle)), a1=(a0+1)%360;
    const double aw=angle-a0;
    auto upper=std::lower_bound(radii_.begin(),radii_.end(),radius_m);
    unsigned r1=static_cast<unsigned>(upper-radii_.begin());
    if(r1>=radii_.size()) r1=static_cast<unsigned>(radii_.size()-1);
    const unsigned r0=(r1>0 && radii_[r1]!=radius_m)?r1-1:r1;
    const double rw=r0==r1?0.0:(std::log(radius_m)-std::log(radii_[r0]))/(std::log(radii_[r1])-std::log(radii_[r0]));
    std::array<std::vector<double>,2> result;
    for(unsigned ear=0;ear<2;++ear) {
        result[ear].resize(taps_);
        auto index=[&](unsigned r,unsigned a,unsigned tap) {return ((std::size_t(r)*360+a)*2+ear)*taps_+tap;};
        for(unsigned k=0;k<taps_;++k) {
            const double lo=(1-aw)*ir_[index(r0,a0,k)]+aw*ir_[index(r0,a1,k)];
            const double hi=(1-aw)*ir_[index(r1,a0,k)]+aw*ir_[index(r1,a1,k)];
            result[ear][k]=(1-rw)*lo+rw*hi;
        }
    }
    return result;
}

std::vector<double> convolve(const std::vector<double>& signal,const std::vector<double>& fir) {
    finite_signal(signal); finite_signal(fir);
    if(signal.empty() || fir.empty()) return {};
    if(signal.size()>100000000 || fir.size()>1000000) throw std::invalid_argument("convolution resource limit");
    std::vector<double> out(signal.size()+fir.size()-1,0.0);
    for(std::size_t k=0;k<fir.size();++k) {
        const double h=fir[k]; if(h==0) continue;
        for(std::size_t n=0;n<signal.size();++n) out[n+k]+=h*signal[n];
    }
    return out;
}

double decimation_delay_s(unsigned input_rate,unsigned output_rate) {
    if(output_rate!=48000 || input_rate<output_rate || input_rate%output_rate || input_rate>768000)
        throw std::invalid_argument("integration rate must be an integer multiple of 48 kHz up to 768 kHz");
    return input_rate==output_rate?0.0:64.0/output_rate;
}
std::vector<double> decimate(const std::vector<double>& signal,unsigned input_rate,unsigned output_rate) {
    decimation_delay_s(input_rate,output_rate); finite_signal(signal);
    if(input_rate==output_rate || signal.empty()) return signal;
    const unsigned factor=input_rate/output_rate, half=64*factor;
    std::vector<double> h(2*half+1);
    const double fc=20000.0/input_rate, beta=9.0, den=i0(beta);
    double total=0;
    for(unsigned j=0;j<h.size();++j) {
        const double x=static_cast<double>(j)-half, unit=x/half;
        h[j]=2*fc*sinc(2*fc*x)*i0(beta*std::sqrt(std::max(0.0,1-unit*unit)))/den;
        total+=h[j];
    }
    for(double& x:h) x/=total;
    const auto last=signal.size()+h.size()-2;
    std::vector<double> out(last/factor+1,0.0);
    for(std::size_t n=0;n<out.size();++n) {
        const std::size_t t=n*factor;
        const std::size_t first=t>=signal.size()?t-signal.size()+1:0;
        const std::size_t end=std::min(t+1,h.size());
        double y=0;
        for(std::size_t k=first;k<end;++k) y+=h[k]*signal[t-k];
        out[n]=y;
    }
    return out;
}

std::vector<double> delay_signal(const std::vector<double>& signal,double delay_samples) {
    if(!std::isfinite(delay_samples) || delay_samples<0 || delay_samples>48000*10)
        throw std::invalid_argument("propagation delay must be finite, nonnegative and at most 10 seconds");
    finite_signal(signal); if(signal.empty()) return {};
    const auto integer=static_cast<std::size_t>(std::floor(delay_samples));
    const double fraction=delay_samples-integer;
    // A 63-tap causal windowed-sinc interpolator adds 31 fixed samples of
    // processing latency, reported separately from physical propagation.
    // Keep that latency at integer delays too: a source coordinate crossing an
    // integer-sample boundary must not jump by 31 samples.
    constexpr int half=31;
    std::vector<double> h(2*half+1); double sum=0;
    for(int j=0;j<=2*half;++j) {
        double x=j-half-fraction;
        const double u=(j-half)/double(half);
        h[j]=sinc(x)*i0(9.0*std::sqrt(std::max(0.0,1-u*u)))/i0(9.0); sum+=h[j];
    }
    for(double& v:h) v/=sum;
    auto tail=convolve(signal,h);
    std::vector<double> out(integer,0.0); out.insert(out.end(),tail.begin(),tail.end()); return out;
}

StereoSignal render_airborne(const std::vector<double>& pressure_at_reference,
                            const HrirBank& bank,double azimuth_deg,double radius_m,double speed) {
    if(!std::isfinite(speed) || speed<250 || speed>450) throw std::invalid_argument("invalid sound speed");
    const auto h=bank.at(azimuth_deg,radius_m);
    // The bank already contains the corrected distance gains. Multiplying by
    // another inverse-distance factor here would attenuate distance twice.
    const auto input=delay_signal(pressure_at_reference,radius_m/speed*bank.sample_rate());
    return {convolve(input,h[0]),convolve(input,h[1])};
}

void write_float_wav(const std::string& path,const StereoSignal& audio,unsigned rate) {
    if(rate<8000 || rate>768000 || audio.left.size()!=audio.right.size())
        throw std::invalid_argument("WAV channels/rate are inconsistent");
    finite_signal(audio.left); finite_signal(audio.right);
    const auto bytes=std::uint64_t(audio.left.size())*8;
    if(bytes>std::numeric_limits<std::uint32_t>::max()-50) throw std::invalid_argument("WAV is too large for RIFF");
    std::ofstream out(path,std::ios::binary|std::ios::trunc);
    if(!out) throw std::runtime_error("cannot open output WAV: "+path);
    out.write("RIFF",4);u32(out,static_cast<std::uint32_t>(bytes+50));out.write("WAVEfmt ",8);
    u32(out,18);u16(out,3);u16(out,2);u32(out,rate);u32(out,rate*8);u16(out,8);u16(out,32);u16(out,0);
    out.write("fact",4);u32(out,4);u32(out,static_cast<std::uint32_t>(audio.left.size()));
    out.write("data",4);u32(out,static_cast<std::uint32_t>(bytes));
    for(std::size_t n=0;n<audio.left.size();++n) for(double d:{audio.left[n],audio.right[n]}) {
        const float f=static_cast<float>(d);
        if(!std::isfinite(f)) throw std::runtime_error("WAV sample overflows float32");
        std::uint32_t bits;std::memcpy(&bits,&f,4);u32(out,bits);
    }
    if(!out) throw std::runtime_error("failed writing WAV");
}
}  // namespace ku100
