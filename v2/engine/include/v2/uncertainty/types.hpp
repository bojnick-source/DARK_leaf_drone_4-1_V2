#pragma once
/*
================================================================================
v2 Uncertainty — Types and Data Structures
FILE: v2/engine/include/v2/uncertainty/types.hpp

Purpose:
  - Define uncertainty parameter models
  - Define Monte Carlo result structures
  - Define risk report artifacts
  - Wrapper-only design: solver remains unchanged

This implements EXECUTION_0.2: Uncertainty Wrapper for Decision-Grade Outputs
================================================================================
*/

#include <string>
#include <vector>
#include <map>
#include <cstdint>

namespace v2::uncertainty {

// Distribution types for uncertain parameters
enum class DistributionType {
    Normal,      // Gaussian distribution
    Uniform,     // Uniform distribution over bounds
    LogNormal    // Log-normal distribution
};

/**
 * UncertainScalar: Definition of a single uncertain parameter
 */
struct UncertainScalar {
    std::string name;                    // Parameter identifier
    double nominal_value = 0.0;          // Nominal/mean value
    DistributionType dist_type = DistributionType::Normal;
    double stddev = 0.0;                 // Standard deviation (for Normal)
    double lower_bound = 0.0;            // Lower bound (for Uniform/constraints)
    double upper_bound = 0.0;            // Upper bound (for Uniform/constraints)
};

/**
 * UncertaintyConfig: Complete uncertainty model for evaluation
 */
struct UncertaintyConfig {
    // Uncertain parameters (scalar multipliers/offsets)
    std::vector<UncertainScalar> parameters;
    
    // Monte Carlo settings
    uint32_t sample_count = 200;         // Number of MC samples (default 200)
    
    /**
     * Add a predefined uncertain parameter
     */
    void add_parameter(const UncertainScalar& param);
    
    /**
     * Create default uncertainty config with standard parameters
     */
    static UncertaintyConfig create_default();
};

/**
 * ConstraintRiskRecord: Risk assessment for a single constraint
 */
struct ConstraintRiskRecord {
    std::string constraint_name;         // e.g., "max_disk_loading"
    double nominal_value = 0.0;          // Value at nominal parameters
    double p50_value = 0.0;              // 50th percentile
    double p90_value = 0.0;              // 90th percentile (or P95)
    double p5_value = 0.0;               // 5th percentile
    double violation_probability = 0.0;  // P(constraint violated)
    double threshold = 0.0;              // Constraint limit
};

/**
 * Sensitivity ranking entry
 */
struct SensitivityEntry {
    std::string parameter_name;
    double contribution = 0.0;           // Variance contribution or correlation
    int rank = 0;                        // Importance rank (1 = most important)
};

/**
 * MonteCarloResult: Statistical summary of MC samples for a single output
 */
struct MonteCarloResult {
    std::string output_name;             // e.g., "hover_power_W"
    double nominal_value = 0.0;          // Deterministic result
    double mean_value = 0.0;             // MC mean
    double stddev_value = 0.0;           // MC standard deviation
    double p50_value = 0.0;              // Median
    double p90_value = 0.0;              // 90th percentile
    double p95_value = 0.0;              // 95th percentile
    double p5_value = 0.0;               // 5th percentile
    
    // All sample values (for further analysis)
    std::vector<double> samples;
};

/**
 * RiskReport: Complete uncertainty analysis artifact
 * 
 * This is the authoritative output for decision-grade risk assessment.
 */
struct RiskReport {
    // Traceability
    std::string run_id;
    uint64_t seed = 0;
    uint32_t sample_count = 0;
    std::string timestamp;
    
    // Uncertainty model used
    std::vector<UncertainScalar> distributions_used;
    
    // Statistical results for key outputs
    std::vector<MonteCarloResult> output_results;
    
    // Constraint risk assessments
    std::vector<ConstraintRiskRecord> constraint_risks;
    
    // Sensitivity analysis
    std::vector<SensitivityEntry> sensitivity_ranking;
    
    /**
     * Serialize to JSON for artifact emission
     */
    std::string to_json() const;
    
    /**
     * Write report to file
     */
    void write_to_file(const std::string& filepath) const;
};

} // namespace v2::uncertainty
