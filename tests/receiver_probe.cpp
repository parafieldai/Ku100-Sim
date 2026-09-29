// Standalone test-only adapter for receiver.cpp. No physics source is linked.
#include "receiver.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
std::vector<double> read_vector(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("cannot open test signal");
    std::vector<double> out;
    std::string word;
    while (in >> word) out.push_back(std::stod(word));
    return out;
}
void vector_json(const std::vector<double>& value) {
    std::cout << '[';
    for (std::size_t n=0; n<value.size(); ++n) {
        if(n) std::cout << ',';
        std::cout << value[n];
    }
    std::cout << ']';
}
void stereo_json(const ku100::StereoSignal& value) {
    std::cout << "{\"left\":"; vector_json(value.left);
    std::cout << ",\"right\":"; vector_json(value.right);
    std::cout << '}';
}
}

int main(int argc, char** argv) {
    try {
        std::cout << std::setprecision(17);
        if (argc < 2) throw std::invalid_argument("probe operation required");
        const std::string operation=argv[1];
        if(operation=="load" && argc==3) {
            const auto bank=ku100::HrirBank::load(argv[2]);
            std::cout << "{\"rate\":" << bank.sample_rate() << ",\"directions\":" << bank.directions()
                      << ",\"taps\":" << bank.taps() << ",\"radii\":";
            vector_json(bank.radii()); std::cout << '}';
        } else if(operation=="at" && argc==5) {
            const auto bank=ku100::HrirBank::load(argv[2]);
            const auto ir=bank.at(std::stod(argv[3]), std::stod(argv[4]));
            stereo_json({ir[0],ir[1]});
        } else if(operation=="convolve" && argc==4) {
            vector_json(ku100::convolve(read_vector(argv[2]),read_vector(argv[3])));
        } else if(operation=="decimate" && argc==5) {
            const unsigned input=static_cast<unsigned>(std::stoul(argv[2]));
            const unsigned output=static_cast<unsigned>(std::stoul(argv[3]));
            const auto signal=read_vector(argv[4]);
            const auto result=ku100::decimate(signal,input,output);
            std::cout << "{\"delay_s\":" << ku100::decimation_delay_s(input,output) << ",\"samples\":";
            vector_json(result); std::cout << '}';
        } else if(operation=="delay" && argc==4) {
            vector_json(ku100::delay_signal(read_vector(argv[3]),std::stod(argv[2])));
        } else if(operation=="airborne" && argc==7) {
            const auto bank=ku100::HrirBank::load(argv[2]);
            stereo_json(ku100::render_airborne(read_vector(argv[6]),bank,std::stod(argv[3]),
                                             std::stod(argv[4]),std::stod(argv[5])));
        } else if(operation=="wav" && argc==6) {
            const ku100::StereoSignal signal{read_vector(argv[4]),read_vector(argv[5])};
            ku100::write_float_wav(argv[2],signal,static_cast<unsigned>(std::stoul(argv[3])));
            std::cout << "{\"written\":true}";
        } else {
            throw std::invalid_argument("incorrect probe operation/arguments");
        }
        std::cout << '\n';
        return 0;
    } catch(const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 2;
    }
}
