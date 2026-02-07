#pragma once
/*
================================================================================
Legacy 4.1 — Physics: Hover Power Model (Momentum Theory Baseline)
FILE: engine/physics/hover_momentum.hpp
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