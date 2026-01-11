#pragma once
/*
================================================================================
v2 Validity — OOD Detector Interface
FILE: v2/engine/include/v2/validity/ood_detector.hpp

Purpose:
  - Define interface for OOD detection
  - Evaluate validity based on Monte Carlo outputs
  - Pure, stateless, deterministic evaluation
  
This implements EXECUTION_0.6: OOD Detection + Conservative Validity Gating
================================================================================
*/

#include "types.hpp"
#include "../uncertainty/types.hpp"
#include "../calibration/types.hpp"

namespace v2::validity {

/**
 * OODDetector: Interface for out-of-distribution detection
 * 
 * Evaluates whether uncertainty outputs are trustworthy based on:
 * - Distribution shape metrics
 * - Calibration consistency
 * - Sample adequacy
 * 
 * Stateless: all inputs passed explicitly
 * Deterministic: same inputs => same validity assessment
 */
class OODDetector {
public:
    virtual ~OODDetector() = default;
    
    /**
     * Assess validity of RiskReport outputs
     * 
     * @param risk_report - Monte Carlo uncertainty analysis results
     * @param calibration_state - Current calibration (may be UNCALIBRATED)
     * @param thresholds - OOD detection thresholds
     * @return ValidityAssessment with complete evaluation
     */
    virtual ValidityAssessment assess_validity(
        const uncertainty::RiskReport& risk_report,
        const calibration::CalibrationState& calibration_state,
        const OODThresholds& thresholds = OODThresholds::create_default()
    ) const = 0;
};

} // namespace v2::validity
