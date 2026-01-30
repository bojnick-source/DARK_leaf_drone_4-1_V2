/*
================================================================================
v2 Uncertainty Tests — Monte Carlo and Risk Assessment
FILE: v2/engine/tests/uncertainty/uncertainty_test.cpp

Purpose:
  - Verify Monte Carlo sampling and statistics
  - Test determinism (same seed ⇒ same distributions)
  - Validate risk report generation
  - Ensure wrapper-only design (no solver modifications)
================================================================================
*/

#include "v2/uncertainty/types.hpp"
#include "v2/uncertainty/monte_carlo_evaluator.hpp"
#include "v2/core/run_config.hpp"
#include <iostream>
#include <cassert>
#include <cmath>

void test_uncertainty_config_creation() {
    std::cout << "Test: UncertaintyConfig creation..." << std::endl;
    
    auto config = v2::uncertainty::UncertaintyConfig::create_default();
    
    assert(config.sample_count == 200);
    assert(config.parameters.size() >= 3);  // At least 3 parameters
    
    // Check that motor efficiency multiplier exists
    bool found_motor_eff = false;
    for (const auto& param : config.parameters) {
        if (param.name == "motor_efficiency_multiplier") {
            found_motor_eff = true;
            assert(param.nominal_value == 1.0);
            assert(param.stddev > 0.0);
        }
    }
    assert(found_motor_eff);
    
    std::cout << "  Sample count: " << config.sample_count << std::endl;
    std::cout << "  Parameter count: " << config.parameters.size() << std::endl;
    std::cout << "  PASS" << std::endl;
}

void test_monte_carlo_determinism() {
    std::cout << "Test: Monte Carlo determinism (same seed ⇒ same results)..." << std::endl;
    
    // Create two identical configs with same seed
    auto uncertainty_config = v2::uncertainty::UncertaintyConfig::create_default();
    uncertainty_config.sample_count = 50;  // Smaller for faster test
    
    auto run_config1 = v2::core::RunConfig::create_with_build_info(12345);
    auto run_config2 = v2::core::RunConfig::create_with_build_info(12345);  // Same seed
    
    v2::uncertainty::MonteCarloEvaluator evaluator1(uncertainty_config, run_config1);
    v2::uncertainty::MonteCarloEvaluator evaluator2(uncertainty_config, run_config2);
    
    // Create simple deterministic evaluator (mock)
    auto simple_evaluator = [](const v2::physics::RotorGeometry& geom,
                               const v2::uncertainty::PerturbedParameters& perturbed) {
        v2::uncertainty::DeterministicEvaluationResult result;
        // Simple model: power scales with efficiency and induced loss
        result.hover_power_W = 1000.0 / perturbed.motor_efficiency_multiplier * perturbed.induced_loss_factor;
        result.disk_loading_N_per_m2 = 100.0;
        result.total_mass_kg = 10.0 * perturbed.mass_growth_factor;
        result.feasible = true;
        return result;
    };
    
    v2::physics::RotorGeometry nominal_geom;
    nominal_geom.rotor_radius_m = 0.5;
    nominal_geom.rotor_count = 4;
    
    // Evaluate twice with same seed
    auto report1 = evaluator1.evaluate(nominal_geom, simple_evaluator);
    auto report2 = evaluator2.evaluate(nominal_geom, simple_evaluator);
    
    // Results should be identical (deterministic)
    assert(report1.output_results.size() == report2.output_results.size());
    
    for (size_t i = 0; i < report1.output_results.size(); ++i) {
        assert(std::abs(report1.output_results[i].mean_value - report2.output_results[i].mean_value) < 1e-9);
        assert(std::abs(report1.output_results[i].p50_value - report2.output_results[i].p50_value) < 1e-9);
        assert(std::abs(report1.output_results[i].p90_value - report2.output_results[i].p90_value) < 1e-9);
    }
    
    std::cout << "  Report 1 mean power: " << report1.output_results[0].mean_value << " W" << std::endl;
    std::cout << "  Report 2 mean power: " << report2.output_results[0].mean_value << " W" << std::endl;
    std::cout << "  PASS (deterministic)" << std::endl;
}

void test_monte_carlo_statistics() {
    std::cout << "Test: Monte Carlo statistics computation..." << std::endl;
    
    auto uncertainty_config = v2::uncertainty::UncertaintyConfig::create_default();
    uncertainty_config.sample_count = 100;
    
    auto run_config = v2::core::RunConfig::create_with_build_info(54321);
    
    v2::uncertainty::MonteCarloEvaluator evaluator(uncertainty_config, run_config);
    
    // Simple deterministic evaluator
    auto simple_evaluator = [](const v2::physics::RotorGeometry& geom,
                               const v2::uncertainty::PerturbedParameters& perturbed) {
        v2::uncertainty::DeterministicEvaluationResult result;
        result.hover_power_W = 1000.0 / perturbed.motor_efficiency_multiplier * perturbed.induced_loss_factor;
        result.disk_loading_N_per_m2 = 100.0;
        result.total_mass_kg = 10.0 * perturbed.mass_growth_factor;
        return result;
    };
    
    v2::physics::RotorGeometry nominal_geom;
    nominal_geom.rotor_radius_m = 0.5;
    nominal_geom.rotor_count = 4;
    
    auto report = evaluator.evaluate(nominal_geom, simple_evaluator);
    
    // Verify report structure
    assert(!report.run_id.empty());
    assert(report.seed == 54321);
    assert(report.sample_count == 100);
    assert(!report.timestamp.empty());
    assert(!report.output_results.empty());
    
    // Check statistics are reasonable
    for (const auto& output : report.output_results) {
        assert(output.mean_value > 0.0);
        assert(output.stddev_value >= 0.0);
        assert(output.p5_value <= output.p50_value);
        assert(output.p50_value <= output.p90_value);
        assert(output.p90_value <= output.p95_value);
        assert(output.samples.size() == 100);
    }
    
    // Check sensitivity ranking exists
    assert(!report.sensitivity_ranking.empty());
    
    // Verify ranking is sorted
    for (size_t i = 1; i < report.sensitivity_ranking.size(); ++i) {
        assert(report.sensitivity_ranking[i-1].contribution >= report.sensitivity_ranking[i].contribution);
        assert(report.sensitivity_ranking[i].rank == static_cast<int>(i + 1));
    }
    
    std::cout << "  Hover power P50: " << report.output_results[0].p50_value << " W" << std::endl;
    std::cout << "  Hover power P90: " << report.output_results[0].p90_value << " W" << std::endl;
    std::cout << "  Sensitivity rank 1: " << report.sensitivity_ranking[0].parameter_name << std::endl;
    std::cout << "  PASS" << std::endl;
}

void test_risk_report_serialization() {
    std::cout << "Test: RiskReport JSON serialization..." << std::endl;
    
    v2::uncertainty::RiskReport report;
    report.run_id = "test_run_001";
    report.seed = 42;
    report.sample_count = 100;
    report.timestamp = "2026-01-11 12:00:00";
    
    // Add a distribution
    v2::uncertainty::UncertainScalar param;
    param.name = "motor_efficiency_multiplier";
    param.nominal_value = 1.0;
    param.stddev = 0.02;
    param.lower_bound = 0.9;
    param.upper_bound = 1.05;
    report.distributions_used.push_back(param);
    
    // Add an output result
    v2::uncertainty::MonteCarloResult result;
    result.output_name = "hover_power_W";
    result.nominal_value = 1000.0;
    result.mean_value = 1050.0;
    result.stddev_value = 50.0;
    result.p50_value = 1045.0;
    result.p90_value = 1100.0;
    report.output_results.push_back(result);
    
    // Add sensitivity
    v2::uncertainty::SensitivityEntry sens;
    sens.parameter_name = "motor_efficiency_multiplier";
    sens.contribution = 0.85;
    sens.rank = 1;
    report.sensitivity_ranking.push_back(sens);
    
    std::string json = report.to_json();
    
    // Verify JSON contains key fields
    assert(json.find("\"run_id\": \"test_run_001\"") != std::string::npos);
    assert(json.find("\"seed\": 42") != std::string::npos);
    assert(json.find("\"sample_count\": 100") != std::string::npos);
    assert(json.find("\"distributions_used\"") != std::string::npos);
    assert(json.find("\"output_results\"") != std::string::npos);
    assert(json.find("\"sensitivity_ranking\"") != std::string::npos);
    assert(json.find("\"hover_power_W\"") != std::string::npos);
    
    std::cout << "  JSON length: " << json.length() << " characters" << std::endl;
    std::cout << "  PASS" << std::endl;
}

void test_percentile_ordering() {
    std::cout << "Test: Percentile ordering (P5 < P50 < P90 < P95)..." << std::endl;
    
    auto uncertainty_config = v2::uncertainty::UncertaintyConfig::create_default();
    uncertainty_config.sample_count = 200;
    
    auto run_config = v2::core::RunConfig::create_with_build_info(99999);
    
    v2::uncertainty::MonteCarloEvaluator evaluator(uncertainty_config, run_config);
    
    // Evaluator with some variance in all outputs
    auto evaluator_func = [](const v2::physics::RotorGeometry& geom,
                             const v2::uncertainty::PerturbedParameters& perturbed) {
        v2::uncertainty::DeterministicEvaluationResult result;
        // Model with all perturbations affecting power
        result.hover_power_W = 1000.0 
            / perturbed.motor_efficiency_multiplier 
            * perturbed.induced_loss_factor
            * perturbed.profile_drag_multiplier;
        // Add variance to disk loading via mass growth
        result.disk_loading_N_per_m2 = 100.0 * perturbed.mass_growth_factor;
        result.total_mass_kg = 10.0 * perturbed.mass_growth_factor;
        return result;
    };
    
    v2::physics::RotorGeometry nominal_geom;
    nominal_geom.rotor_radius_m = 0.5;
    nominal_geom.rotor_count = 4;
    
    auto report = evaluator.evaluate(nominal_geom, evaluator_func);
    
    // Verify percentile ordering for outputs with variance
    for (const auto& output : report.output_results) {
        // Skip outputs with zero variance
        if (output.stddev_value < 1e-9) {
            std::cout << "  " << output.output_name << ": constant (no variance), skipped" << std::endl;
            continue;
        }
        
        assert(output.p5_value <= output.p50_value);  // Allow equality for edge cases
        assert(output.p50_value <= output.p90_value);
        assert(output.p90_value <= output.p95_value);
        
        std::cout << "  " << output.output_name << ": "
                  << "P5=" << output.p5_value << ", "
                  << "P50=" << output.p50_value << ", "
                  << "P90=" << output.p90_value << ", "
                  << "P95=" << output.p95_value << std::endl;
    }
    
    std::cout << "  PASS (all percentiles properly ordered)" << std::endl;
}

int main() {
    std::cout << "=== Uncertainty and Monte Carlo Tests ===" << std::endl;
    
    test_uncertainty_config_creation();
    test_monte_carlo_determinism();
    test_monte_carlo_statistics();
    test_risk_report_serialization();
    test_percentile_ordering();
    
    std::cout << "\nAll uncertainty tests passed!" << std::endl;
    return 0;
}
