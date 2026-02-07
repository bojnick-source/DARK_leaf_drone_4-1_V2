#pragma once
/*
================================================================================
Fragment 2.1 — Analysis: Closeout Evaluator (Gates + Missing-Data Audit)
FILE: cpp/engine/analysis/closeout_eval.hpp

Purpose:
  Turn a CloseoutReport into a submission-grade "GO / NO-GO / NEEDS DATA"
  decision with:
    - Explicit gate evaluation (only when thresholds are set)
    - Explicit missing-data list (so nothing silently passes)
    - Deterministic mass-delta totals and derived ratios (when possible)

Key rules:
  - Any numeric "unset" field is NaN. We treat it as missing.
  - A gate with an unset threshold is NOT evaluated.
  - A gate with a set threshold but missing required measured values -> NeedsData.
  - GateDecision precedence:
      NoGo beats Go.
      NeedsData beats Go.
      Go only if all evaluated gates pass AND no evaluated gate is missing data.

Outputs:
  - lift::GateResult with:
      decision, failed_gates[], missing_data[], notes

================================================================================
*/

#include "engine/analysis/closeout_types.hpp"

#include <string>
#include <vector>

namespace lift {

struct CloseoutEvalOptions {
  // If true, missing-data in ANY evaluated gate forces NeedsData (recommended).
  bool strict_missing_data = true;

  // If true, require at least one gate to be evaluated; otherwise NeedsData.
  bool require_any_gate = true;

  // If true, compute resulting_payload_ratio using baseline ratio * baseline mass
  // as proxy for payload mass when payload mass itself isn't stored.
  bool derive_payload_mass_from_baseline_ratio = true;
};

// Helper: NaN => unset
bool is_set(double x);

// 1) Mass delta: sum items, compute resulting mass, compute resulting payload ratio.
void finalize_mass_delta(MassDeltaBreakdown& md, const CloseoutEvalOptions& opt);

// 10) Gate evaluation over the report.
// This does not run physics; it only evaluates gates against report fields.
GateResult evaluate_gates(const CloseoutReport& r, const CloseoutEvalOptions& opt);

// Convenience: finalize mass + evaluate gates, write into report.gate_result
void finalize_and_evaluate(CloseoutReport& r, const CloseoutEvalOptions& opt);

} // namespace lift
