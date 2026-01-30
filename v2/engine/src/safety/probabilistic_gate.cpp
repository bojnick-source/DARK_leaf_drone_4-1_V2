/*
================================================================================
v2 Safety — Probabilistic Safety Gate Implementation
FILE: v2/engine/src/safety/probabilistic_gate.cpp
================================================================================
*/

#include "v2/safety/probabilistic_gate.hpp"
#include <algorithm>
#include <sstream>
#include <ctime>
#include <cmath>

namespace v2::safety {

ConstraintEvaluation ProbabilisticSafetyGate::evaluate_constraint(
    const std::string& constraint_name,
    const uncertainty::ConstraintRiskRecord& risk_record,
    const SafetyThresholds& thresholds) const {
    
    ConstraintEvaluation eval;
    eval.constraint_name = constraint_name;
    
    // Determine constraint type (heuristic based on name)
    if (constraint_name.find("max") != std::string::npos || 
        constraint_name.find("structural") != std::string::npos ||
        constraint_name.find("regulatory") != std::string::npos) {
        eval.type = ConstraintType::HARD;
    } else {
        eval.type = ConstraintType::SOFT;
    }
    
    eval.threshold = risk_record.threshold;
    eval.p50_value = risk_record.p50_value;
    eval.p90_value = risk_record.p90_value;
    eval.violation_probability = risk_record.violation_probability;
    eval.margin = risk_record.threshold - risk_record.p90_value;
    
    // Evaluate pass/fail
    double max_violation_prob = (eval.type == ConstraintType::HARD) 
        ? thresholds.max_violation_prob_hard 
        : thresholds.max_violation_prob_soft;
    
    bool prob_acceptable = eval.violation_probability <= max_violation_prob;
    bool margin_adequate = (eval.margin / eval.threshold) >= thresholds.min_margin_fraction;
    
    eval.passed = prob_acceptable && margin_adequate;
    
    // Generate rationale
    std::ostringstream rationale;
    if (eval.passed) {
        rationale << "PASS: P(violation)=" << eval.violation_probability 
                  << " ≤ " << max_violation_prob
                  << ", margin=" << eval.margin << " (" 
                  << (eval.margin / eval.threshold * 100.0) << "%)";
    } else {
        rationale << "FAIL: ";
        if (!prob_acceptable) {
            rationale << "P(violation)=" << eval.violation_probability 
                      << " > " << max_violation_prob;
        }
        if (!margin_adequate) {
            if (!prob_acceptable) rationale << ", ";
            rationale << "insufficient margin=" << eval.margin;
        }
    }
    eval.rationale = rationale.str();
    
    return eval;
}

ConfidenceState ProbabilisticSafetyGate::assess_confidence(
    const uncertainty::RiskReport& risk_report,
    const SafetyThresholds& thresholds) const {
    
    // Check sample count
    if (risk_report.sample_count < thresholds.min_confidence_samples) {
        return ConfidenceState::LOW;
    }
    
    // Check for high uncertainty (variance too large)
    for (const auto& output : risk_report.output_results) {
        if (output.stddev_value > 0.0 && output.mean_value > 0.0) {
            double cv = output.stddev_value / output.mean_value;  // Coefficient of variation
            if (cv > 0.5) {  // More than 50% variation
                return ConfidenceState::LOW;
            }
        }
    }
    
    // Check for OOD conditions (heuristic: very large percentile spread)
    for (const auto& output : risk_report.output_results) {
        if (output.p95_value > 0.0 && output.p5_value > 0.0) {
            double spread_ratio = output.p95_value / output.p5_value;
            if (spread_ratio > 3.0) {  // P95 > 3x P5
                return ConfidenceState::OOD;
            }
        }
    }
    
    return ConfidenceState::VALID;
}

SafetyDecision ProbabilisticSafetyGate::make_decision(
    const std::vector<ConstraintEvaluation>& constraint_evals,
    ConfidenceState confidence_state) const {
    
    // DEFER if confidence is insufficient
    if (confidence_state != ConfidenceState::VALID) {
        return SafetyDecision::DEFER;
    }
    
    // REJECT if any hard constraint fails
    for (const auto& eval : constraint_evals) {
        if (eval.type == ConstraintType::HARD && !eval.passed) {
            return SafetyDecision::REJECT;
        }
    }
    
    // REJECT if too many soft constraints fail
    int soft_failures = 0;
    int soft_total = 0;
    for (const auto& eval : constraint_evals) {
        if (eval.type == ConstraintType::SOFT) {
            soft_total++;
            if (!eval.passed) soft_failures++;
        }
    }
    
    if (soft_total > 0 && static_cast<double>(soft_failures) / soft_total > 0.5) {
        return SafetyDecision::REJECT;  // More than 50% soft constraints failed
    }
    
    // ACCEPT otherwise
    return SafetyDecision::ACCEPT;
}

std::string ProbabilisticSafetyGate::generate_rationale(
    SafetyDecision decision,
    const std::vector<ConstraintEvaluation>& constraint_evals,
    ConfidenceState confidence_state) const {
    
    std::ostringstream rationale;
    
    switch (decision) {
        case SafetyDecision::ACCEPT:
            rationale << "ACCEPT: All hard constraints passed, acceptable soft constraint performance.";
            break;
        case SafetyDecision::REJECT:
            {
                rationale << "REJECT: ";
                // Find failure reasons
                bool hard_failure = false;
                for (const auto& eval : constraint_evals) {
                    if (eval.type == ConstraintType::HARD && !eval.passed) {
                        hard_failure = true;
                        rationale << "Hard constraint '" << eval.constraint_name << "' failed. ";
                    }
                }
                if (!hard_failure) {
                    rationale << "Excessive soft constraint failures. ";
                }
            }
            break;
        case SafetyDecision::DEFER:
            rationale << "DEFER: ";
            switch (confidence_state) {
                case ConfidenceState::LOW:
                    rationale << "Insufficient confidence (low sample count or high variance).";
                    break;
                case ConfidenceState::OOD:
                    rationale << "Out-of-distribution detection (high uncertainty spread).";
                    break;
                case ConfidenceState::UNCALIBRATED:
                    rationale << "Model not calibrated for this design region.";
                    break;
                case ConfidenceState::VALID:
                    rationale << "Confidence valid but deferred for other reasons.";
                    break;
            }
            break;
    }
    
    return rationale.str();
}

std::vector<std::string> ProbabilisticSafetyGate::generate_recommendations(
    SafetyDecision decision,
    const std::vector<ConstraintEvaluation>& constraint_evals,
    ConfidenceState confidence_state) const {
    
    std::vector<std::string> recommendations;
    
    switch (decision) {
        case SafetyDecision::ACCEPT:
            recommendations.push_back("Design meets safety criteria - proceed to detailed evaluation");
            recommendations.push_back("Consider validation testing for critical parameters");
            break;
        case SafetyDecision::REJECT:
            recommendations.push_back("Design violates safety criteria - do not proceed");
            for (const auto& eval : constraint_evals) {
                if (!eval.passed) {
                    recommendations.push_back("Address constraint: " + eval.constraint_name);
                }
            }
            break;
        case SafetyDecision::DEFER:
            recommendations.push_back("Increase sample count for better confidence");
            if (confidence_state == ConfidenceState::OOD) {
                recommendations.push_back("Design may be outside validated region - proceed with caution");
            }
            recommendations.push_back("Gather additional data before making final decision");
            break;
    }
    
    return recommendations;
}

SafetyDecisionRecord ProbabilisticSafetyGate::evaluate_safety(
    const uncertainty::RiskReport& risk_report,
    const SafetyThresholds& thresholds,
    const core::RunConfig& config) const {
    
    SafetyDecisionRecord record;
    record.design_id = "design_" + risk_report.run_id;  // Derive from risk report
    record.run_id = config.run_id;
    record.seed = config.global_seed;
    record.thresholds = thresholds;
    
    // Generate timestamp
    std::time_t now = std::time(nullptr);
    char timestamp_buf[100];
    std::strftime(timestamp_buf, sizeof(timestamp_buf), "%Y-%m-%d %H:%M:%S", std::localtime(&now));
    record.timestamp = timestamp_buf;
    
    // Assess confidence
    record.confidence_state = assess_confidence(risk_report, thresholds);
    
    // Compute confidence score (simple heuristic)
    record.confidence_score = (record.confidence_state == ConfidenceState::VALID) ? 0.9 : 0.5;
    
    // Evaluate constraints
    for (const auto& constraint_risk : risk_report.constraint_risks) {
        auto eval = evaluate_constraint(constraint_risk.constraint_name, constraint_risk, thresholds);
        record.constraint_evals.push_back(eval);
        
        record.num_constraints_evaluated++;
        if (eval.type == ConstraintType::HARD) {
            if (eval.passed) record.num_hard_constraints_passed++;
            else record.num_hard_constraints_failed++;
        } else {
            if (eval.passed) record.num_soft_constraints_passed++;
            else record.num_soft_constraints_failed++;
        }
    }
    
    // Make decision
    record.decision = make_decision(record.constraint_evals, record.confidence_state);
    record.decision_rationale = generate_rationale(record.decision, record.constraint_evals, record.confidence_state);
    record.recommendations = generate_recommendations(record.decision, record.constraint_evals, record.confidence_state);
    
    return record;
}

} // namespace v2::safety
