// ============================================================================
// Fragment 1.4.26 — Stats Report CSV API (Generic Metrics → CSV) (C++)
// File: cpp/engine/physics/stats_report_csv.hpp
// ============================================================================
//
// Purpose:
// - Serialize statistical summaries (CDF/quantiles/probabilities) to CSV.
// - Intended for uncertainty runs (BEMT MC), closeout aggregation, and dashboards.
// - No filesystem policy: caller provides std::ostream.
//
// CSV formats:
// 1) Summary CSV: metric_key,units,mean,stdev,min,max,prob_meets_threshold
// 2) Quantiles CSV: metric_key,q,value
//
// ============================================================================

#pragma once
#include "engine/physics/bemt_uncertainty_runner.hpp"
#include "engine/physics/bemt_require.hpp"

#include <iosfwd>

namespace lift::bemt {

void write_uncertainty_summary_csv(std::ostream& os, const BemtUncertaintyReport& rep);
void write_uncertainty_quantiles_csv(std::ostream& os, const BemtUncertaintyReport& rep);

} // namespace lift::bemt
