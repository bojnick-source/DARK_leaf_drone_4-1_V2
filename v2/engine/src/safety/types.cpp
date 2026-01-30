/*
================================================================================
v2 Safety — Types Implementation
FILE: v2/engine/src/safety/types.cpp
================================================================================
*/

#include "v2/safety/types.hpp"
#include <sstream>
#include <fstream>
#include <iomanip>

namespace v2::safety {

SafetyThresholds SafetyThresholds::create_default() {
    SafetyThresholds thresholds;
    thresholds.max_violation_prob_hard = 0.001;  // 0.1%
    thresholds.max_violation_prob_soft = 0.10;   // 10%
    thresholds.min_confidence_samples = 50;
    thresholds.min_margin_fraction = 0.05;       // 5%
    return thresholds;
}

SafetyThresholds SafetyThresholds::create_relaxed() {
    SafetyThresholds thresholds;
    thresholds.max_violation_prob_hard = 0.01;   // 1% (more relaxed)
    thresholds.max_violation_prob_soft = 0.20;   // 20%
    thresholds.min_confidence_samples = 30;
    thresholds.min_margin_fraction = 0.02;       // 2%
    return thresholds;
}

std::string SafetyDecisionRecord::to_json() const {
    std::ostringstream json;
    json << std::fixed << std::setprecision(6);
    
    json << "{\n";
    json << "  \"design_id\": \"" << design_id << "\",\n";
    json << "  \"run_id\": \"" << run_id << "\",\n";
    json << "  \"seed\": " << seed << ",\n";
    json << "  \"timestamp\": \"" << timestamp << "\",\n";
    
    // Decision
    json << "  \"decision\": \"";
    switch (decision) {
        case SafetyDecision::ACCEPT: json << "ACCEPT"; break;
        case SafetyDecision::REJECT: json << "REJECT"; break;
        case SafetyDecision::DEFER: json << "DEFER"; break;
    }
    json << "\",\n";
    
    json << "  \"decision_rationale\": \"" << decision_rationale << "\",\n";
    json << "  \"confidence_score\": " << confidence_score << ",\n";
    json << "  \"confidence_state\": \"";
    switch (confidence_state) {
        case ConfidenceState::VALID: json << "VALID"; break;
        case ConfidenceState::LOW: json << "LOW"; break;
        case ConfidenceState::OOD: json << "OOD"; break;
        case ConfidenceState::UNCALIBRATED: json << "UNCALIBRATED"; break;
    }
    json << "\",\n";
    
    // Evidence summary
    json << "  \"evidence_summary\": {\n";
    json << "    \"num_constraints_evaluated\": " << num_constraints_evaluated << ",\n";
    json << "    \"num_hard_constraints_passed\": " << num_hard_constraints_passed << ",\n";
    json << "    \"num_soft_constraints_passed\": " << num_soft_constraints_passed << ",\n";
    json << "    \"num_hard_constraints_failed\": " << num_hard_constraints_failed << ",\n";
    json << "    \"num_soft_constraints_failed\": " << num_soft_constraints_failed << "\n";
    json << "  },\n";
    
    // Constraint evaluations
    json << "  \"constraint_evaluations\": [\n";
    for (size_t i = 0; i < constraint_evals.size(); ++i) {
        const auto& eval = constraint_evals[i];
        if (i > 0) json << ",\n";
        json << "    {\n";
        json << "      \"constraint\": \"" << eval.constraint_name << "\",\n";
        json << "      \"type\": \"" << (eval.type == ConstraintType::HARD ? "HARD" : "SOFT") << "\",\n";
        json << "      \"threshold\": " << eval.threshold << ",\n";
        json << "      \"p50_value\": " << eval.p50_value << ",\n";
        json << "      \"p90_value\": " << eval.p90_value << ",\n";
        json << "      \"violation_probability\": " << eval.violation_probability << ",\n";
        json << "      \"margin\": " << eval.margin << ",\n";
        json << "      \"passed\": " << (eval.passed ? "true" : "false") << ",\n";
        json << "      \"rationale\": \"" << eval.rationale << "\"\n";
        json << "    }";
    }
    json << "\n  ],\n";
    
    // Thresholds
    json << "  \"thresholds\": {\n";
    json << "    \"max_violation_prob_hard\": " << thresholds.max_violation_prob_hard << ",\n";
    json << "    \"max_violation_prob_soft\": " << thresholds.max_violation_prob_soft << ",\n";
    json << "    \"min_confidence_samples\": " << thresholds.min_confidence_samples << ",\n";
    json << "    \"min_margin_fraction\": " << thresholds.min_margin_fraction << "\n";
    json << "  },\n";
    
    // Recommendations
    json << "  \"recommendations\": [";
    for (size_t i = 0; i < recommendations.size(); ++i) {
        if (i > 0) json << ", ";
        json << "\"" << recommendations[i] << "\"";
    }
    json << "]\n";
    json << "}";
    
    return json.str();
}

void SafetyDecisionRecord::write_to_file(const std::string& filepath) const {
    std::ofstream file(filepath);
    if (!file.is_open()) {
        throw std::runtime_error("Failed to open file for writing: " + filepath);
    }
    file << to_json();
    file.close();
}

} // namespace v2::safety
