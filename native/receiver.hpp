#pragma once
#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace ku100 {
struct StereoSignal {
    std::vector<double> left, right;
};

// The bank contains the published horizontal measurements after the authors'
// distance corrections. It is not a contact or sub-25-cm transfer model.
class HrirBank {
public:
    static HrirBank load(const std::string& path);
    std::array<std::vector<double>, 2> at(double azimuth_deg, double radius_m) const;
    unsigned sample_rate() const { return rate_; }
    unsigned taps() const { return taps_; }
    unsigned directions() const { return directions_; }
    const std::vector<double>& radii() const { return radii_; }
private:
    unsigned rate_ = 0, directions_ = 0, taps_ = 0;
    std::vector<double> radii_;
    std::vector<float> ir_;
};

// All operations preserve their causal convolution tail. The output is never
// independently normalized, clipped, or adjusted per ear.
std::vector<double> convolve(const std::vector<double>& signal,
                             const std::vector<double>& fir);
std::vector<double> decimate(const std::vector<double>& signal,
                            unsigned input_rate, unsigned output_rate = 48000);
double decimation_delay_s(unsigned input_rate, unsigned output_rate = 48000);
std::vector<double> delay_signal(const std::vector<double>& signal,
                                double delay_samples);
StereoSignal render_airborne(const std::vector<double>& pressure_at_reference,
                            const HrirBank& bank, double azimuth_deg,
                            double radius_m, double sound_speed_m_s = 343.0);
void write_float_wav(const std::string& path, const StereoSignal& audio,
                     unsigned rate);
}  // namespace ku100
