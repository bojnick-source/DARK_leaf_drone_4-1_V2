#pragma once
/*
================================================================================
v2 Safety — Types and Data Structures
FILE: v2/engine/include/v2/safety/types.hpp

Purpose:
  - Define decision types for safety gate
  - Store safety decision records with full justification
  - Track constraint evaluations and confidence states
  - Maintain complete audit trail

This implements EXECUTION_0.4: Probabilistic Safety Gate
================================================================================
*/

#include <string>
#include <vector>
#include <map>
#include <cstdint>

namespace v2::safety {

/**
 * SafetyDecision: Final decision outcome
 */
enum class SafetyDecision {
    ACCEPT,     // Design meets all safety criteria
    REJECT,     // Design violates safety criteria
    DEFER       // Insufficient confidence to make decision
};

/**
 * ConstraintType: Classification of constraint severity
 */
enum class ConstraintType {
    HARD,       // Never violate (structural limits, regulations)
    SOFT        // Risk-budgeted (performance targets, margins)
};

/**
 * ConfidenceState: Validity of probabilistic assessments
 */
enum class ConfidenceState {
    VALID,          // Confidence metrics are reliable
    LOW,            // Insufficient samples or high uncertainty
    OOD,            // Out-of-distribution (extrapolation risk)
    UNCALIBRATED    // Model not calibrated for this region
};

/**
 * ConstraintEvaluation: Result of evaluating a single constraint
 */
struct ConstraintEvaluation {
    std::string constraint_name;
    ConstraintType type = ConstraintType::SOFT;
    
    // Threshold and values
    double threshold = 0.0;
    double p50_value = 0.0;             // Median prediction
    double p90_value = 0.0;             // Conservative estimate
    
    // Probabilistic assessment
    double violation_probability = 0.0;  // P(constraint violated)
    double margin = 0.0;                 // Safety margin (threshold - p90)
    
    // Decision
    bool passed = false;                 // Does constraint pass?
    std::string rationale;               // Why passed/failed
};

/**
 * SafetyThresholds: Configurable safety criteria
 */
struct SafetyThresholds {
    double max_violation_prob_hard = 0.001;   // 0.1% for hard constraints
    double max_violation_prob_soft = 0.10;    // 10% for soft constraints
    double min_confidence_samples = 50;       // Minimum MC samples for confidence
    double min_margin_fraction = 0.05;        // 5% safety margin required
    
    /**
     * Create default conservative thresholds
     */
    static SafetyThresholds create_default();
    
    /**
     * Create relaxed thresholds for early exploration
     */
    static SafetyThresholds create_relaxed();
};

/**
 * SafetyDecisionRecord: Complete record of safety gate decision
 * 
 * This is the authoritative artifact for accept/reject decisions.
 */
struct SafetyDecisionRecord {
    // Traceability
    std::string design_id;
    std::string run_id;
    uint64_t seed = 0;
    std::string timestamp;
    
    // Decision outcome
    SafetyDecision decision = SafetyDecision::DEFER;
    std::string decision_rationale;         // High-level explanation
    double confidence_score = 0.0;          // Overall confidence [0, 1]
    ConfidenceState confidence_state = ConfidenceState::UNCALIBRATED;
    
    // Constraint evaluations
    std::vector<ConstraintEvaluation> constraint_evals;
    
    // Evidence summary
    int num_constraints_evaluated = 0;
    int num_hard_constraints_passed = 0;
    int num_soft_constraints_passed = 0;
    int num_hard_constraints_failed = 0;
    int num_soft_constraints_failed = 0;
    
    // Thresholds used
    SafetyThresholds thresholds;
    
    // Recommendations
    std::vector<std::string> recommendations;  // What to do next
    
    /**
     * Serialize to JSON for artifact emission
     */
    std::string to_json() const;
    
    /**
     * Write record to file
     */
    void write_to_file(const std::string& filepath) const;
};

/**
 * SafetyStatistics: Aggregate safety stats across multiple evaluations
 */
struct SafetyStatistics {
    int total_evaluations = 0;
    int num_accepted = 0;
    int num_rejected = 0;
    int num_deferred = 0;
    
    double accept_rate = 0.0;
    double reject_rate = 0.0;
    double defer_rate = 0.0;
    
    // Most common failure modes
    std::map<std::string, int> constraint_failure_counts;
};

} // namespace v2::safety
