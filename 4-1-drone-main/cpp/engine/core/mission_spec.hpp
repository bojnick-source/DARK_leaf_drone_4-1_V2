#pragma once
/*
================================================================================
Fragment 1.3 — Core: Mission Specification (Hardened)
FILE: cpp/engine/core/mission_spec.hpp

Purpose:
  - Encode the DARPA LIFT mission in a deterministic, validation-first structure.
  - Provide a single source of truth for:
      * Payload requirement
      * Max aircraft mass
      * Route / distance
      * Altitude band
      * Scoring/time preferences (where applicable)

Scope:
  - This is mission *data* + validation rules (not the full simulator).
  - Used by: cache keys, feasibility gates, sizing routines, reporting.

Hardening:
  - validate_or_throw provides explicit, actionable failures (throws ValidationError).
  - Units are explicit (meters, seconds, kg).
  - Defaults are conservative and editable in one place.

Note:
  - If you later ingest a rules PDF, keep THIS struct as the canonical internal
    representation, and write a translator/loader that populates it.
================================================================================
*/

#include <cstdint>
#include <string>

#include "engine/core/errors.hpp"
#include "engine/core/units.hpp"

namespace lift {

// ---------------------------- MissionSpec -------------------------------------
struct MissionSpec {
  // Core constraints
  double max_aircraft_mass_kg = 24.948;      // 55 lb (approx), keep kg internal
  double min_payload_mass_kg  = 49.895;      // 110 lb (approx)
  double target_ratio         = 4.0;         // payload / aircraft

  // Mission geometry
  double route_distance_m     = 5.0 * units::nmi_to_m;  // 5 nmi
  double altitude_m           = 350.0 * units::ft_to_m; // 350 ft nominal band/target

  // Optional scoring knobs (not mandatory constraints)
  double preferred_time_s     = 30.0 * 60.0;     // < 30 min preference

  // Validation gates: strict sanity limits (prevent nonsense)
  double min_route_m          = 100.0;
  double max_route_m          = 200.0 * units::nmi_to_m;
  double min_altitude_m       = 0.0;
  double max_altitude_m       = 3000.0 * units::ft_to_m;

  // If true: require payload ratio >= target_ratio (in addition to min payload).
  bool enforce_ratio_gate     = true;

  // -------------------------- Validation --------------------------------------
  void validate_or_throw() const {
    if (max_aircraft_mass_kg <= 0.0) {
      throw ValidationError("MissionSpec: max_aircraft_mass_kg must be > 0");
    }
    if (min_payload_mass_kg <= 0.0) {
      throw ValidationError("MissionSpec: min_payload_mass_kg must be > 0");
    }
    if (target_ratio <= 0.0) {
      throw ValidationError("MissionSpec: target_ratio must be > 0");
    }

    if (route_distance_m < min_route_m || route_distance_m > max_route_m) {
      throw ValidationError("MissionSpec: route_distance_m outside sanity bounds");
    }
    if (altitude_m < min_altitude_m || altitude_m > max_altitude_m) {
      throw ValidationError("MissionSpec: altitude_m outside sanity bounds");
    }
  }

  // Convenience for consistent defaults.
  static MissionSpec darpa_lift_default() {
    MissionSpec m;
    return m;
  }
};

}  // namespace lift
