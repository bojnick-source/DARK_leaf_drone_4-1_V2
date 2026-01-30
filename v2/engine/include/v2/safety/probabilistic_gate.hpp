#pragma once
/*
================================================================================
v2 Safety — Probabilistic Safety Gate
FILE: v2/engine/include/v2/safety/probabilistic_gate.hpp

Purpose:
  - Concrete implementation of SafetyGate
  - Probabilistic evaluation with explicit thresholds
  - Conservative decisions under uncertainty
  - Confidence-aware (defer when uncertain)

Decision Logic:
  - Hard constraints: P(violation) < 0.1%
  - Soft constraints: P(violation) < 10%
  - Confidence: Check sample count and variance
  - Conservative: Use P90 for safety margins
================================================================================
*/

#include "v2/safety/safety_gate.hpp"

namespace v2::safety {

/**
 * ProbabilisticSafetyGate: Evidence-based safety decisions
 * 
 * Strategy:
 * 1. Evaluate each constraint (hard/soft)
 * 2. Check violation probabilities against thresholds
 * 3. Assess confidence validity
 * 4. Make conservative decision (ACCEPT/REJECT/DEFER)
 */
class ProbabilisticSafetyGate : public SafetyGate {
public:
    /**
     * Constructor
     */
    ProbabilisticSafetyGate() = default;
    
    /**
     * Evaluate design for safety
     */
    SafetyDecisionRecord evaluate_safety(
        const uncertainty::RiskReport& risk_report,
        const SafetyThresholds& thresholds,
        const core::RunConfig& config) const override;
    
    /**
     * Get gate name
     */
    std::string get_gate_name() const override {
        return "ProbabilisticSafetyGate";
    }

private:
    /**
     * Evaluate a single constraint
     */
    ConstraintEvaluation evaluate_constraint(
        const std::string& constraint_name,
        const uncertainty::ConstraintRiskRecord& risk_record,
        const SafetyThresholds& thresholds) const;
    
    /**
     * Assess confidence validity
     */
    ConfidenceState assess_confidence(
        const uncertainty::RiskReport& risk_report,
        const SafetyThresholds& thresholds) const;
    
    /**
     * Make final decision based on constraint evaluations
     */
    SafetyDecision make_decision(
        const std::vector<ConstraintEvaluation>& constraint_evals,
        ConfidenceState confidence_state) const;
    
    /**
     * Generate decision rationale
     */
    std::string generate_rationale(
        SafetyDecision decision,
        const std::vector<ConstraintEvaluation>& constraint_evals,
        ConfidenceState confidence_state) const;
    
    /**
     * Generate recommendations
     */
    std::vector<std::string> generate_recommendations(
        SafetyDecision decision,
        const std::vector<ConstraintEvaluation>& constraint_evals,
        ConfidenceState confidence_state) const;
};

} // namespace v2::safety
