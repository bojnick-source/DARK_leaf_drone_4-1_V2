#pragma once
/*
================================================================================
Legacy 4.1 Adapter — Hover Power Model
FILE: v2/engine/src/physics/adapters/legacy_4_1/hover_power_adapter.hpp
================================================================================
*/

#include "v2/physics/interfaces/hover_power_model.hpp"

// VENDOR INCLUDES (private to this adapter)
#include "engine/physics/hover_momentum.hpp"
#include "engine/core/settings.hpp"

namespace v2::physics::adapters {

class LegacyHoverPowerAdapter final : public v2::physics::HoverPowerModel {
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

private:
    lift::EvalSettings create_legacy_settings(
        const AtmosphereConditions& atmosphere,
        const RotorPerformance& rotor_perf) const;

    HoverPowerResult translate_from_legacy(
        const lift::HoverMomentumResult& legacy_result) const;
};

} // namespace v2::physics::adapters