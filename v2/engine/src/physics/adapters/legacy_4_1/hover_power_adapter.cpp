/*
================================================================================
Legacy 4.1 Adapter — Hover Power Model Implementation
FILE: v2/engine/src/physics/adapters/legacy_4_1/hover_power_adapter.cpp
================================================================================
*/

#include "hover_power_adapter.hpp"
#include <stdexcept>

namespace v2::physics::adapters {

lift::EvalSettings LegacyHoverPowerAdapter::create_legacy_settings(
    const AtmosphereConditions& atmosphere,
    const RotorPerformance& rotor_perf) const {
    
    // Validate v2 inputs
    if (atmosphere.rho_kg_m3 <= 0.0) {
        throw std::invalid_argument("LegacyHoverPowerAdapter: rho_kg_m3 must be > 0");
    }
    if (rotor_perf.hover_FM <= 0.0 || rotor_perf.hover_FM > 1.0) {
        throw std::invalid_argument("LegacyHoverPowerAdapter: hover_FM must be in (0,1]");
    }
    if (rotor_perf.induced_k < 1.0) {
        throw std::invalid_argument("LegacyHoverPowerAdapter: induced_k must be >= 1.0");
    }
    
    // Create legacy EvalSettings with minimal required fields
    lift::EvalSettings settings;
    settings.atmosphere.rho_kg_m3 = atmosphere.rho_kg_m3;
    settings.rotor.hover_FM = rotor_perf.hover_FM;
    settings.rotor.induced_k = rotor_perf.induced_k;
    
    // Set reasonable defaults for other fields (already set by EvalSettings defaults)
    settings.rotor.max_tip_mach = 0.65;
    settings.power.motor_eff = 0.92;
    settings.power.esc_eff = 0.98;
    settings.power.mech_eff = 0.99;
    
    return settings;
}

HoverPowerResult LegacyHoverPowerAdapter::translate_from_legacy(
    const lift::HoverMomentumResult& legacy_result) const {
    
    HoverPowerResult result;
    result.thrust_N = legacy_result.thrust_N;
    result.A_total_m2 = legacy_result.A_total_m2;
    result.disk_loading_N_per_m2 = legacy_result.disk_loading_N_per_m2;
    result.P_induced_ideal_W = legacy_result.P_induced_ideal_W;
    result.P_induced_W = legacy_result.P_induced_W;
    result.P_total_W = legacy_result.P_total_W;
    result.FM_used = legacy_result.FM_used;
    result.rho_used_kg_m3 = legacy_result.rho_used;
    
    return result;
}

HoverPowerResult LegacyHoverPowerAdapter::compute_power(
    double thrust_N,
    double A_total_m2,
    const AtmosphereConditions& atmosphere,
    const RotorPerformance& rotor_perf) const {
    
    try {
        // Validate inputs
        if (thrust_N <= 0.0) {
            throw std::invalid_argument("LegacyHoverPowerAdapter: thrust_N must be > 0");
        }
        if (A_total_m2 <= 0.0) {
            throw std::invalid_argument("LegacyHoverPowerAdapter: A_total_m2 must be > 0");
        }
        
        // Create legacy settings
        lift::EvalSettings legacy_settings = create_legacy_settings(atmosphere, rotor_perf);
        
        // Call legacy computation
        lift::HoverMomentumResult legacy_result = 
            lift::hover_momentum_power(thrust_N, A_total_m2, legacy_settings);
        
        // Translate result
        return translate_from_legacy(legacy_result);
        
    } catch (const lift::ValidationError& e) {
        // Re-throw legacy validation errors as std::invalid_argument
        throw std::invalid_argument(std::string("Legacy validation failed: ") + e.what());
    }
}

HoverPowerResult LegacyHoverPowerAdapter::compute_power_sized(
    double thrust_N,
    double A_total_m2,
    const AtmosphereConditions& atmosphere,
    const RotorPerformance& rotor_perf,
    double reserve_mult) const {
    
    try {
        // Validate inputs
        if (thrust_N <= 0.0) {
            throw std::invalid_argument("LegacyHoverPowerAdapter: thrust_N must be > 0");
        }
        if (A_total_m2 <= 0.0) {
            throw std::invalid_argument("LegacyHoverPowerAdapter: A_total_m2 must be > 0");
        }
        if (reserve_mult < 1.0 || reserve_mult > 3.0) {
            throw std::invalid_argument("LegacyHoverPowerAdapter: reserve_mult must be in [1,3]");
        }
        
        // Create legacy settings
        lift::EvalSettings legacy_settings = create_legacy_settings(atmosphere, rotor_perf);
        
        // Call legacy computation with sizing
        lift::HoverMomentumResult legacy_result = 
            lift::hover_momentum_power_sized(thrust_N, A_total_m2, legacy_settings, reserve_mult);
        
        // Translate result
        return translate_from_legacy(legacy_result);
        
    } catch (const lift::ValidationError& e) {
        // Re-throw legacy validation errors as std::invalid_argument
        throw std::invalid_argument(std::string("Legacy validation failed: ") + e.what());
    }
}

} // namespace v2::physics::adapters
