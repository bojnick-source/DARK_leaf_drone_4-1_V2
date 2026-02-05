#pragma once
/*
================================================================================
v2 Physics Baseline — Hover Power Model
FILE: v2/engine/src/physics/baseline/hover_power_model.hpp

Purpose:
  - Baseline (non-legacy) hover power computation
  - Deterministic momentum-theory implementation
================================================================================
*/

#include "v2/physics/interfaces/hover_power_model.hpp"

namespace v2::physics::baseline {

class HoverPowerModel final : public v2::physics::HoverPowerModel {
public:
    HoverPowerResult compute_power(
        double thrust_N,
        double A_total_m2,
        const AtmosphereConditions& atmosphere,
        const RotorPerformance& rotor_perf) const override;

    HoverPowerResult compute_power_sized(
        double thrust_N,
        double A_total_m2,
        const AtmosphereConditions& atmosphere,
        const RotorPerformance& rotor_perf,
        double reserve_mult) const override;
};

} // namespace v2::physics::baseline
