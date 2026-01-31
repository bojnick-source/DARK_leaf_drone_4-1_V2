#pragma once
/*
================================================================================
Fragment 1.4 — Core: Evaluation + Physics Settings (Hardened)
FILE: cpp/engine/core/settings.hpp

Purpose:
  - Centralize all evaluation assumptions (physics knobs, efficiencies, sizing
    margins, numerical tolerances) into a single validated object.
  - Ensure deterministic results and stable caching: ANY change here should
    change the evaluation hash (done later in cache_key).

Why this exists:
  - The engine must compare designs fairly. That requires locking:
      * Atmosphere assumptions (rho)
      * Rotor performance (FM / inflow losses)
      * Propulsive efficiencies
      * Sizing margins / reserves
      * Numerical tolerances (to prevent "optimizer lies")

Hardening:
  - validate_or_throw() catches nonsensical values early.
  - Explicit units and conservative defaults.
  - Separate "physics assumptions" from "optimizer parameters".

Links to your “exhaustive closeout” checklist:
  - This file defines the knobs that drive:
      * induced power sensitivity (rho, FM)
      * cruise power (CdS assumptions live in analysis layer later)
      * GO/NO-GO gates (thresholds stored here; applied in analysis/closeout_eval)
================================================================================
*/

#include <cstdint>
#include <string>

#include "engine/core/errors.hpp"

namespace lift {

// ----------------------------- Fidelity --------------------------------------
// Used for multi-fidelity optimization (fast screening -> higher fidelity).
enum class Fidelity : int {
  F0_FAST = 0,     // very fast approximations, coarse penalties
  F1_MED  = 1,     // mid-fidelity hover + cruise estimates
  F2_HIGH = 2      // higher-fidelity (e.g., BEMT hover + better drag model)
};

// ----------------------------- Atmosphere ------------------------------------
struct AtmosphereSettings {
  // Air density (kg/m^3). Standard sea level ~1.225
  double rho_kg_m3 = 1.225;

  // Optional: if later you add ISA model, this becomes an override.
  bool rho_is_override = true;

  void validate_or_throw() const {
    if (rho_kg_m3 < 0.5 || rho_kg_m3 > 1.6) {
      throw ValidationError("AtmosphereSettings: rho_kg_m3 outside sane bounds");
    }
  }
};

// ----------------------------- Rotor/Induced ---------------------------------
struct RotorInducedSettings {
  // Figure of merit (FM) for hover/low-speed induced power scaling.
  // Typical range 0.6–0.8; conservative default 0.75.
  double hover_FM = 0.75;

  // Induced power multiplier "k_i" (>=1). Used in momentum-theory + losses.
  double induced_k = 1.15;

  // Tip Mach guard (for rotor sizing checks; not a strict rule constraint).
  double max_tip_mach = 0.65;

  void validate_or_throw() const {
    if (hover_FM <= 0.0 || hover_FM > 1.0) {
      throw ValidationError("RotorInducedSettings: hover_FM must be (0,1]");
    }
    if (induced_k < 1.0 || induced_k > 2.5) {
      throw ValidationError("RotorInducedSettings: induced_k outside sane bounds");
    }
    if (max_tip_mach < 0.2 || max_tip_mach > 0.9) {
      throw ValidationError("RotorInducedSettings: max_tip_mach outside sane bounds");
    }
  }
};

// ----------------------------- Powertrain ------------------------------------
struct PowertrainSettings {
  // Motor electrical efficiency (0..1)
  double motor_eff = 0.92;

  // ESC efficiency (0..1)
  double esc_eff = 0.98;

  // Mechanical transmission efficiency (0..1). For direct drive set ~1.0.
  double mech_eff = 0.99;

  // Battery discharge efficiency / wiring efficiency (0..1)
  double electrical_bus_eff = 0.98;

  // Optional: for hybrid fuel-based modeling (kg/kWh).
  // Set to 0 to disable fuel mass modeling at this layer.
  double sfc_kg_per_kwh = 0.0;

  void validate_or_throw() const {
    auto in01 = [](double x) { return x > 0.0 && x <= 1.0; };
    if (!in01(motor_eff))          throw ValidationError("PowertrainSettings: motor_eff must be (0,1]");
    if (!in01(esc_eff))            throw ValidationError("PowertrainSettings: esc_eff must be (0,1]");
    if (!in01(mech_eff))           throw ValidationError("PowertrainSettings: mech_eff must be (0,1]");
    if (!in01(electrical_bus_eff)) throw ValidationError("PowertrainSettings: electrical_bus_eff must be (0,1]");
    if (sfc_kg_per_kwh < 0.0 || sfc_kg_per_kwh > 2.0) {
      throw ValidationError("PowertrainSettings: sfc_kg_per_kwh outside sane bounds");
    }
  }

  // Combined efficiency for converting shaft power -> source power.
  double total_eff() const {
    return motor_eff * esc_eff * mech_eff * electrical_bus_eff;
  }
};

// ----------------------------- Numerical -------------------------------------
struct NumericalSettings {
  // Generic epsilon for comparisons
  double eps = 1e-9;

  // Max iterations for inner solvers (BEMT, trim, etc.)
  int max_iter = 200;

  // Convergence tolerance for inner solvers
  double tol = 1e-6;

  void validate_or_throw() const {
    if (eps <= 0.0 || eps > 1e-3) {
      throw ValidationError("NumericalSettings: eps outside sane bounds");
    }
    if (max_iter < 10 || max_iter > 20000) {
      throw ValidationError("NumericalSettings: max_iter outside sane bounds");
    }
    if (tol <= 0.0 || tol > 1e-2) {
      throw ValidationError("NumericalSettings: tol outside sane bounds");
    }
  }
};

// ----------------------------- Optimizer -------------------------------------
struct OptimizerSettings {
  // Random seed to ensure deterministic runs.
  uint64_t seed = 1;

  // Hard cap on evaluations per run (used by GA/PSO/BO).
  int eval_budget = 200000;

  // Population/swarm size suggestions (algorithm may ignore if not applicable).
  int population = 256;

  void validate_or_throw() const {
    if (eval_budget < 1 || eval_budget > 100000000) {
      throw ValidationError("OptimizerSettings: eval_budget outside sane bounds");
    }
    if (population < 4 || population > 100000) {
      throw ValidationError("OptimizerSettings: population outside sane bounds");
    }
  }
};

// ----------------------------- Closeout Gates --------------------------------
// These gates encode your "numerical GO/NO-GO threshold definitions".
// They do NOT decide feasibility alone; they define required margins.
struct CloseoutGates {
  // Mass delta gate: a concept change is only acceptable if added mass <= this.
  // (Used when comparing variants / refits vs a baseline.)
  double max_added_mass_kg = 2.0;

  // Disk area gate: require at least this much effective disk area (m^2).
  double min_disk_area_m2 = 0.0;  // 0 = no gate (set later when you lock D6)

  // Cruise power improvement gate: require at least this fractional reduction.
  // Example: 0.10 means >=10% cruise power reduction to justify added parts.
  double min_cruise_power_reduction_frac = 0.0;

  // Control authority margin gate: require torque/moment margin >= this factor.
  // Example: 1.2 means 20% margin over required.
  double min_control_margin = 1.1;

  void validate_or_throw() const {
    if (max_added_mass_kg < 0.0 || max_added_mass_kg > 50.0) {
      throw ValidationError("CloseoutGates: max_added_mass_kg outside sane bounds");
    }
    if (min_disk_area_m2 < 0.0 || min_disk_area_m2 > 1000.0) {
      throw ValidationError("CloseoutGates: min_disk_area_m2 outside sane bounds");
    }
    if (min_cruise_power_reduction_frac < 0.0 || min_cruise_power_reduction_frac > 0.95) {
      throw ValidationError("CloseoutGates: min_cruise_power_reduction_frac outside sane bounds");
    }
    if (min_control_margin < 0.5 || min_control_margin > 10.0) {
      throw ValidationError("CloseoutGates: min_control_margin outside sane bounds");
    }
  }
};

// ----------------------------- EvalSettings ----------------------------------
// All knobs that affect physics + feasibility + scoring should live here.
struct EvalSettings {
  Fidelity fidelity = Fidelity::F1_MED;

  AtmosphereSettings atmosphere;
  RotorInducedSettings rotor;
  PowertrainSettings power;
  NumericalSettings numerics;
  OptimizerSettings optimizer;

  // Closeout gates (used by the analysis/closeout layer)
  CloseoutGates gates;

  void validate_or_throw() const {
    atmosphere.validate_or_throw();
    rotor.validate_or_throw();
    power.validate_or_throw();
    numerics.validate_or_throw();
    optimizer.validate_or_throw();
    gates.validate_or_throw();
  }

  static EvalSettings defaults() {
    EvalSettings s;
    return s;
  }
};

}  // namespace lift

