/*
================================================================================
Fragment 1.8 — Core: Deterministic Cache Keys (Implementation)
FILE: cpp/engine/core/cache_key.cpp

Implements:
  - hash_mission
  - hash_settings
  - make_cache_key
  - CacheKey::eval_id

Hardening:
  - All fields are hashed in a fixed order.
  - Enums hashed as underlying integers.
  - Floating values hashed via canonical bit patterns.
================================================================================
*/

#include "engine/core/cache_key.hpp"

#include <string>
#include <string_view>

namespace lift {
namespace {

static inline void add_tag(Fnv1a64& h, std::string_view tag) {
  // Tag + separator makes schema evolution detectable.
  h.update_string(tag);
  h.update_u8(0x1F);
}

}  // namespace

Hash64 hash_mission(const MissionSpec& m) {
  // Validate first so nonsensical configs don't enter caches.
  m.validate_or_throw();

  Fnv1a64 h;
  add_tag(h, "MissionSpec/v1");

  h.update_f64(m.max_aircraft_mass_kg);
  h.update_f64(m.min_payload_mass_kg);
  h.update_f64(m.target_ratio);

  h.update_f64(m.route_distance_m);
  h.update_f64(m.altitude_m);
  h.update_f64(m.preferred_time_s);

  h.update_f64(m.min_route_m);
  h.update_f64(m.max_route_m);
  h.update_f64(m.min_altitude_m);
  h.update_f64(m.max_altitude_m);

  h.update_bool(m.enforce_ratio_gate);

  return Hash64{h.value()};
}

Hash64 hash_settings(const EvalSettings& s) {
  s.validate_or_throw();

  Fnv1a64 h;
  add_tag(h, "EvalSettings/v1");

  // Fidelity
  h.update_enum(s.fidelity);

  // Atmosphere
  add_tag(h, "Atmosphere");
  h.update_f64(s.atmosphere.rho_kg_m3);
  h.update_bool(s.atmosphere.rho_is_override);

  // Rotor induced
  add_tag(h, "RotorInduced");
  h.update_f64(s.rotor.hover_FM);
  h.update_f64(s.rotor.induced_k);
  h.update_f64(s.rotor.max_tip_mach);

  // Powertrain
  add_tag(h, "Powertrain");
  h.update_f64(s.power.motor_eff);
  h.update_f64(s.power.esc_eff);
  h.update_f64(s.power.mech_eff);
  h.update_f64(s.power.electrical_bus_eff);
  h.update_f64(s.power.sfc_kg_per_kwh);

  // Numerical
  add_tag(h, "Numerics");
  h.update_f64(s.numerics.eps);
  h.update_i32(s.numerics.max_iter);
  h.update_f64(s.numerics.tol);

  // Optimizer
  add_tag(h, "Optimizer");
  h.update_u64(s.optimizer.seed);
  h.update_i32(s.optimizer.eval_budget);
  h.update_i32(s.optimizer.population);

  // Closeout gates (analysis layer thresholds)
  add_tag(h, "CloseoutGates");
  h.update_f64(s.gates.max_added_mass_kg);
  h.update_f64(s.gates.min_disk_area_m2);
  h.update_f64(s.gates.min_cruise_power_reduction_frac);
  h.update_f64(s.gates.min_control_margin);

  return Hash64{h.value()};
}

std::string CacheKey::eval_id() const {
  return std::string("m_") + mission_hex() +
         "__s_" + settings_hex() +
         "__g_" + geom_hex() +
         "__e_" + combined_hex();
}

CacheKey make_cache_key(const MissionSpec& m, const EvalSettings& s, Hash64 geom_h) {
  CacheKey k;
  k.mission_h = hash_mission(m);
  k.settings_h = hash_settings(s);
  k.geom_h = geom_h;

  // Combine deterministically
  Hash64 ms = hash_combine(k.mission_h, k.settings_h);
  k.combined_h = hash_combine(ms, k.geom_h);

  return k;
}

}  // namespace lift
