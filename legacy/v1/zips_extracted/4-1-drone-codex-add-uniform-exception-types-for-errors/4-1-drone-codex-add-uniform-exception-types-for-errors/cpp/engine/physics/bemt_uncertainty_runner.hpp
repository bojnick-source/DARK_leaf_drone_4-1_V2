#pragma once
// ============================================================================
// BEMT Uncertainty Runner Data Structures
// File: cpp/engine/physics/bemt_uncertainty_runner.hpp
// ============================================================================
//
// Purpose:
// - Define data structures for uncertainty quantification results.
// - Used by stats_report_csv to serialize uncertainty summaries.
//
// ============================================================================

#include <string>
#include <vector>

namespace lift::bemt {

// Summary statistics for a single metric from uncertainty analysis
struct BemtUncSummary {
    std::string metric_key;
    std::string units;
    
    // Basic statistics
    double mean = 0.0;
    double stdev = 0.0;
    double min = 0.0;
    double max = 0.0;
    
    // Quantiles (typically 7: 0.01, 0.05, 0.10, 0.50, 0.90, 0.95, 0.99)
    std::vector<double> q;
    
    // Probability of meeting a threshold
    double prob_meets_threshold = 0.0;
};

// Complete uncertainty analysis report
struct BemtUncertaintyReport {
    std::vector<BemtUncSummary> summaries;
    std::string notes;
    
    void validate() const {
        // Placeholder for future validation
        // Would check that all summaries have consistent quantile counts, etc.
    }
};

} // namespace lift::bemt
