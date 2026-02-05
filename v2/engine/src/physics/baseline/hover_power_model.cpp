/*
================================================================================
v2 Physics Baseline — Hover Power Model Implementation
FILE: v2/engine/src/physics/baseline/hover_power_model.cpp
================================================================================
*/

#include "physics/baseline/hover_power_model.hpp"

#include <cmath>
#include <stdexcept>

namespace v2::physics::baseline {

namespace {
inline void validate_inputs(double thrust_N,
                            double A_total_m2,
                            const AtmosphereConditions& atmosphere,
                            const RotorPerformance& rotor_perf) {
    if (thrust_N <= 0.0) {
        throw std::invalid_argument("HoverPowerModel: thrust_N must be > 0");
    }
    if (A_total_m2 <= 0.0) {
        throw std::invalid_argument("HoverPowerModel: A_total_m2 must be > 0");
    }
    if (atmosphere.rho_kg_m3 <= 0.0) {
        throw std::invalid_argument("HoverPowerModel: rho_kg_m3 must be > 0");
    }
    if (!(rotor_perf.hover_FM > 0.0 && rotor_perf.hover_FM <= 1.0)) {
        throw std::invalid_argument("HoverPowerModel: hover_FM must be in (0,1]");
    }
    if (rotor_perf.induced_k < 1.0) {
        throw std::invalid_argument("HoverPowerModel: induced_k must be >= 1.0");
    }
}
}

HoverPowerResult HoverPowerModel::compute_power(
    double thrust_N,
    double A_total_m2,
    const AtmosphereConditions& atmosphere,
    const RotorPerformance& rotor_perf) const {
    validate_inputs(thrust_N, A_total_m2, atmosphere, rotor_perf);

    HoverPowerResult result;
    result.thrust_N = thrust_N;
    result.A_total_m2 = A_total_m2;
    result.rho_used_kg_m3 = atmosphere.rho_kg_m3;
    result.FM_used = rotor_perf.hover_FM;

    result.disk_loading_N_per_m2 = thrust_N / A_total_m2;

    const double denom = std::sqrt(2.0 * result.rho_used_kg_m3 * A_total_m2);
    const double T32 = thrust_N * std::sqrt(thrust_N);
    result.P_induced_ideal_W = T32 / denom;

    result.P_induced_W = result.P_induced_ideal_W * rotor_perf.induced_k;
    result.P_total_W = result.P_induced_W / result.FM_used;

    return result;
}

HoverPowerResult HoverPowerModel::compute_power_sized(
    double thrust_N,
    double A_total_m2,
    const AtmosphereConditions& atmosphere,
    const RotorPerformance& rotor_perf,
    double reserve_mult) const {
    if (reserve_mult < 1.0 || reserve_mult > 3.0) {
        throw std::invalid_argument("HoverPowerModel: reserve_mult must be in [1,3]");
    }

    auto result = compute_power(thrust_N, A_total_m2, atmosphere, rotor_perf);
    result.P_total_W *= reserve_mult;
    result.P_induced_W *= reserve_mult;
    result.P_induced_ideal_W *= reserve_mult;
    return result;
}

} // namespace v2::physics::baseline
