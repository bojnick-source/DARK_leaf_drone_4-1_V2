#pragma once
/*
================================================================================
Fragment 1.14 — Physics: Hover Power Model (Momentum Theory Baseline)
FILE: cpp/engine/physics/hover_momentum.hpp

Purpose:
  - Provide a fast, deterministic hover power model used for:
      * screening candidate designs
      * induced-power sensitivity (disk area scaling)
      * closeout computations (A_total, DL, P_hover_1g, P_sized)

Model:
  - Ideal induced power: P_i = T^(3/2) / sqrt(2*rho*A)
  - Loss multiplier: induced_k (>=1)
  - Figure of merit FM folds profile + misc losses:
      P_actual = P_ideal * induced_k / FM

Notes:
  - Coaxial stacks do NOT double disk area if they share the same footprint.
    The effective disk area is the inlet area, not sum of stages.
    This function takes effective A_total as an input, so the caller must compute
    A_total correctly for each concept.

Hardening:
  - Input validation and explicit units.
  - Returns both induced-only and total (with FM).
================================================================================
*/

#include "engine/core/errors.hpp"
#include "engine/core/settings.hpp"

namespace lift {

// Hover results for a single evaluation point.
struct HoverMomentumResult {
  double thrust_N = 0.0;
  double A_total_m2 = 0.0;
  double disk_loading_N_per_m2 = 0.0;

  double P_induced_ideal_W = 0.0;
  double P_induced_W = 0.0;      // with induced_k
  double P_total_W = 0.0;        // with FM

  double FM_used = 0.0;
  double rho_used = 0.0;
};

// Compute hover power for required thrust and effective total disk area.
HoverMomentumResult hover_momentum_power(double thrust_N,
                                         double A_total_m2,
                                         const EvalSettings& settings);

// Convenience: sized power including reserve multiplier.
// reserve_mult = 1.0 means no reserve; 1.2 means 20% margin.
HoverMomentumResult hover_momentum_power_sized(double thrust_N,
                                               double A_total_m2,
                                               const EvalSettings& settings,
                                               double reserve_mult);

}  // namespace lift

