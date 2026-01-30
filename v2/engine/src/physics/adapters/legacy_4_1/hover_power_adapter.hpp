#pragma once
/*
================================================================================
Legacy 4.1 Adapter — Hover Power Model
FILE: v2/engine/src/physics/adapters/legacy_4_1/hover_power_adapter.hpp

Purpose:
  - Adapts legacy 4-1-drone hover power computation to v2 interface
  - Translates v2::physics types to/from lift::EvalSettings types
  - Contains ALL assumptions about legacy behavior
  - Fails loudly if inputs are invalid

ISOLATION RULES:
  - This file MAY include vendor headers (privately)
  - v2 public headers MUST NOT include vendor headers
  - All vendor symbols are contained within this adapter
================================================================================
*/

#include "v2/physics/interfaces/hover_power_model.hpp"

// VENDOR INCLUDES (private to this adapter)
#include "engine/physics/hover_momentum.hpp"
#include "engine/core/settings.hpp"

namespace v2::physics::adapters {

class LegacyHoverPowerAdapter : public HoverPowerModel {
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
    // Translate v2 types to legacy types
    lift::EvalSettings create_legacy_settings(
        const AtmosphereConditions& atmosphere,
        const RotorPerformance& rotor_perf) const;
    
    // Translate legacy result to v2 types
    HoverPowerResult translate_from_legacy(
        const lift::HoverMomentumResult& legacy_result) const;
};

} // namespace v2::physics::adapters
