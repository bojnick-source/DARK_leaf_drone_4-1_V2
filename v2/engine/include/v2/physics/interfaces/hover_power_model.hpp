#pragma once
/*
================================================================================
v2 Physics Interface — Hover Power Model
FILE: v2/engine/include/v2/physics/interfaces/hover_power_model.hpp

Purpose:
  - Abstract interface for hover power computation
  - Based on momentum theory with configurable loss factors
  - Used for screening candidates and closeout computations

This interface defines the contract for hover power computation.
Implementations may use different fidelity levels (momentum theory, BEMT, CFD, etc.)
================================================================================
*/

#include "v2/physics/types.hpp"

namespace v2::physics {

class HoverPowerModel {
public:
    virtual ~HoverPowerModel() = default;
    
    /**
     * Compute hover power for required thrust and effective total disk area.
     * 
     * @param thrust_N Required thrust in Newtons
     * @param A_total_m2 Effective total disk area in m²
     * @param atmosphere Atmosphere conditions
     * @param rotor_perf Rotor performance parameters
     * @return HoverPowerResult with P_total_W and breakdown
     * @throws std::invalid_argument if inputs are invalid
     */
    virtual HoverPowerResult compute_power(
        double thrust_N,
        double A_total_m2,
        const AtmosphereConditions& atmosphere,
        const RotorPerformance& rotor_perf) const = 0;
    
    /**
     * Compute hover power with sizing reserve multiplier.
     * 
     * @param thrust_N Required thrust in Newtons
     * @param A_total_m2 Effective total disk area in m²
     * @param atmosphere Atmosphere conditions
     * @param rotor_perf Rotor performance parameters
     * @param reserve_mult Reserve multiplier (1.0 = no reserve, 1.2 = 20% margin)
     * @return HoverPowerResult with P_total_W and breakdown (including reserve)
     * @throws std::invalid_argument if inputs are invalid
     */
    virtual HoverPowerResult compute_power_sized(
        double thrust_N,
        double A_total_m2,
        const AtmosphereConditions& atmosphere,
        const RotorPerformance& rotor_perf,
        double reserve_mult) const = 0;
};

} // namespace v2::physics
