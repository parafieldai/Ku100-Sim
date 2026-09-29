#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace ku100 {
// SI-valued generic bilateral contact fixture. This is not a KU100 material or
// internal-geometry specification. No microphone gain or measured HRIR is used.
struct PhysicsParams {
    unsigned sample_rate = 192000;
    double duration_s = 4.0;
    unsigned modes_per_plate = 128;
    std::uint64_t seed = 1;
    std::string action = "stroke"; // stroke, press, tap, silence
    std::string side = "left";     // left, right
    double load_n = 0.01;
    double speed_m_s = 0.035;
    double wetness = 0.0;          // 0..1, fixed for a render
    double contact_radius_m = 0.004;
    double roughness_rms_m = 2e-6;
    double plate_width_m = 0.060;
    double plate_height_m = 0.085;
    double plate_thickness_m = 0.003;
    double young_modulus_pa = 1.2e6;
    double poisson_ratio = 0.45;
    double density_kg_m3 = 1100.0;
    double modal_loss_ratio = 0.025;
    double cavity_volume_m3 = 8e-5;
    double duct_length_m = 0.18;
    double duct_radius_m = 0.003;
    unsigned duct_cells = 32;     // distributed 1D acoustic line
    double vent_length_m = 0.025;
    double vent_radius_m = 0.001;
    double contact_stiffness_n_m15 = 18000.0;
    double contact_damping_n_s_m = 0.08;
    double friction_coefficient = 0.6;
    double friction_velocity_m_s = 0.002;
    double film_thickness_m = 8e-5;
    double film_viscosity_pa_s = 0.001;
    double air_density_kg_m3 = 1.204;
    double sound_speed_m_s = 343.0;
    double air_viscosity_pa_s = 1.81e-5;
    unsigned trace_stride = 192;
};

struct PhysicsTrace {
    double time_s = 0.0;
    double normal_force_n = 0.0;
    double tangential_force_n = 0.0;
    double indentation_m = 0.0;
    double stored_energy_j = 0.0;
    double actuator_work_j = 0.0;
    double dissipated_energy_j = 0.0;
    double energy_residual_j = 0.0;
    double local_pressure_left_pa = 0.0;
    double local_pressure_right_pa = 0.0;
    double sliding_distance_m = 0.0;
};

struct PhysicsStats {
    double initial_energy_j = 0.0;
    double final_energy_j = 0.0;
    double actuator_work_j = 0.0;
    double dissipated_energy_j = 0.0;
    double max_energy_residual_j = 0.0;
    double max_contact_solve_residual_n = 0.0;
    double max_normal_force_n = 0.0;
    double max_indentation_m = 0.0;
    double max_contact_point_displacement_m = 0.0;
    double max_plate_displacement_bound_m = 0.0;
    double max_displacement_thickness_ratio = 0.0;
    double max_vent_mach = 0.0;
    double max_vent_reynolds = 0.0;
    double max_duct_mach = 0.0;
    double max_duct_reynolds = 0.0;
    double min_mode_hz = 0.0;
    double max_mode_hz = 0.0;
    unsigned max_solver_iterations = 0;
    unsigned retained_modes_per_plate = 0;
    bool finite = true;
    // Conservative small-signal/laminar screens, not device calibration or a
    // guarantee of spatial/bandwidth/constitutive accuracy.
    bool regime_valid = true;
    std::vector<std::string> regime_warnings;
};

struct PhysicsResult {
    unsigned sample_rate = 0;
    std::vector<double> local_pressure_left_pa;
    std::vector<double> local_pressure_right_pa;
    // Equivalent free-field monopole pressure at 0.25 m, excluding delay.
    // These are separate airborne observations, not contact-ear crossfeed.
    std::vector<double> airborne_pressure_left_at_025m_pa;
    std::vector<double> airborne_pressure_right_at_025m_pa;
    std::vector<PhysicsTrace> trace;
    PhysicsStats stats;
};

void validate_physics_params(const PhysicsParams& params);
PhysicsResult simulate(const PhysicsParams& params);
} // namespace ku100
