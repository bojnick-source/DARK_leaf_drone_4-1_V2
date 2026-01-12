#pragma once
/*
================================================================================
Fragment 1.11 — Core: Design Schema (Canonical Candidate Aircraft Config)
FILE: cpp/engine/core/design.hpp

Purpose:
  - Define the single canonical "Design" representation used across:
      * optimization (GA/PSO/BO)
      * physics evaluation (hover/cruise/BEMT, mass/drag)
      * closeout reporting (Δmass, A_total, CdS, moments)
      * UI (3D rendering + summary dashboards)

Why you need this:
  - Without a locked schema, fragments drift and the code becomes paste-chaos.
  - The optimizer needs a stable param vector <-> struct mapping.

Hardening:
  - Explicit units (meters, kg, rad/s, etc.).
  - Deterministic validation via validate_or_throw().
  - Avoid optional/nullable pointer patterns for core fields.
  - Separate "geometry/layout" from "mass model knobs".

Notes:
  - Geometry kernels (PicoGK/OpenCascade) will later consume layout fields.
  - This schema supports multiple topologies: quad/hex/octo/coax/tandem/shrouded.
================================================================================
*/

#include <cstdint>
#include <string>
#include <vector>

#include "engine/core/errors.hpp"

namespace lift {

// Supported high-level architectures.
enum class Architecture : int {
  Multicopter_Open = 0,
  Multicopter_Shrouded = 1,
  Coaxial_Stacked = 2,
  Tandem_Twin = 3,
  Tiltrotor = 4,
  Other = 99
};

// Rotor placement in body frame (meters). Z is up.
struct RotorNode {
  double x_m = 0.0;
  double y_m = 0.0;
  double z_m = 0.0;

  // Rotor axis direction (unit vector) in body frame.
  // Default: +Z (vertical).
  double ax = 0.0;
  double ay = 0.0;
  double az = 1.0;

  // Rotor rotation direction (+1 or -1) for yaw torque modeling.
  int spin_dir = +1;
};

// Mass budget hooks used by the evaluator.
// These are not final CAD masses; they are modeling levers.
struct MassModel {
  double structural_kg = 0.0;         // frame/booms/sfcs
  double propulsion_kg = 0.0;         // motors/props/shrouds/gear
  double energy_kg = 0.0;             // battery or fuel+engine subsystem
  double avionics_kg = 0.0;           // flight computer/sensors/wiring
  double payload_interface_kg = 0.0;  // payload mounting hardware
  double misc_kg = 0.0;               // fasteners, fairings, etc.

  double total_kg() const {
    return structural_kg + propulsion_kg + energy_kg + avionics_kg + payload_interface_kg + misc_kg;
  }
};

// Aerodynamic “lumped” parameters (placeholder until geometry -> CdS).
struct AeroModel {
  double CdS_m2 = 0.0;       // parasite drag area
  double lift_to_drag = 0.0; // optional, for winged variants (0 means unused)
};

// Power system parameters (placeholder until detailed motor models).
struct PowerSystem {
  // Per-rotor max shaft power (W) and max continuous (W).
  double rotor_max_shaft_W = 0.0;
  double rotor_cont_shaft_W = 0.0;

  // Voltage class for bus sizing (V).
  double bus_voltage_V = 0.0;
};

// Core design definition.
struct Design {
  std::string name;

  Architecture arch = Architecture::Multicopter_Open;

  // Rotor geometry
  int rotor_count = 4;
  double rotor_radius_m = 0.0;      // single-rotor radius (m)
  double rotor_solidity = 0.0;      // blade area / disk area (0..1); used later in BEMT
  double rotor_tip_speed_mps = 0.0; // optional direct input (0 => derived from rpm)
  double rotor_rpm = 0.0;           // optional input (0 => derived)

  // Coaxial specifics
  bool is_coaxial = false;
  double coaxial_spacing_m = 0.0; // rotor-rotor axial separation if coax
  int coax_pairs = 0;             // number of coax stacks (if coaxial layout)

  // Shroud/duct flags
  bool has_shroud = false;
  double shroud_inner_radius_m = 0.0;
  double shroud_exit_area_ratio = 1.0; // Ae/Ainlet (>=1 typically), placeholder

  // Layout
  std::vector<RotorNode> nodes;

  // Models
  MassModel mass;
  AeroModel aero;
  PowerSystem power;

  // Validation
  void validate_or_throw() const {
    if (rotor_count <= 0 || rotor_count > 64) {
      throw ValidationError("Design: rotor_count outside sane bounds");
    }
    if (rotor_radius_m <= 0.0 || rotor_radius_m > 10.0) {
      throw ValidationError("Design: rotor_radius_m outside sane bounds");
    }
    if (rotor_solidity < 0.0 || rotor_solidity > 0.3) {
      // typical multicopter solidity is small; allow up to 0.3 as guard.
      throw ValidationError("Design: rotor_solidity outside sane bounds");
    }
    if (rotor_rpm < 0.0 || rotor_rpm > 20000.0) {
      throw ValidationError("Design: rotor_rpm outside sane bounds");
    }
    if (rotor_tip_speed_mps < 0.0 || rotor_tip_speed_mps > 350.0) {
      throw ValidationError("Design: rotor_tip_speed_mps outside sane bounds");
    }

    if (is_coaxial) {
      if (coax_pairs <= 0) throw ValidationError("Design: coax_pairs must be > 0 when is_coaxial");
      if (coaxial_spacing_m <= 0.0 || coaxial_spacing_m > 2.0) {
        throw ValidationError("Design: coaxial_spacing_m outside sane bounds");
      }
    }

    if (has_shroud) {
      if (shroud_inner_radius_m <= 0.0 || shroud_inner_radius_m < rotor_radius_m * 0.9) {
        // shroud inner should be >= rotor radius-ish; keep loose but safe.
        throw ValidationError("Design: shroud_inner_radius_m must be >= ~rotor_radius_m");
      }
      if (shroud_exit_area_ratio < 0.8 || shroud_exit_area_ratio > 5.0) {
        throw ValidationError("Design: shroud_exit_area_ratio outside sane bounds");
      }
    }

    if (!nodes.empty() && static_cast<int>(nodes.size()) != rotor_count) {
      throw ValidationError("Design: nodes.size() must equal rotor_count when nodes provided");
    }

    if (mass.total_kg() <= 0.0 || mass.total_kg() > 200.0) {
      throw ValidationError("Design: mass.total_kg outside sane bounds");
    }

    if (aero.CdS_m2 < 0.0 || aero.CdS_m2 > 20.0) {
      throw ValidationError("Design: aero.CdS_m2 outside sane bounds");
    }
    if (aero.lift_to_drag < 0.0 || aero.lift_to_drag > 50.0) {
      throw ValidationError("Design: aero.lift_to_drag outside sane bounds");
    }

    if (power.rotor_max_shaft_W < 0.0 || power.rotor_max_shaft_W > 500000.0) {
      throw ValidationError("Design: power.rotor_max_shaft_W outside sane bounds");
    }
    if (power.rotor_cont_shaft_W < 0.0 || power.rotor_cont_shaft_W > power.rotor_max_shaft_W) {
      throw ValidationError("Design: power.rotor_cont_shaft_W invalid");
    }
    if (power.bus_voltage_V < 0.0 || power.bus_voltage_V > 2000.0) {
      throw ValidationError("Design: power.bus_voltage_V outside sane bounds");
    }
  }

  // Convenience
  double aircraft_mass_kg() const { return mass.total_kg(); }
};

}  // namespace lift

