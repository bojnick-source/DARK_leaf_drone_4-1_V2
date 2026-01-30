#pragma once
/*
================================================================================
v2 Calibration — Calibration Fitter
FILE: v2/engine/include/v2/calibration/calibration_fitter.hpp

Purpose:
  - Fit bounded correction factors from measurement data
  - Use robust, conservative estimation
  - Produce deterministic, auditable FitResult
  - Never destabilize solver with unbounded corrections

This implements EXECUTION_0.5: Calibration / Assimilation Layer
================================================================================
*/

#include "types.hpp"
#include <v2/core/run_config.hpp>

namespace v2::calibration {

/**
 * CalibrationFitter: Robust parameter estimation from measurements
 * 
 * Implements bounded, conservative fitting of correction factors.
 * Uses least-squares with bounded optimization.
 */
class CalibrationFitter {
public:
    /**
     * Fit correction factors from measurement dataset
     * 
     * @param dataset Measurement data for fitting
     * @param config Run configuration (for seed, traceability)
     * @param initial_state Starting calibration state (optional)
     * @return Fit result with calibrated state
     */
    static FitResult fit(
        const CalibrationDataset& dataset,
        const core::RunConfig& config,
        const CalibrationState& initial_state = CalibrationState::create_default_bounded()
    );
    
    /**
     * Evaluate residuals (predicted - measured) for given state
     * 
     * @param dataset Measurement data
     * @param state Current calibration state
     * @return RMS residual
     */
    static double evaluate_residuals(
        const CalibrationDataset& dataset,
        const CalibrationState& state
    );
    
    /**
     * Assess confidence level based on fit quality
     * 
     * @param fit_result Completed fit result
     * @return Confidence assessment
     */
    static ConfidenceLevel assess_confidence(const FitResult& fit_result);

private:
    // Internal helper: simple bounded least squares
    static void bounded_least_squares(
        const CalibrationDataset& dataset,
        CalibrationState& state,
        int max_iterations = 100
    );
};

} // namespace v2::calibration
