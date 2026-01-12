/*
================================================================================
Fragment 2.2 — Analysis: Closeout Evaluation (GO/NO-GO Gate Engine)
FILE: cpp/engine/analysis/closeout_eval.cpp
================================================================================
*/

#include "engine/analysis/closeout_eval.hpp"

#include <cmath>
#include <limits>
#include <sstream>

namespace lift {

static inline void add_missing(std::vector<std::string>& v, const std::string& s) {
  v.push_back(s);
}

static inline void add_fail(std::vector<std::string>& v, const std::string& s) {
  v.push_back(s);
}

static inline double nan_sum(double a, double b) {
  if (!is_set(a)) return b;
  if (!is_set(b)) return a;
  return a + b;
}

void finalize_mass_delta(MassDeltaBreakdown& md, const CloseoutEvalOptions& opt) {
  // Sum items deterministically.
  double total = 0.0;

  if (md.items.empty()) {
    md.delta_mass_total_kg = kUnset;
  } else {
    for (const auto& it : md.items) {
      total += it.delta_mass_kg;
    }
    md.delta_mass_total_kg = total;
  }

  // Resulting aircraft mass if baseline exists.
  if (is_set(md.baseline_aircraft_mass_kg)) {
    md.resulting_aircraft_mass_kg = md.baseline_aircraft_mass_kg + total;
  } else {
    md.resulting_aircraft_mass_kg = kUnset;
  }

  // Derive resulting payload ratio if possible.
  // We do NOT store payload_mass directly in CloseoutReport yet, so we can:
  //  (A) derive payload mass from baseline payload ratio * baseline mass (proxy)
  //  (B) then compute payload_ratio_new = payload_mass / new_aircraft_mass
  //
  // NOTE: This assumes payload mass is unchanged between baseline and variant.
  // If your variant changes payload mass (e.g., payload interface), you should
  // add payload_mass_kg explicitly and override this logic.
  if (opt.derive_payload_mass_from_baseline_ratio &&
      is_set(md.baseline_payload_ratio) &&
      is_set(md.baseline_aircraft_mass_kg) &&
      is_set(md.resulting_aircraft_mass_kg) &&
      md.resulting_aircraft_mass_kg > 0.0) {

    const double payload_mass_proxy =
        md.baseline_payload_ratio * md.baseline_aircraft_mass_kg;

    md.resulting_payload_ratio = payload_mass_proxy / md.resulting_aircraft_mass_kg;
  } else {
    md.resulting_payload_ratio = kUnset;
  }
}

static GateDecision combine_decisions(GateDecision a, GateDecision b) {
  // Priority: NoGo > NeedsData > Go
  if (a == GateDecision::NoGo || b == GateDecision::NoGo) return GateDecision::NoGo;
  if (a == GateDecision::NeedsData || b == GateDecision::NeedsData) return GateDecision::NeedsData;
  return GateDecision::Go;
}

GateResult evaluate_gates(const CloseoutReport& r, const CloseoutEvalOptions& opt) {
  GateResult out;
  out.decision = GateDecision::Go;

  int evaluated_gate_count = 0;

  auto mark_needs_data = [&](const std::string& field, const std::string& why) {
    add_missing(out.missing_data, field + ": " + why);
    out.decision = combine_decisions(out.decision, GateDecision::NeedsData);
  };

  auto mark_fail = [&](const std::string& gate, const std::string& why) {
    add_fail(out.failed_gates, gate + ": " + why);
    out.decision = combine_decisions(out.decision, GateDecision::NoGo);
  };

  auto mark_pass = [&]() {
    // no-op; kept for symmetry
  };

  // ---------- Gate: max_delta_mass_kg ----------
  if (is_set(r.gates.max_delta_mass_kg)) {
    evaluated_gate_count++;
    if (!is_set(r.mass_delta.delta_mass_total_kg)) {
      mark_needs_data("mass_delta.delta_mass_total_kg", "required for gate max_delta_mass_kg");
    } else {
      if (r.mass_delta.delta_mass_total_kg <= r.gates.max_delta_mass_kg) {
        mark_pass();
      } else {
        std::ostringstream ss;
        ss << "delta_mass_total_kg=" << r.mass_delta.delta_mass_total_kg
           << " > max_delta_mass_kg=" << r.gates.max_delta_mass_kg;
        mark_fail("GATE max_delta_mass_kg", ss.str());
      }
    }
  }

  // ---------- Gate: min_A_total_m2 ----------
  if (is_set(r.gates.min_A_total_m2)) {
    evaluated_gate_count++;
    if (!is_set(r.disk.A_total_m2)) {
      mark_needs_data("disk.A_total_m2", "required for gate min_A_total_m2");
    } else {
      if (r.disk.A_total_m2 >= r.gates.min_A_total_m2) {
        mark_pass();
      } else {
        std::ostringstream ss;
        ss << "A_total_m2=" << r.disk.A_total_m2
           << " < min_A_total_m2=" << r.gates.min_A_total_m2;
        mark_fail("GATE min_A_total_m2", ss.str());
      }
    }
  }

  // ---------- Gate: min_parasite_power_reduction_pct ----------
  // Uses (delta_P_parasite_W / baseline_P_parasite_W) * 100, where delta is negative for reduction.
  if (is_set(r.gates.min_parasite_power_reduction_pct)) {
    evaluated_gate_count++;
    if (!is_set(r.parasite.P_parasite_W)) {
      mark_needs_data("parasite.P_parasite_W", "required baseline parasite power for reduction %");
    } else if (!is_set(r.parasite.delta_P_parasite_W)) {
      mark_needs_data("parasite.delta_P_parasite_W", "required delta parasite power for reduction %");
    } else if (r.parasite.P_parasite_W <= 0.0) {
      mark_needs_data("parasite.P_parasite_W", "must be > 0 to compute reduction %");
    } else {
      const double reduction_pct = (-r.parasite.delta_P_parasite_W / r.parasite.P_parasite_W) * 100.0;
      if (reduction_pct >= r.gates.min_parasite_power_reduction_pct) {
        mark_pass();
      } else {
        std::ostringstream ss;
        ss << "parasite_reduction_pct=" << reduction_pct
           << " < min_required=" << r.gates.min_parasite_power_reduction_pct
           << " (delta_P_parasite_W should be negative for reduction)";
        mark_fail("GATE min_parasite_power_reduction_pct", ss.str());
      }
    }
  }

  // ---------- Gate: min_yaw_margin_ratio ----------
  if (is_set(r.gates.min_yaw_margin_ratio)) {
    evaluated_gate_count++;
    if (!is_set(r.maneuver.authority.yaw_margin_ratio)) {
      mark_needs_data("maneuver.authority.yaw_margin_ratio", "required for yaw margin gate");
    } else {
      if (r.maneuver.authority.yaw_margin_ratio >= r.gates.min_yaw_margin_ratio) {
        mark_pass();
      } else {
        std::ostringstream ss;
        ss << "yaw_margin_ratio=" << r.maneuver.authority.yaw_margin_ratio
           << " < min_required=" << r.gates.min_yaw_margin_ratio;
        mark_fail("GATE min_yaw_margin_ratio", ss.str());
      }
    }
  }

  // ---------- Gate: min_phase_tolerance_deg ----------
  if (is_set(r.gates.min_phase_tolerance_deg)) {
    evaluated_gate_count++;
    if (!is_set(r.sync_risk.phase_tolerance_deg)) {
      mark_needs_data("sync_risk.phase_tolerance_deg", "required for intermeshing phase tolerance gate");
    } else {
      if (r.sync_risk.phase_tolerance_deg >= r.gates.min_phase_tolerance_deg) {
        mark_pass();
      } else {
        std::ostringstream ss;
        ss << "phase_tolerance_deg=" << r.sync_risk.phase_tolerance_deg
           << " < min_required=" << r.gates.min_phase_tolerance_deg;
        mark_fail("GATE min_phase_tolerance_deg", ss.str());
      }
    }
  }

  // ---------- Gate: max_latency_ms ----------
  if (is_set(r.gates.max_latency_ms)) {
    evaluated_gate_count++;
    if (!is_set(r.sync_risk.estimated_latency_ms)) {
      mark_needs_data("sync_risk.estimated_latency_ms", "required for latency gate");
    } else {
      if (r.sync_risk.estimated_latency_ms <= r.gates.max_latency_ms) {
        mark_pass();
      } else {
        std::ostringstream ss;
        ss << "estimated_latency_ms=" << r.sync_risk.estimated_latency_ms
           << " > max_allowed=" << r.gates.max_latency_ms;
        mark_fail("GATE max_latency_ms", ss.str());
      }
    }
  }

  // ---------- Gate: max_time_increase_pct ----------
  // Uses (resulting - baseline)/baseline * 100
  if (is_set(r.gates.max_time_increase_pct)) {
    evaluated_gate_count++;
    if (!is_set(r.mission.baseline_time_s)) {
      mark_needs_data("mission.baseline_time_s", "required baseline time for time increase %");
    } else if (!is_set(r.mission.resulting_time_s)) {
      mark_needs_data("mission.resulting_time_s", "required resulting time for time increase %");
    } else if (r.mission.baseline_time_s <= 0.0) {
      mark_needs_data("mission.baseline_time_s", "must be > 0 to compute time increase %");
    } else {
      const double inc_pct =
          ((r.mission.resulting_time_s - r.mission.baseline_time_s) / r.mission.baseline_time_s) * 100.0;
      if (inc_pct <= r.gates.max_time_increase_pct) {
        mark_pass();
      } else {
        std::ostringstream ss;
        ss << "time_increase_pct=" << inc_pct
           << " > max_allowed=" << r.gates.max_time_increase_pct;
        mark_fail("GATE max_time_increase_pct", ss.str());
      }
    }
  }

  // If strict missing-data, any missing_data makes decision at least NeedsData.
  if (opt.strict_missing_data && !out.missing_data.empty()) {
    out.decision = combine_decisions(out.decision, GateDecision::NeedsData);
  }

  // If require_any_gate, and none were evaluated, force NeedsData (prevents false "Go").
  if (opt.require_any_gate && evaluated_gate_count == 0) {
    out.decision = GateDecision::NeedsData;
    add_missing(out.missing_data, "gates: no thresholds set; no gates evaluated");
  }

  // Notes summary
  {
    std::ostringstream ss;
    ss << "evaluated_gates=" << evaluated_gate_count
       << ", failed=" << out.failed_gates.size()
       << ", missing=" << out.missing_data.size();
    out.notes = ss.str();
  }

  return out;
}

void finalize_and_evaluate(CloseoutReport& r, const CloseoutEvalOptions& opt) {
  // Finalize deterministic derived fields first (mass totals/ratio).
  finalize_mass_delta(r.mass_delta, opt);

  // Evaluate gates and store.
  r.gate_result = evaluate_gates(r, opt);
}

} // namespace lift
