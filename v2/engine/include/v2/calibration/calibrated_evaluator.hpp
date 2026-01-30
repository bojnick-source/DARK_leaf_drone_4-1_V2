#pragma once
/*
================================================================================
v2 Calibration — Calibrated Evaluator
FILE: v2/engine/include/v2/calibration/calibrated_evaluator.hpp

Purpose:
  - Apply calibration corrections at boundary layer
  - Wrap deterministic evaluation with learned corrections
  - Maintain full audit trail
  - Enable deterministic, reversible application

This implements EXECUTION_0.5: Calibration / Assimilation Layer
================================================================================
*/

#include "types.hpp"
#include <v2/core/run_config.hpp>
#include <v2/uncertainty/types.hpp>

namespace v2::calibration {

/**
 * CalibratedEvaluator: Applies calibration corrections at boundary
 * 
 * Wraps base evaluation and applies learned correction factors to
 * physics parameters before evaluation. All corrections applied at
 * adapter/wrapper boundary, never modifying solver internals.
 */
class CalibratedEvaluator {
public:
    /**
     * Construct evaluator with calibration state
     * 
     * @param state Calibration state to apply
     */
    explicit CalibratedEvaluator(const CalibrationState& state);
    
    /**
     * Apply calibration corrections to uncertainty config
     * 
     * Adjusts nominal values of uncertain parameters based on
     * learned correction factors.
     * 
     * @param base_config Base uncertainty configuration
     * @return Calibrated uncertainty configuration
     */
    uncertainty::UncertaintyConfig apply_calibration(
        const uncertainty::UncertaintyConfig& base_config
    ) const;
    
    /**
     * Get current calibration state
     */
    const CalibrationState& get_state() const { return state_; }
    
    /**
     * Check if calibration is active (not uncalibrated)
     */
    bool is_calibrated() const;
    
    /**
     * Get confidence level of applied calibration
     */
    ConfidenceLevel get_confidence() const { return state_.confidence; }
    
private:
    CalibrationState state_;
};

} // namespace v2::calibration
