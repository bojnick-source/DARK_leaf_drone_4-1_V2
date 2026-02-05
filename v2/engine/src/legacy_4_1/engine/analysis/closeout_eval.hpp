#pragma once
/*
================================================================================
Legacy 4.1 — Analysis: Closeout Evaluator (Gates + Missing-Data Audit)
FILE: engine/analysis/closeout_eval.hpp
================================================================================
*/

#include "engine/analysis/closeout_types.hpp"

#include <string>
#include <vector>

namespace lift {

struct CloseoutEvalOptions {
  bool strict_missing_data = true;
  bool require_any_gate = true;
  bool derive_payload_mass_from_baseline_ratio = true;
};

// Helper: NaN => unset
bool is_set(double x);

// 1) Mass delta: sum items, compute resulting mass, compute resulting payload ratio.
void finalize_mass_delta(MassDeltaBreakdown& md, const CloseoutEvalOptions& opt);

// 10) Gate evaluation over the report.
GateResult evaluate_gates(const CloseoutReport& r, const CloseoutEvalOptions& opt);

// Convenience: finalize mass + evaluate gates, write into report.gate_result
void finalize_and_evaluate(CloseoutReport& r, const CloseoutEvalOptions& opt);

} // namespace lift