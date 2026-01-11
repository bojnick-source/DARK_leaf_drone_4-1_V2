#pragma once
/*
================================================================================
v2 Validity — Out-of-Distribution Detection and Validity Gating
FILE: v2/engine/include/v2/validity/types.hpp

Purpose:
  - Define validity states for uncertainty outputs
  - Define OOD detection metrics
  - Provide validity assessment artifacts
  - Evidence-only layer: does not modify behavior

This implements EXECUTION_0.6: OOD Detection + Conservative Validity Gating
================================================================================
*/

#include <string>
#include <vector>
#include <map>
#include <cstdint>

namespace v2::validity {

/**
 * ValidityState: Classification of trustworthiness
 * 
 * Orthogonal to ACCEPT/REJECT/DEFER — describes only reliability of outputs
 */
enum class ValidityState {
    VALID,                 // Outputs are trustworthy, in-distribution
    LOW_CONFIDENCE,        // Outputs have high uncertainty, use cautiously
    OUT_OF_DISTRIBUTION    // Outputs are unreliable, extrapolation region
};

/**
 * OODMetric: Single out-of-distribution check result
 */
struct OODMetric {
    std::string metric_name;           // e.g., "percentile_spread_ratio"
    double computed_value = 0.0;       // Measured value
    double threshold = 0.0;            // Threshold for concern
    bool flagged = false;              // True if threshold exceeded
    std::string interpretation;        // Human-readable explanation
};

/**
 * OODThresholds: Configurable thresholds for OOD detection
 * 
 * Conservative defaults designed to flag suspicious distributions
 */
struct OODThresholds {
    // Percentile spread ratio: (P95 - P5) / max(|P50|, eps)
    double max_spread_ratio = 2.0;     // Flag if spread > 2x nominal
    
    // Sample variance ratio: max(CV_i) for all outputs
    double max_coeff_variation = 0.5;  // Flag if CV > 50%
    
    // Calibration drift: |calibrated_mean - nominal| / nominal
    double max_calibration_drift = 0.3; // Flag if drift > 30%
    
    // Minimum sample count for validity
    uint32_t min_sample_count = 50;    // Need at least 50 samples
    
    /**
     * Create default conservative thresholds
     */
    static OODThresholds create_default();
    
    /**
     * Create relaxed thresholds for early exploration
     */
    static OODThresholds create_relaxed();
};

/**
 * ValidityAssessment: Complete validity evaluation artifact
 * 
 * This is the authoritative record of whether uncertainty outputs are trustworthy.
 */
struct ValidityAssessment {
    // Traceability
    std::string run_id;
    uint64_t seed = 0;
    std::string timestamp;
    
    // Validity classification
    ValidityState state = ValidityState::OUT_OF_DISTRIBUTION;
    std::string state_rationale;       // Why this classification?
    double confidence_score = 0.0;     // Overall confidence [0, 1]
    
    // OOD metrics evaluated
    std::vector<OODMetric> ood_metrics;
    
    // Summary statistics
    int num_metrics_evaluated = 0;
    int num_metrics_flagged = 0;
    
    // Thresholds used
    OODThresholds thresholds;
    
    // Recommendations
    std::vector<std::string> recommendations;  // What to do if OOD
    
    /**
     * Serialize to JSON for artifact emission
     */
    std::string to_json() const;
    
    /**
     * Write assessment to file
     */
    void write_to_file(const std::string& filepath) const;
};

/**
 * ValidityStatistics: Aggregate validity stats across multiple evaluations
 */
struct ValidityStatistics {
    int total_evaluations = 0;
    int num_valid = 0;
    int num_low_confidence = 0;
    int num_ood = 0;
    
    double valid_rate = 0.0;
    double low_confidence_rate = 0.0;
    double ood_rate = 0.0;
    
    // Most common OOD flags
    std::map<std::string, int> ood_flag_counts;
};

} // namespace v2::validity
