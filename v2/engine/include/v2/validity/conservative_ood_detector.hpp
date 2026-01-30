#pragma once
/*
================================================================================
v2 Validity — Conservative OOD Detector Implementation
FILE: v2/engine/include/v2/validity/conservative_ood_detector.hpp

Purpose:
  - Concrete implementation of OOD detection
  - Conservative approach: flag suspicious distributions
  - Deterministic metrics from existing Monte Carlo outputs
  
This implements EXECUTION_0.6: OOD Detection + Conservative Validity Gating
================================================================================
*/

#include "ood_detector.hpp"

namespace v2::validity {

/**
 * ConservativeOODDetector: Conservative validity assessment
 * 
 * Implements OOD detection using deterministic metrics:
 * 1. Percentile spread ratio: (P95 - P5) / max(|P50|, eps)
 * 2. Coefficient of variation: stddev / mean for each output
 * 3. Calibration drift: deviation from nominal after calibration
 * 4. Sample count adequacy: minimum samples required
 * 
 * Classification logic:
 * - VALID: No flags, adequate samples
 * - LOW_CONFIDENCE: 1 minor flag OR low sample count
 * - OUT_OF_DISTRIBUTION: 2+ flags OR critical threshold exceeded
 */
class ConservativeOODDetector : public OODDetector {
public:
    ConservativeOODDetector() = default;
    ~ConservativeOODDetector() override = default;
    
    /**
     * Assess validity of RiskReport outputs
     */
    ValidityAssessment assess_validity(
        const uncertainty::RiskReport& risk_report,
        const calibration::CalibrationState& calibration_state,
        const OODThresholds& thresholds = OODThresholds::create_default()
    ) const override;
    
private:
    /**
     * Evaluate percentile spread ratio for each output
     */
    std::vector<OODMetric> evaluate_spread_ratios(
        const uncertainty::RiskReport& risk_report,
        const OODThresholds& thresholds
    ) const;
    
    /**
     * Evaluate coefficient of variation for each output
     */
    std::vector<OODMetric> evaluate_coeff_variation(
        const uncertainty::RiskReport& risk_report,
        const OODThresholds& thresholds
    ) const;
    
    /**
     * Evaluate calibration drift (if calibrated)
     */
    std::vector<OODMetric> evaluate_calibration_drift(
        const uncertainty::RiskReport& risk_report,
        const calibration::CalibrationState& calibration_state,
        const OODThresholds& thresholds
    ) const;
    
    /**
     * Evaluate sample count adequacy
     */
    OODMetric evaluate_sample_adequacy(
        const uncertainty::RiskReport& risk_report,
        const OODThresholds& thresholds
    ) const;
    
    /**
     * Classify validity state based on flagged metrics
     */
    ValidityState classify_state(
        const std::vector<OODMetric>& all_metrics,
        uint32_t sample_count,
        const OODThresholds& thresholds
    ) const;
    
    /**
     * Generate recommendations based on validity state
     */
    std::vector<std::string> generate_recommendations(
        ValidityState state,
        const std::vector<OODMetric>& flagged_metrics
    ) const;
};

} // namespace v2::validity
