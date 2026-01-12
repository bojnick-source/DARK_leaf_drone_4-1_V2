/*
================================================================================
Fragment 2.5 — CLI: Closeout Demo Harness (End-to-End Smoke Test)
FILE: cpp/cli/closeout_demo.cpp

Purpose:
  - Build a CloseoutReport with representative fields filled.
  - Run gate evaluation (finalize_and_evaluate).
  - Export deterministic JSON via closeout_to_json + write_closeout_json_file.

This is NOT the optimizer. This is a hardened pipeline sanity-check:
  Types -> Eval -> JSON -> File

Usage:
  closeout_demo [output_path]
Examples:
  closeout_demo
  closeout_demo closeout.json

Hardening:
  - No silent success: prints decision + failures/missing_data counts.
  - Uses explicit NaN-unset semantics (kUnset) for missing values.
================================================================================
*/

#include "engine/analysis/closeout_types.hpp"
#include "engine/analysis/closeout_eval.hpp"
#include "engine/analysis/closeout_json.hpp"

#include <cstdlib>
#include <iostream>
#include <string>

static std::string default_out_path() {
  return "closeout.json";
}

static int print_result_and_return(const lift::GateResult& gr) {
  std::cout << "GateDecision: ";
  switch (gr.decision) {
    case lift::GateDecision::Go:        std::cout << "Go"; break;
    case lift::GateDecision::NoGo:      std::cout << "NoGo"; break;
    case lift::GateDecision::NeedsData: std::cout << "NeedsData"; break;
    default:                            std::cout << "NeedsData"; break;
  }
  std::cout << "\n";
  std::cout << "Failed gates: " << gr.failed_gates.size() << "\n";
  std::cout << "Missing data: " << gr.missing_data.size() << "\n";
  if (!gr.notes.empty()) std::cout << "Notes: " << gr.notes << "\n";

  // Non-zero on NoGo to make CI-friendly.
  if (gr.decision == lift::GateDecision::NoGo) return 2;
  if (gr.decision == lift::GateDecision::NeedsData) return 3;
  return 0;
}

int main(int argc, char** argv) {
  const std::string out_path = (argc >= 2) ? std::string(argv[1]) : default_out_path();

  lift::CloseoutReport r;

  // -------------------------
  // Identity
  // -------------------------
  r.concept = lift::VariantConcept::Quad_With_SFCS;
  r.variant_name = "D6_baseline_like_demo";
  r.geom_hash = "demo_geom_hash_placeholder";
  r.eval_hash = "demo_eval_hash_placeholder";

  // -------------------------
  // Gates (explicit thresholds)
  // -------------------------
  // NOTE: Use NaN (kUnset) for any gate you do not want evaluated.
  r.gates.max_delta_mass_kg = 1.50;                 // must not add more than +1.5 kg
  r.gates.min_A_total_m2 = 1.60;                    // must have at least 1.6 m^2 disk area
  r.gates.min_parasite_power_reduction_pct = 5.0;   // must reduce parasite power >= 5%
  r.gates.min_yaw_margin_ratio = 1.10;              // must have >=10% yaw margin
  r.gates.max_time_increase_pct = 2.0;              // mission time cannot worsen by >2%
  // Intermeshing gates left unset for this concept:
  r.gates.min_phase_tolerance_deg = lift::kUnset;
  r.gates.max_latency_ms = lift::kUnset;

  r.gates.notes =
      "Demo gates. Replace with rule-driven thresholds and design targets.";

  // -------------------------
  // 1) Mass delta breakdown (Δmass)
  // -------------------------
  r.mass_delta.baseline_aircraft_mass_kg = 24.95;   // example baseline
  r.mass_delta.baseline_payload_ratio = 4.20;       // example baseline ratio

  r.mass_delta.items.push_back({"motors",  +0.40, "demo motor swap mass delta"});
  r.mass_delta.items.push_back({"escs",    +0.10, "demo esc delta"});
  r.mass_delta.items.push_back({"wiring",  +0.08, "extra harnessing"});
  r.mass_delta.items.push_back({"structure",-0.20,"removed bracketry via SFCS routing"});
  r.mass_delta.items.push_back({"cooling", +0.15, "added ducting/heat spreader"});

  // Optional CG/inertia deltas (leave unset if not computed yet).
  r.mass_delta.delta_cg_x_m = lift::kUnset;
  r.mass_delta.delta_cg_y_m = lift::kUnset;
  r.mass_delta.delta_cg_z_m = lift::kUnset;
  r.mass_delta.delta_Ixx_kgm2 = lift::kUnset;
  r.mass_delta.delta_Iyy_kgm2 = lift::kUnset;
  r.mass_delta.delta_Izz_kgm2 = lift::kUnset;

  // -------------------------
  // 2) Disk area / induced power outputs (placeholders filled for gating)
  // -------------------------
  r.disk.A_total_m2 = 1.75;                       // example effective disk area
  r.disk.disk_loading_N_per_m2 = 0.0;             // can be computed later
  r.disk.P_hover_induced_W = lift::kUnset;
  r.disk.P_hover_profile_W = lift::kUnset;
  r.disk.P_hover_total_W = lift::kUnset;
  r.disk.P_sized_W = lift::kUnset;
  r.disk.FM_used = 0.75;
  r.disk.rho_used = 1.225;

  // -------------------------
  // 3) Parasite drag / cruise deltas
  // -------------------------
  // Convention used in closeout_eval:
  //   delta_P_parasite_W negative => reduction
  r.parasite.V_cruise_mps = 22.0;                 // example cruise speed
  r.parasite.P_parasite_W = 3200.0;               // baseline parasite power at V (W)
  r.parasite.delta_P_parasite_W = -250.0;         // improvement (reduction)
  r.parasite.CdS_m2 = lift::kUnset;
  r.parasite.delta_CdS_m2 = lift::kUnset;

  // -------------------------
  // 4) Maneuverability metrics
  // -------------------------
  r.maneuver.authority.yaw_margin_ratio = 1.20;   // passes 1.10 gate
  r.maneuver.authority.roll_margin_ratio = lift::kUnset;
  r.maneuver.authority.pitch_margin_ratio = lift::kUnset;
  r.maneuver.authority.yaw_moment_reserve_Nm = lift::kUnset;
  r.maneuver.authority.roll_moment_reserve_Nm = lift::kUnset;
  r.maneuver.authority.pitch_moment_reserve_Nm = lift::kUnset;
  r.maneuver.roll_bandwidth_hz = lift::kUnset;
  r.maneuver.pitch_bandwidth_hz = lift::kUnset;
  r.maneuver.yaw_bandwidth_hz = lift::kUnset;
  r.maneuver.min_turn_radius_m = lift::kUnset;

  // -------------------------
  // 5) Sync risk (only used for intermeshing gates; left unset)
  // -------------------------
  r.sync_risk.phase_tolerance_deg = lift::kUnset;
  r.sync_risk.estimated_latency_ms = lift::kUnset;
  r.sync_risk.worst_case_disturbance_notes = "";
  r.sync_risk.fault_tree_notes = "";

  // -------------------------
  // 6) Structural closeout (placeholders)
  // -------------------------
  r.structure.mast_bending_margin_ratio = lift::kUnset;
  r.structure.gearbox_backlash_deg = lift::kUnset;
  r.structure.gearbox_mass_kg = lift::kUnset;
  r.structure.notes = "";

  // -------------------------
  // 7) Mission scoring impacts
  // -------------------------
  r.mission.baseline_time_s = 720.0;              // 12 minutes baseline
  r.mission.resulting_time_s = 730.0;             // slightly worse (1.39% increase) passes 2% gate
  r.mission.baseline_energy_Wh = lift::kUnset;
  r.mission.resulting_energy_Wh = lift::kUnset;
  r.mission.scoring_notes = "Demo times only.";

  // -------------------------
  // 8) Rules verification (citations placeholders)
  // -------------------------
  r.rules.ruleset_name = "DARPA_LIFT";
  r.rules.ruleset_version = "UNSET";
  r.rules.clause_citations.clear();
  r.rules.notes = "Populate with clause IDs once rules PDF is parsed.";

  // -------------------------
  // 9) SFCS integration notes
  // -------------------------
  r.sfcs.corridor_routing_notes = "Demo: corridor routing TBD.";
  r.sfcs.emi_isolation_notes = "Demo: EMI/grounding TBD.";
  r.sfcs.serviceability_notes = "Demo: serviceability TBD.";

  // -------------------------
  // Evaluate + Export
  // -------------------------
  lift::CloseoutEvalOptions opt;
  opt.strict_missing_data = true;
  opt.require_any_gate = true;
  opt.derive_payload_mass_from_baseline_ratio = true;

  lift::finalize_and_evaluate(r, opt);

  if (!lift::write_closeout_json_file(r, out_path, 2)) {
    std::cerr << "ERROR: failed to write JSON to: " << out_path << "\n";
    return 10;
  }

  std::cout << "Wrote: " << out_path << "\n";
  return print_result_and_return(r.gate_result);
}
