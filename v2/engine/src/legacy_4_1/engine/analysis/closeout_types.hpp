#pragma once
/*
================================================================================
Legacy 4.1 — Analysis: Closeout Types (Submission-Grade Closeout Data Model)
FILE: engine/analysis/closeout_types.hpp
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
  std::string category;
  double delta_mass_kg = 0.0;
  std::string notes;
};

struct MassDeltaBreakdown {
  double baseline_aircraft_mass_kg = kUnset;
  double baseline_payload_ratio = kUnset;

  std::vector<MassDeltaItem> items;

  double delta_mass_total_kg = kUnset;
  double resulting_aircraft_mass_kg = kUnset;
  double resulting_payload_ratio = kUnset;

  double delta_cg_x_m = kUnset;
  double delta_cg_y_m = kUnset;
  double delta_cg_z_m = kUnset;

  double delta_Ixx_kgm2 = kUnset;
  double delta_Iyy_kgm2 = kUnset;
  double delta_Izz_kgm2 = kUnset;
};

struct DiskAreaCloseout {
  double A_total_m2 = kUnset;
  double disk_loading_N_per_m2 = kUnset;

  double P_hover_induced_W = kUnset;
  double P_hover_profile_W = kUnset;
  double P_hover_total_W = kUnset;

  double P_sized_W = kUnset;

  double FM_used = kUnset;
  double rho_used = kUnset;
};

struct ParasiteCloseout {
  double P_parasite_W = kUnset;
  double delta_P_parasite_W = kUnset;

  double CdS_m2 = kUnset;
  double delta_CdS_m2 = kUnset;

  double V_cruise_mps = kUnset;
};

struct ControlAuthority {
  double yaw_margin_ratio = kUnset;
  double roll_margin_ratio = kUnset;
  double pitch_margin_ratio = kUnset;

  double yaw_moment_reserve_Nm = kUnset;
  double roll_moment_reserve_Nm = kUnset;
  double pitch_moment_reserve_Nm = kUnset;
};

struct ManeuverabilityCloseout {
  ControlAuthority authority;

  double roll_bandwidth_hz = kUnset;
  double pitch_bandwidth_hz = kUnset;
  double yaw_bandwidth_hz = kUnset;

  double min_turn_radius_m = kUnset;
};

struct SyncRiskCloseout {
  double phase_tolerance_deg = kUnset;
  double estimated_latency_ms = kUnset;

  std::string worst_case_disturbance_notes;
  std::string fault_tree_notes;
};

struct StructuralCloseout {
  double mast_bending_margin_ratio = kUnset;
  double gearbox_backlash_deg = kUnset;
  double gearbox_mass_kg = kUnset;
  std::string notes;
};

struct MissionCloseout {
  double baseline_time_s = kUnset;
  double resulting_time_s = kUnset;

  double baseline_energy_Wh = kUnset;
  double resulting_energy_Wh = kUnset;

  std::string scoring_notes;
};

struct RulesCloseout {
  std::string ruleset_name;
  std::string ruleset_version;
  std::vector<std::string> clause_citations;
  std::string notes;
};

struct SfcsIntegrationCloseout {
  std::string corridor_routing_notes;
  std::string emi_isolation_notes;
  std::string serviceability_notes;
};

struct GoNoGoGates {
  double max_delta_mass_kg = kUnset;
  double min_A_total_m2 = kUnset;
  double min_parasite_power_reduction_pct = kUnset;
  double min_yaw_margin_ratio = kUnset;
  double min_phase_tolerance_deg = kUnset;
  double max_latency_ms = kUnset;
  double max_time_increase_pct = kUnset;

  std::string notes;
};

struct GateResult {
  GateDecision decision = GateDecision::NeedsData;
  std::vector<std::string> failed_gates;
  std::vector<std::string> missing_data;
  std::string notes;
};

struct CloseoutReport {
  VariantConcept variant_concept = VariantConcept::Unknown;
  std::string variant_name;
  std::string geom_hash;
  std::string eval_hash;

  MassDeltaBreakdown mass_delta;
  DiskAreaCloseout disk;
  ParasiteCloseout parasite;
  ManeuverabilityCloseout maneuver;
  SyncRiskCloseout sync_risk;
  StructuralCloseout structure;
  MissionCloseout mission;
  RulesCloseout rules;
  SfcsIntegrationCloseout sfcs;

  GoNoGoGates gates;
  GateResult gate_result;
};

} // namespace lift