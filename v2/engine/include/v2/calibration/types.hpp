#pragma once
/*
================================================================================
v2 Calibration — Types and Data Structures
FILE: v2/engine/include/v2/calibration/types.hpp

Purpose:
  - Define calibration state with versioning and provenance
  - Define bounded correction factors learned from measured data
  - Enable deterministic, auditable, reversible calibration
  - Apply corrections at boundary layer without modifying solver

This implements EXECUTION_0.5: Calibration / Assimilation Layer
================================================================================
*/

#include <string>
#include <vector>
#include <map>
#include <cstdint>

namespace v2::calibration {

/**
 * Confidence level for calibration state
 */
enum class ConfidenceLevel {
    HIGH,         // Sufficient data, low uncertainty, valid for use
    MEDIUM,       // Moderate uncertainty, use with caution
    LOW,          // Insufficient data or high uncertainty, do not use
    UNCALIBRATED  // No calibration applied (default state)
};

/**
 * CorrectionFactor: Single bounded scalar correction
 * 
 * Represents a learned multiplier or offset that adjusts physics parameters
 * at the adapter/wrapper boundary.
 */
struct CorrectionFactor {
    std::string parameter_name;       // e.g., "motor_efficiency_multiplier"
    double value = 1.0;                // Fitted correction value
    double lower_bound = 0.5;          // Hard lower limit (conservative)
    double upper_bound = 1.5;          // Hard upper limit (conservative)
    double uncertainty = 0.0;          // Estimated uncertainty in fitted value
    int observation_count = 0;         // Number of data points used
    
    /**
     * Check if value is within bounds
     */
    bool is_valid() const;
    
    /**
     * Clamp value to bounds (conservative safety)
     */
    void clamp_to_bounds();
};

/**
 * CalibrationProvenance: Complete audit trail for calibration
 */
struct CalibrationProvenance {
    std::string creation_timestamp;    // When calibration was created
    std::string git_commit_hash;       // Exact code version
    std::string data_source;           // Source of measurement data
    std::string fit_method;            // Algorithm used (e.g., "least_squares")
    int total_observations = 0;        // Total data points
    double residual_rms = 0.0;         // Root-mean-square residual
    std::map<std::string, std::string> metadata; // Additional context
};

/**
 * CalibrationState: Versioned, auditable calibration artifact
 * 
 * This is the authoritative record of learned correction factors.
 * Must be deterministic, reversible, and conservative.
 */
struct CalibrationState {
    // Version and identity
    std::string calibration_id;        // Unique identifier
    uint32_t version = 1;              // State version (increment on update)
    ConfidenceLevel confidence = ConfidenceLevel::UNCALIBRATED;
    
    // Correction factors (5 parameters as specified)
    std::vector<CorrectionFactor> correction_factors;
    
    // Provenance and traceability
    CalibrationProvenance provenance;
    
    /**
     * Create uncalibrated state (identity corrections)
     */
    static CalibrationState create_uncalibrated();
    
    /**
     * Create state with default bounds for specified parameters
     */
    static CalibrationState create_default_bounded();
    
    /**
     * Validate state (check bounds, consistency)
     */
    bool is_valid() const;
    
    /**
     * Get correction factor by name
     */
    const CorrectionFactor* get_factor(const std::string& name) const;
    
    /**
     * Get correction factor by name (mutable)
     */
    CorrectionFactor* get_factor_mut(const std::string& name);
    
    /**
     * Serialize to JSON for artifact emission
     */
    std::string to_json() const;
    
    /**
     * Load from JSON string
     */
    static CalibrationState from_json(const std::string& json_str);
    
    /**
     * Write state to file
     */
    void write_to_file(const std::string& filepath) const;
    
    /**
     * Load state from file
     */
    static CalibrationState load_from_file(const std::string& filepath);
};

/**
 * MeasurementPoint: Single observed data point for calibration
 */
struct MeasurementPoint {
    // Input parameters (design specification)
    std::map<std::string, double> design_params;
    
    // Measured outputs (ground truth)
    std::map<std::string, double> measured_outputs;
    
    // Optional: measurement uncertainty
    std::map<std::string, double> measurement_uncertainties;
};

/**
 * CalibrationDataset: Collection of measurements for fitting
 */
struct CalibrationDataset {
    std::vector<MeasurementPoint> measurements;
    std::string dataset_id;
    std::string source_description;
    
    /**
     * Validate dataset (check completeness)
     */
    bool is_valid() const;
    
    /**
     * Get number of measurements
     */
    size_t size() const { return measurements.size(); }
};

/**
 * FitResult: Result of calibration fitting procedure
 */
struct FitResult {
    CalibrationState calibrated_state;
    double residual_rms = 0.0;         // RMS error
    double max_residual = 0.0;         // Maximum error
    int iterations = 0;                // Fit iterations
    bool converged = false;            // Did fit converge?
    std::string fit_summary;           // Human-readable summary
    
    /**
     * Check if fit is acceptable
     */
    bool is_acceptable() const;
};

} // namespace v2::calibration
