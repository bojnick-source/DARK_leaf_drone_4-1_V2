#include "engine/physics/hover_momentum.hpp"

#include <cmath>

namespace lift {

static inline void validate_inputs(double thrust_N, double A_total_m2, const EvalSettings& s) {
  if (!(thrust_N > 0.0)) throw ValidationError("hover_momentum: thrust_N must be > 0");
  if (!(A_total_m2 > 0.0)) throw ValidationError("hover_momentum: A_total_m2 must be > 0");
  s.validate_or_throw();
}

HoverMomentumResult hover_momentum_power(double thrust_N,
                                         double A_total_m2,
                                         const EvalSettings& settings) {
  validate_inputs(thrust_N, A_total_m2, settings);

  HoverMomentumResult r;
  r.thrust_N = thrust_N;
  r.A_total_m2 = A_total_m2;

  r.rho_used = settings.atmosphere.rho_kg_m3;
  r.FM_used  = settings.rotor.hover_FM;

  r.disk_loading_N_per_m2 = thrust_N / A_total_m2;

  // Ideal induced power from momentum theory:
  // P_i = T^(3/2) / sqrt(2 rho A)
  const double denom = std::sqrt(2.0 * r.rho_used * A_total_m2);
  const double T32 = thrust_N * std::sqrt(thrust_N);

  r.P_induced_ideal_W = T32 / denom;

  // Apply induced loss factor
  r.P_induced_W = r.P_induced_ideal_W * settings.rotor.induced_k;

  // Apply FM to estimate total hover power
  if (!(r.FM_used > 0.0 && r.FM_used <= 1.0)) {
    throw ValidationError("hover_momentum: settings.rotor.hover_FM invalid");
  }
  r.P_total_W = r.P_induced_W / r.FM_used;

  return r;
}

HoverMomentumResult hover_momentum_power_sized(double thrust_N,
                                               double A_total_m2,
                                               const EvalSettings& settings,
                                               double reserve_mult) {
  if (!(reserve_mult >= 1.0 && reserve_mult <= 3.0)) {
    throw ValidationError("hover_momentum_sized: reserve_mult must be in [1,3]");
  }
  auto r = hover_momentum_power(thrust_N, A_total_m2, settings);
  r.P_total_W *= reserve_mult;
  r.P_induced_W *= reserve_mult;
  r.P_induced_ideal_W *= reserve_mult;
  return r;
}

}  // namespace lift
