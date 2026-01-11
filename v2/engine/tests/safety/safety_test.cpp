/*
================================================================================
v2 Safety Tests — Probabilistic Safety Gate
FILE: v2/engine/tests/safety/safety_test.cpp

Purpose:
  - Verify safety gate decision logic
  - Test constraint evaluation (hard/soft)
  - Validate confidence assessment
  - Ensure auditable decisions with full justification
================================================================================
*/

#include "v2/safety/safety_gate.hpp"
#include "v2/safety/probabilistic_gate.hpp"
#include "v2/safety/types.hpp"
#include "v2/uncertainty/types.hpp"
#include "v2/core/run_config.hpp"
#include <iostream>
#include <cassert>
#include <cmath>

void test_safety_types() {
    std::cout << "Test: Safety types creation..." << std::endl;
    
    // Create thresholds
    auto thresholds = v2::safety::SafetyThresholds::create_default();
    assert(thresholds.max_violation_prob_hard < thresholds.max_violation_prob_soft);
    assert(thresholds.min_confidence_samples > 0);
    
    // Create decision record
    v2::safety::SafetyDecisionRecord record;
    record.design_id = "design_001";
    record.decision = v2::safety::SafetyDecision::ACCEPT;
    record.confidence_state = v2::safety::ConfidenceState::VALID;
    
    assert(!record.design_id.empty());
    assert(record.decision == v2::safety::SafetyDecision::ACCEPT);
    
    std::cout << "  Max hard violation prob: " << thresholds.max_violation_prob_hard << std::endl;
    std::cout << "  Max soft violation prob: " << thresholds.max_violation_prob_soft << std::endl;
    std::cout << "  PASS" << std::endl;
}

void test_safety_gate_accept() {
    std::cout << "Test: Safety gate ACCEPT decision..." << std::endl;
    
    v2::safety::ProbabilisticSafetyGate gate;
    auto config = v2::core::RunConfig::create_with_build_info(12345);
    auto thresholds = v2::safety::SafetyThresholds::create_default();
    
    // Create risk report with constraints that pass
    v2::uncertainty::RiskReport risk_report;
    risk_report.run_id = "test_run_001";
    risk_report.sample_count = 200;  // Sufficient samples
    
    // Add output result (low uncertainty)
    v2::uncertainty::MonteCarloResult result;
    result.output_name = "hover_power_W";
    result.mean_value = 1000.0;
    result.stddev_value = 50.0;  // Low variance
    result.p5_value = 950.0;
    result.p95_value = 1050.0;   // Narrow spread
    risk_report.output_results.push_back(result);
    
    // Add constraint that passes
    v2::uncertainty::ConstraintRiskRecord constraint;
    constraint.constraint_name = "max_disk_loading";
    constraint.threshold = 150.0;
    constraint.p50_value = 100.0;
    constraint.p90_value = 110.0;  // Well below threshold
    constraint.violation_probability = 0.0001;  // Very low
    risk_report.constraint_risks.push_back(constraint);
    
    // Evaluate safety
    auto decision_record = gate.evaluate_safety(risk_report, thresholds, config);
    
    assert(decision_record.decision == v2::safety::SafetyDecision::ACCEPT);
    assert(decision_record.confidence_state == v2::safety::ConfidenceState::VALID);
    assert(!decision_record.decision_rationale.empty());
    assert(!decision_record.recommendations.empty());
    
    std::cout << "  Decision: ACCEPT" << std::endl;
    std::cout << "  Rationale: " << decision_record.decision_rationale << std::endl;
    std::cout << "  PASS" << std::endl;
}

void test_safety_gate_reject_hard_constraint() {
    std::cout << "Test: Safety gate REJECT (hard constraint violation)..." << std::endl;
    
    v2::safety::ProbabilisticSafetyGate gate;
    auto config = v2::core::RunConfig::create_with_build_info(54321);
    auto thresholds = v2::safety::SafetyThresholds::create_default();
    
    // Create risk report with hard constraint violation
    v2::uncertainty::RiskReport risk_report;
    risk_report.run_id = "test_run_002";
    risk_report.sample_count = 200;
    
    v2::uncertainty::MonteCarloResult result;
    result.output_name = "hover_power_W";
    result.mean_value = 1000.0;
    result.stddev_value = 50.0;
    result.p5_value = 950.0;
    result.p95_value = 1050.0;
    risk_report.output_results.push_back(result);
    
    // Add hard constraint that FAILS
    v2::uncertainty::ConstraintRiskRecord constraint;
    constraint.constraint_name = "max_structural_load";  // "max" triggers HARD classification
    constraint.threshold = 100.0;
    constraint.p50_value = 105.0;
    constraint.p90_value = 120.0;  // Exceeds threshold
    constraint.violation_probability = 0.15;  // High violation probability
    risk_report.constraint_risks.push_back(constraint);
    
    // Evaluate safety
    auto decision_record = gate.evaluate_safety(risk_report, thresholds, config);
    
    assert(decision_record.decision == v2::safety::SafetyDecision::REJECT);
    assert(decision_record.num_hard_constraints_failed > 0);
    assert(!decision_record.decision_rationale.empty());
    
    std::cout << "  Decision: REJECT" << std::endl;
    std::cout << "  Rationale: " << decision_record.decision_rationale << std::endl;
    std::cout << "  PASS" << std::endl;
}

void test_safety_gate_defer_low_confidence() {
    std::cout << "Test: Safety gate DEFER (low confidence)..." << std::endl;
    
    v2::safety::ProbabilisticSafetyGate gate;
    auto config = v2::core::RunConfig::create_with_build_info(99999);
    auto thresholds = v2::safety::SafetyThresholds::create_default();
    
    // Create risk report with LOW confidence
    v2::uncertainty::RiskReport risk_report;
    risk_report.run_id = "test_run_003";
    risk_report.sample_count = 30;  // Below min_confidence_samples (50)
    
    v2::uncertainty::MonteCarloResult result;
    result.output_name = "hover_power_W";
    result.mean_value = 1000.0;
    result.stddev_value = 600.0;  // High variance (CV > 0.5)
    result.p5_value = 400.0;
    result.p95_value = 1600.0;
    risk_report.output_results.push_back(result);
    
    // Add constraint (would pass, but confidence is low)
    v2::uncertainty::ConstraintRiskRecord constraint;
    constraint.constraint_name = "max_disk_loading";
    constraint.threshold = 150.0;
    constraint.p50_value = 100.0;
    constraint.p90_value = 110.0;
    constraint.violation_probability = 0.001;
    risk_report.constraint_risks.push_back(constraint);
    
    // Evaluate safety
    auto decision_record = gate.evaluate_safety(risk_report, thresholds, config);
    
    assert(decision_record.decision == v2::safety::SafetyDecision::DEFER);
    assert(decision_record.confidence_state != v2::safety::ConfidenceState::VALID);
    assert(!decision_record.decision_rationale.empty());
    
    std::cout << "  Decision: DEFER" << std::endl;
    std::cout << "  Confidence state: LOW" << std::endl;
    std::cout << "  Rationale: " << decision_record.decision_rationale << std::endl;
    std::cout << "  PASS" << std::endl;
}

void test_decision_record_serialization() {
    std::cout << "Test: SafetyDecisionRecord JSON serialization..." << std::endl;
    
    v2::safety::SafetyDecisionRecord record;
    record.design_id = "design_test";
    record.run_id = "run_test";
    record.seed = 42;
    record.timestamp = "2026-01-11 12:00:00";
    record.decision = v2::safety::SafetyDecision::ACCEPT;
    record.decision_rationale = "All criteria met";
    record.confidence_score = 0.9;
    record.confidence_state = v2::safety::ConfidenceState::VALID;
    record.num_constraints_evaluated = 1;
    record.num_hard_constraints_passed = 1;
    record.thresholds = v2::safety::SafetyThresholds::create_default();
    
    // Add a constraint evaluation
    v2::safety::ConstraintEvaluation eval;
    eval.constraint_name = "max_disk_loading";
    eval.type = v2::safety::ConstraintType::HARD;
    eval.threshold = 150.0;
    eval.p50_value = 100.0;
    eval.p90_value = 110.0;
    eval.violation_probability = 0.0001;
    eval.margin = 40.0;
    eval.passed = true;
    eval.rationale = "Well below threshold";
    record.constraint_evals.push_back(eval);
    
    record.recommendations.push_back("Proceed to detailed evaluation");
    
    // Serialize to JSON
    std::string json = record.to_json();
    
    // Verify JSON contains key fields
    assert(json.find("\"decision\": \"ACCEPT\"") != std::string::npos);
    assert(json.find("\"confidence_state\": \"VALID\"") != std::string::npos);
    assert(json.find("\"constraint_evaluations\"") != std::string::npos);
    assert(json.find("\"max_disk_loading\"") != std::string::npos);
    assert(json.find("\"recommendations\"") != std::string::npos);
    
    std::cout << "  JSON length: " << json.length() << " characters" << std::endl;
    std::cout << "  PASS" << std::endl;
}

void test_auditability_and_traceability() {
    std::cout << "Test: Auditability and traceability..." << std::endl;
    
    v2::safety::ProbabilisticSafetyGate gate;
    auto config = v2::core::RunConfig::create_with_build_info(11111);
    auto thresholds = v2::safety::SafetyThresholds::create_default();
    
    // Create risk report
    v2::uncertainty::RiskReport risk_report;
    risk_report.run_id = "test_run_audit";
    risk_report.sample_count = 200;
    
    v2::uncertainty::MonteCarloResult result;
    result.output_name = "hover_power_W";
    result.mean_value = 1000.0;
    result.stddev_value = 50.0;
    result.p5_value = 950.0;
    result.p95_value = 1050.0;
    risk_report.output_results.push_back(result);
    
    v2::uncertainty::ConstraintRiskRecord constraint;
    constraint.constraint_name = "max_disk_loading";
    constraint.threshold = 150.0;
    constraint.p50_value = 100.0;
    constraint.p90_value = 110.0;
    constraint.violation_probability = 0.0001;
    risk_report.constraint_risks.push_back(constraint);
    
    // Evaluate safety
    auto decision_record = gate.evaluate_safety(risk_report, thresholds, config);
    
    // Verify full traceability
    assert(!decision_record.design_id.empty());
    assert(!decision_record.run_id.empty());
    assert(decision_record.seed == config.global_seed);
    assert(!decision_record.timestamp.empty());
    assert(!decision_record.decision_rationale.empty());
    assert(!decision_record.constraint_evals.empty());
    
    // Verify every constraint has rationale
    for (const auto& eval : decision_record.constraint_evals) {
        assert(!eval.constraint_name.empty());
        assert(!eval.rationale.empty());
    }
    
    std::cout << "  Design ID: " << decision_record.design_id << std::endl;
    std::cout << "  Run ID: " << decision_record.run_id << std::endl;
    std::cout << "  Seed: " << decision_record.seed << std::endl;
    std::cout << "  Constraints evaluated: " << decision_record.num_constraints_evaluated << std::endl;
    std::cout << "  PASS (fully auditable)" << std::endl;
}

void test_conservative_under_uncertainty() {
    std::cout << "Test: Conservative decisions under uncertainty..." << std::endl;
    
    v2::safety::ProbabilisticSafetyGate gate;
    auto config = v2::core::RunConfig::create_with_build_info(22222);
    auto thresholds = v2::safety::SafetyThresholds::create_default();
    
    // Create risk report with borderline constraint
    v2::uncertainty::RiskReport risk_report;
    risk_report.run_id = "test_run_conservative";
    risk_report.sample_count = 200;
    
    v2::uncertainty::MonteCarloResult result;
    result.output_name = "hover_power_W";
    result.mean_value = 1000.0;
    result.stddev_value = 50.0;
    result.p5_value = 950.0;
    result.p95_value = 1050.0;
    risk_report.output_results.push_back(result);
    
    // Borderline constraint: P90 close to threshold
    v2::uncertainty::ConstraintRiskRecord constraint;
    constraint.constraint_name = "max_power_limit";
    constraint.threshold = 1000.0;
    constraint.p50_value = 950.0;
    constraint.p90_value = 990.0;  // Just below threshold (1% margin)
    constraint.violation_probability = 0.05;  // 5% violation probability
    risk_report.constraint_risks.push_back(constraint);
    
    // Evaluate safety
    auto decision_record = gate.evaluate_safety(risk_report, thresholds, config);
    
    // Should reject due to insufficient margin (< 5%)
    assert(decision_record.decision == v2::safety::SafetyDecision::REJECT);
    
    std::cout << "  Decision: REJECT (conservative)" << std::endl;
    std::cout << "  Margin: " << (990.0 / 1000.0 * 100.0 - 100.0) << "% (insufficient)" << std::endl;
    std::cout << "  PASS (appropriately conservative)" << std::endl;
}

int main() {
    std::cout << "=== Probabilistic Safety Gate Tests ===" << std::endl;
    
    test_safety_types();
    test_safety_gate_accept();
    test_safety_gate_reject_hard_constraint();
    test_safety_gate_defer_low_confidence();
    test_decision_record_serialization();
    test_auditability_and_traceability();
    test_conservative_under_uncertainty();
    
    std::cout << "\nAll safety tests passed!" << std::endl;
    return 0;
}
