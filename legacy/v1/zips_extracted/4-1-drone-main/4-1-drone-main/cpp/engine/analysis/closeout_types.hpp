#pragma once
/*
================================================================================
Fragment 2.0 — Analysis: Closeout Types (Submission-Grade Closeout Data Model)
FILE: cpp/engine/analysis/closeout_types.hpp

Purpose:
  Provide a strict, explicit data model for the "exhaustive closeout" items:
    1) Quantified mass deltas
    2) Disk-area / induced-power math outputs (as fields to be filled)
    3) Parasite drag / cruise power deltas
    4) Maneuverability metrics
    5) Intermeshing phase/latency risk outputs
    6) Structural/gearbox feasibility outputs (as fields to be filled)
    7) Mission scoring impacts
    8) Rules verification (as citations/fields to be filled)
    9) SFCS integration notes
   10) Explicit GO/NO-GO thresholds and gate results

Hardening rules:
  - Any double field set to NaN means "UNSET / missing".
  - Gates are only evaluated when thresholds are finite (not NaN).
  - Missing-data is tracked separately from failures.
  - No hidden defaults that could accidentally "pass" a design.

Note:
  This header defines *types only*. Computation happens in closeout_eval.*.
================================================================================
*/

#include <cmath>
#include <cstdint>
#include <limits>
#include <string>
#include <vector>

namespace lift {

// Sentinel for "unset" numeric values (NaN by default).
inline constexpr double kUnset = std::numeric_limits<double>::quiet_NaN();

enum class VariantConcept : int {
  Unknown = 0,
  Quad_OpenRotor,
  Hex_OpenRotor,
  Octo_OpenRotor,
  Coaxial_Stacked,
  Tandem_Twin,
  Shrouded_Variants,
  Intermeshing_Synchropter,
  Quad_With_SFCS,
  Other
};

enum class GateDecision : int {
  Go = 0,
  NoGo = 1,
  NeedsData = 2
};

struct MassDeltaItem {
  // Example categories: "motors", "escs", "props", "mounts", "wiring", "structure",
  // "fairings", "bearings", "shafts", "gearbox", "gimbals", "cooling", etc.
  std::string category;
  double delta_mass_kg = 0.0;
  std::string notes; // optional human-readable trace (source, assumption, part #, etc.)
};

struct MassDeltaBreakdown {
  // Baseline aircraft mass for the reference concept this variant is being compared to.
  double baseline_aircraft_mass_kg = kUnset;

  // Baseline payload ratio (payload / aircraft mass), if available.
  double baseline_payload_ratio = kUnset;

  // Itemized deltas (sum produces delta_mass_total_kg).
  std::vector<MassDeltaItem> items;

  // Computed totals:
  double delta_mass_total_kg = kUnset;
  double resulting_aircraft_mass_kg = kUnset;
  double resulting_payload_ratio = kUnset; // derived if possible (see eval logic)

  // Optional: CG and inertia deltas (can be filled by geometry/structural modules)
  double delta_cg_x_m = kUnset; // body axes
  double delta_cg_y_m = kUnset;
  double delta_cg_z_m = kUnset;

  double delta_Ixx_kgm2 = kUnset;
  double delta_Iyy_kgm2 = kUnset;
  double delta_Izz_kgm2 = kUnset;
};

struct DiskAreaCloseout {
  // Total actuator disk area used for induced-power scaling.
  double A_total_m2 = kUnset;

  // Disk loading at hover (T/A). You can store N/m^2 or kg/m^2; document units.
  double disk_loading_N_per_m2 = kUnset;

  // Hover induced and total powers (placeholders for your chosen model outputs).
  double P_hover_induced_W = kUnset;
  double P_hover_profile_W = kUnset;
  double P_hover_total_W = kUnset;

  // Sizing / reserve power using your k factors (k_hover, k_reserve etc).
  double P_sized_W = kUnset;

  // Sensitivity placeholders (fill if running sweeps)
  double FM_used = kUnset;
  double rho_used = kUnset;
};

struct ParasiteCloseout {
  // Baseline parasite power and delta at a chosen cruise speed (W).
  double P_parasite_W = kUnset;
  double delta_P_parasite_W = kUnset;

  // Baseline and delta CdS (m^2), if you compute it.
  double CdS_m2 = kUnset;
  double delta_CdS_m2 = kUnset;

  // Cruise speed where these were evaluated.
  double V_cruise_mps = kUnset;
};

struct ControlAuthority {
  // Ratios > 1 mean margin exists; define precisely in your control module.
  double yaw_margin_ratio = kUnset;
  double roll_margin_ratio = kUnset;
  double pitch_margin_ratio = kUnset;

  // Optional: torque / moment reserves, etc.
  double yaw_moment_reserve_Nm = kUnset;
  double roll_moment_reserve_Nm = kUnset;
  double pitch_moment_reserve_Nm = kUnset;
};

struct ManeuverabilityCloseout {
  ControlAuthority authority;

  // Response bandwidth estimates (Hz), if computed.
  double roll_bandwidth_hz = kUnset;
  double pitch_bandwidth_hz = kUnset;
  double yaw_bandwidth_hz = kUnset;

  // Turn-radius / course-transition metrics if computed.
  double min_turn_radius_m = kUnset;
};

struct SyncRiskCloseout {
  // For intermeshing: tolerance before blade strike (deg) and system latency (ms).
  double phase_tolerance_deg = kUnset;
  double estimated_latency_ms = kUnset;

  // Optional: dominant disturbance sources
  std::string worst_case_disturbance_notes;
  std::string fault_tree_notes;
};

struct StructuralCloseout {
  // Structural stiffness/gearbox feasibility placeholders.
  double mast_bending_margin_ratio = kUnset;
  double gearbox_backlash_deg = kUnset;
  double gearbox_mass_kg = kUnset;
  std::string notes;
};

struct MissionCloseout {
  // Baseline and resulting mission time (s) for scoring impact.
  double baseline_time_s = kUnset;
  double resulting_time_s = kUnset;

  // Optional: energy usage deltas, etc.
  double baseline_energy_Wh = kUnset;
  double resulting_energy_Wh = kUnset;

  std::string scoring_notes;
};

struct RulesCloseout {
  // Track what rule set/version was used and any clause citations.
  std::string ruleset_name;
  std::string ruleset_version;
  std::vector<std::string> clause_citations; // e.g., "Rule 3.2.1 payload attachment..."
  std::string notes;
};

struct SfcsIntegrationCloseout {
  // Notes about corridor routing, EMI, serviceability, failure isolation.
  std::string corridor_routing_notes;
  std::string emi_isolation_notes;
  std::string serviceability_notes;
};

struct GoNoGoGates {
  // 10) Explicit gates. Any NaN means gate "unset" (not evaluated).

  // Mass delta gate
  double max_delta_mass_kg = kUnset;

  // Disk area gate
  double min_A_total_m2 = kUnset;

  // Parasite reduction gate (percentage)
  double min_parasite_power_reduction_pct = kUnset;

  // Maneuverability gate
  double min_yaw_margin_ratio = kUnset;

  // Intermeshing risk gates
  double min_phase_tolerance_deg = kUnset;
  double max_latency_ms = kUnset;

  // Mission time penalty gate (percentage)
  double max_time_increase_pct = kUnset;

  // Free-form description of how these gates were chosen.
  std::string notes;
};

struct GateResult {
  GateDecision decision = GateDecision::NeedsData;
  std::vector<std::string> failed_gates;  // each entry: "GATE_NAME: reason"
  std::vector<std::string> missing_data;  // each entry: "FIELD: reason"
  std::string notes;                      // summary
};

struct CloseoutReport {
  // Identification
  VariantConcept concept = VariantConcept::Unknown;
  std::string variant_name;   // e.g. "D6 baseline", "D6 + pusher", etc.
  std::string geom_hash;      // optional: geometry hash for traceability
  std::string eval_hash;      // optional: evaluation hash for traceability

  // Closeout sections (fields may remain NaN until computed by physics modules).
  MassDeltaBreakdown mass_delta;
  DiskAreaCloseout disk;
  ParasiteCloseout parasite;
  ManeuverabilityCloseout maneuver;
  SyncRiskCloseout sync_risk;
  StructuralCloseout structure;
  MissionCloseout mission;
  RulesCloseout rules;
  SfcsIntegrationCloseout sfcs;

  // Gates + results
  GoNoGoGates gates;
  GateResult gate_result;
};

} // namespace lift
