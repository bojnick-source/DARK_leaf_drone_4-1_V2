/*
================================================================================
v2 Sampling Tests — Agentic Sampling and Boundary Discovery
FILE: v2/engine/tests/sampling/sampling_test.cpp

Purpose:
  - Verify sampling policy determinism
  - Test acquisition scoring and ranking
  - Validate boundary proximity estimation
  - Ensure reporting-only (no automatic decisions)
================================================================================
*/

#include "v2/sampling/sampling_policy.hpp"
#include "v2/sampling/uncertainty_driven_policy.hpp"
#include "v2/sampling/types.hpp"
#include "v2/core/run_config.hpp"
#include <iostream>
#include <cassert>
#include <cmath>

void test_sampling_types() {
    std::cout << "Test: Sampling types creation..." << std::endl;
    
    // Create evaluated design
    v2::sampling::EvaluatedDesign eval_design;
    eval_design.design_id = "design_001";
    eval_design.geometry.rotor_radius_m = 0.5;
    eval_design.geometry.rotor_count = 4;
    eval_design.constraint_margins["max_disk_loading"] = 50.0;
    
    // Create proposed design
    v2::sampling::ProposedDesign prop_design;
    prop_design.proposal_id = "proposal_001";
    prop_design.rank = 1;
    prop_design.geometry.rotor_radius_m = 0.55;
    prop_design.geometry.rotor_count = 4;
    prop_design.acquisition_score.total_value = 0.85;
    prop_design.rationale = "High uncertainty region";
    
    assert(!eval_design.design_id.empty());
    assert(!prop_design.proposal_id.empty());
    assert(prop_design.acquisition_score.total_value > 0.0);
    
    std::cout << "  Evaluated design: " << eval_design.design_id << std::endl;
    std::cout << "  Proposed design: " << prop_design.proposal_id << std::endl;
    std::cout << "  PASS" << std::endl;
}

void test_uncertainty_driven_policy_creation() {
    std::cout << "Test: UncertaintyDrivenPolicy creation..." << std::endl;
    
    v2::sampling::UncertaintyDrivenPolicy::Parameters params;
    params.exploration_weight = 0.4;
    params.boundary_weight = 0.4;
    params.diversity_weight = 0.2;
    
    v2::sampling::UncertaintyDrivenPolicy policy(params);
    
    assert(policy.get_policy_name() == "UncertaintyDrivenPolicy");
    
    std::cout << "  Policy name: " << policy.get_policy_name() << std::endl;
    std::cout << "  PASS" << std::endl;
}

void test_sampling_determinism() {
    std::cout << "Test: Sampling determinism (same seed ⇒ same proposals)..." << std::endl;
    
    // Create policy
    v2::sampling::UncertaintyDrivenPolicy policy;
    
    // Create run configs with same seed
    auto config1 = v2::core::RunConfig::create_with_build_info(12345);
    auto config2 = v2::core::RunConfig::create_with_build_info(12345);  // Same seed
    
    // Create some evaluated designs
    std::vector<v2::sampling::EvaluatedDesign> evaluated_designs;
    
    v2::sampling::EvaluatedDesign eval1;
    eval1.design_id = "design_001";
    eval1.geometry.rotor_radius_m = 0.5;
    eval1.geometry.rotor_count = 4;
    
    // Add mock risk report
    v2::uncertainty::MonteCarloResult result;
    result.output_name = "hover_power_W";
    result.nominal_value = 1000.0;
    result.p50_value = 1050.0;
    result.p90_value = 1150.0;
    eval1.risk_report.output_results.push_back(result);
    
    evaluated_designs.push_back(eval1);
    
    // Propose candidates twice with same seed
    auto proposals1 = policy.propose_next_candidates(evaluated_designs, config1, 3);
    auto proposals2 = policy.propose_next_candidates(evaluated_designs, config2, 3);
    
    // Should be identical (deterministic)
    assert(proposals1.size() == proposals2.size());
    
    for (size_t i = 0; i < proposals1.size(); ++i) {
        assert(std::abs(proposals1[i].geometry.rotor_radius_m - proposals2[i].geometry.rotor_radius_m) < 1e-9);
        assert(std::abs(proposals1[i].acquisition_score.total_value - proposals2[i].acquisition_score.total_value) < 1e-9);
        assert(proposals1[i].rank == proposals2[i].rank);
    }
    
    std::cout << "  Proposals 1 count: " << proposals1.size() << std::endl;
    std::cout << "  Proposals 2 count: " << proposals2.size() << std::endl;
    std::cout << "  Rank 1 value: " << proposals1[0].acquisition_score.total_value << std::endl;
    std::cout << "  PASS (deterministic)" << std::endl;
}

void test_proposal_ranking() {
    std::cout << "Test: Proposal ranking (by acquisition value)..." << std::endl;
    
    v2::sampling::UncertaintyDrivenPolicy policy;
    auto config = v2::core::RunConfig::create_with_build_info(54321);
    
    // Create evaluated designs
    std::vector<v2::sampling::EvaluatedDesign> evaluated_designs;
    
    for (int i = 0; i < 3; ++i) {
        v2::sampling::EvaluatedDesign eval;
        eval.design_id = "design_00" + std::to_string(i + 1);
        eval.geometry.rotor_radius_m = 0.4 + (i * 0.1);
        eval.geometry.rotor_count = 4;
        
        v2::uncertainty::MonteCarloResult result;
        result.output_name = "hover_power_W";
        result.p50_value = 1000.0 + (i * 50.0);
        result.p90_value = 1100.0 + (i * 60.0);
        eval.risk_report.output_results.push_back(result);
        
        evaluated_designs.push_back(eval);
    }
    
    // Propose candidates
    auto proposals = policy.propose_next_candidates(evaluated_designs, config, 5);
    
    assert(!proposals.empty());
    assert(proposals.size() <= 5);
    
    // Verify ranking is in descending order of acquisition value
    for (size_t i = 1; i < proposals.size(); ++i) {
        assert(proposals[i-1].acquisition_score.total_value >= proposals[i].acquisition_score.total_value);
        assert(proposals[i-1].rank < proposals[i].rank);
    }
    
    std::cout << "  Proposal count: " << proposals.size() << std::endl;
    std::cout << "  Top proposal value: " << proposals[0].acquisition_score.total_value << std::endl;
    std::cout << "  Top proposal rank: " << proposals[0].rank << std::endl;
    std::cout << "  PASS (properly ranked)" << std::endl;
}

void test_sampling_report_generation() {
    std::cout << "Test: SamplingReport generation and serialization..." << std::endl;
    
    v2::sampling::SamplingReport report;
    report.run_id = "test_run_001";
    report.seed = 42;
    report.policy_name = "UncertaintyDrivenPolicy";
    report.timestamp = "2026-01-11 12:00:00";
    report.num_evaluated_designs = 3;
    report.evaluated_design_ids = {"design_001", "design_002", "design_003"};
    
    // Add a proposal
    v2::sampling::ProposedDesign prop;
    prop.proposal_id = "proposal_001";
    prop.rank = 1;
    prop.geometry.rotor_radius_m = 0.55;
    prop.geometry.rotor_count = 4;
    prop.acquisition_score.total_value = 0.85;
    prop.acquisition_score.exploration_value = 0.3;
    prop.acquisition_score.boundary_value = 0.4;
    prop.acquisition_score.strategy_used = "boundary";
    prop.rationale = "Near constraint boundary";
    prop.parent_design_id = "design_001";
    report.proposals.push_back(prop);
    
    report.best_acquisition_value = 0.85;
    report.mean_acquisition_value = 0.85;
    report.dominant_strategy = "boundary";
    
    // Serialize to JSON
    std::string json = report.to_json();
    
    // Verify JSON contains key fields
    assert(json.find("\"run_id\": \"test_run_001\"") != std::string::npos);
    assert(json.find("\"seed\": 42") != std::string::npos);
    assert(json.find("\"policy_name\": \"UncertaintyDrivenPolicy\"") != std::string::npos);
    assert(json.find("\"proposals\"") != std::string::npos);
    assert(json.find("\"acquisition_score\"") != std::string::npos);
    assert(json.find("\"boundary\"") != std::string::npos);
    
    std::cout << "  JSON length: " << json.length() << " characters" << std::endl;
    std::cout << "  PASS" << std::endl;
}

void test_no_automatic_decisions() {
    std::cout << "Test: Reporting-only (no automatic accept/reject)..." << std::endl;
    
    v2::sampling::UncertaintyDrivenPolicy policy;
    auto config = v2::core::RunConfig::create_with_build_info(99999);
    
    // Create evaluated designs with constraint violations
    std::vector<v2::sampling::EvaluatedDesign> evaluated_designs;
    
    v2::sampling::EvaluatedDesign eval;
    eval.design_id = "infeasible_design";
    eval.geometry.rotor_radius_m = 0.3;  // Very small (likely infeasible)
    eval.geometry.rotor_count = 2;
    eval.constraint_margins["max_disk_loading"] = -50.0;  // VIOLATED (negative margin)
    evaluated_designs.push_back(eval);
    
    // Policy should still propose candidates (no automatic rejection)
    auto proposals = policy.propose_next_candidates(evaluated_designs, config, 3);
    
    // Verify proposals are generated despite violations
    assert(!proposals.empty());
    
    // Verify no "accept" or "reject" flags in proposals (reporting only)
    for (const auto& prop : proposals) {
        // ProposedDesign has no accept/reject fields - it's reporting only
        assert(!prop.proposal_id.empty());
        assert(prop.acquisition_score.total_value >= 0.0);
    }
    
    std::cout << "  Proposals generated despite violations: " << proposals.size() << std::endl;
    std::cout << "  PASS (reporting-only, no automatic decisions)" << std::endl;
}

int main() {
    std::cout << "=== Agentic Sampling and Boundary Discovery Tests ===" << std::endl;
    
    test_sampling_types();
    test_uncertainty_driven_policy_creation();
    test_sampling_determinism();
    test_proposal_ranking();
    test_sampling_report_generation();
    test_no_automatic_decisions();
    
    std::cout << "\nAll sampling tests passed!" << std::endl;
    return 0;
}
