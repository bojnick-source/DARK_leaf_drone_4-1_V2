/*
================================================================================
v2 Calibration — Tests
FILE: v2/engine/tests/calibration/calibration_test.cpp

Tests:
  - CalibrationState creation, validation, serialization
  - Bounded correction factors
  - Deterministic fitting
  - Calibrated evaluation with corrections
  - JSON artifact generation
  - Confidence assessment
================================================================================
*/

#include <v2/calibration/types.hpp>
#include <v2/calibration/calibration_fitter.hpp>
#include <v2/calibration/calibrated_evaluator.hpp>
#include <v2/core/run_config.hpp>
#include <v2/uncertainty/types.hpp>
#include <iostream>
#include <cassert>
#include <cmath>

using namespace v2::calibration;
using namespace v2::core;
using namespace v2::uncertainty;

void test_calibration_state_creation() {
    std::cout << "Testing CalibrationState creation..." << std::endl;
    
    // Test uncalibrated state
    auto uncalib = CalibrationState::create_uncalibrated();
    assert(uncalib.confidence == ConfidenceLevel::UNCALIBRATED);
    assert(uncalib.correction_factors.size() == 5);
    assert(uncalib.is_valid());
    
    // Check that all factors are identity
    for (const auto& factor : uncalib.correction_factors) {
        if (factor.parameter_name == "air_density_offset") {
            assert(std::abs(factor.value - 0.0) < 1e-9);
        } else {
            assert(std::abs(factor.value - 1.0) < 1e-9);
        }
        assert(factor.is_valid());
    }
    
    // Test bounded state
    auto bounded = CalibrationState::create_default_bounded();
    assert(bounded.is_valid());
    assert(bounded.correction_factors.size() == 5);
    
    // Check specific bounds from EXECUTION_0.5 spec
    auto motor_factor = bounded.get_factor("motor_efficiency_multiplier");
    assert(motor_factor != nullptr);
    assert(std::abs(motor_factor->lower_bound - 0.85) < 1e-9);
    assert(std::abs(motor_factor->upper_bound - 1.15) < 1e-9);
    
    auto drag_factor = bounded.get_factor("profile_drag_multiplier");
    assert(drag_factor != nullptr);
    assert(std::abs(drag_factor->lower_bound - 0.80) < 1e-9);
    assert(std::abs(drag_factor->upper_bound - 1.25) < 1e-9);
    
    std::cout << "  ✓ CalibrationState creation tests passed" << std::endl;
}

void test_correction_factor_bounds() {
    std::cout << "Testing CorrectionFactor bounds..." << std::endl;
    
    CorrectionFactor factor;
    factor.parameter_name = "test_param";
    factor.value = 1.0;
    factor.lower_bound = 0.8;
    factor.upper_bound = 1.2;
    
    assert(factor.is_valid());
    
    // Test clamping
    factor.value = 1.5;  // Above upper bound
    factor.clamp_to_bounds();
    assert(std::abs(factor.value - 1.2) < 1e-9);
    
    factor.value = 0.5;  // Below lower bound
    factor.clamp_to_bounds();
    assert(std::abs(factor.value - 0.8) < 1e-9);
    
    factor.value = 1.0;  // Within bounds
    factor.clamp_to_bounds();
    assert(std::abs(factor.value - 1.0) < 1e-9);
    
    std::cout << "  ✓ CorrectionFactor bounds tests passed" << std::endl;
}

void test_json_serialization() {
    std::cout << "Testing JSON serialization..." << std::endl;
    
    auto state = CalibrationState::create_default_bounded();
    state.calibration_id = "test_calibration_v1";
    state.version = 1;
    state.confidence = ConfidenceLevel::HIGH;
    
    // Set some provenance
    state.provenance.creation_timestamp = "2026-01-11T00:00:00Z";
    state.provenance.git_commit_hash = "abc123";
    state.provenance.data_source = "test_dataset";
    state.provenance.fit_method = "bounded_least_squares";
    state.provenance.total_observations = 10;
    state.provenance.residual_rms = 0.05;
    
    // Serialize
    std::string json = state.to_json();
    
    // Check JSON contains expected fields
    assert(json.find("calibration_id") != std::string::npos);
    assert(json.find("test_calibration_v1") != std::string::npos);
    assert(json.find("correction_factors") != std::string::npos);
    assert(json.find("motor_efficiency_multiplier") != std::string::npos);
    assert(json.find("provenance") != std::string::npos);
    assert(json.find("HIGH") != std::string::npos);
    
    std::cout << "  ✓ JSON serialization tests passed" << std::endl;
}

void test_calibration_fitting() {
    std::cout << "Testing calibration fitting..." << std::endl;
    
    // Create simple synthetic dataset
    CalibrationDataset dataset;
    dataset.dataset_id = "test_dataset";
    dataset.source_description = "synthetic_test_data";
    
    // Add a few measurement points
    for (int i = 0; i < 10; ++i) {
        MeasurementPoint point;
        point.design_params["rotor_diameter_m"] = 1.0 + i * 0.1;
        point.measured_outputs["hover_power_W"] = 1000.0 + i * 50.0;
        dataset.measurements.push_back(point);
    }
    
    assert(dataset.is_valid());
    assert(dataset.size() == 10);
    
    // Create run config
    RunConfig config;
    config.global_seed = 12345;
    config.run_id = "test_fit_run";
    config.git_commit_hash = "test_commit";
    
    // Perform fit
    auto initial_state = CalibrationState::create_default_bounded();
    FitResult result = CalibrationFitter::fit(dataset, config, initial_state);
    
    // Check fit result
    assert(result.calibrated_state.is_valid());
    assert(result.calibrated_state.provenance.total_observations == 10);
    assert(result.calibrated_state.provenance.fit_method == "bounded_least_squares");
    assert(result.residual_rms >= 0.0);
    
    // Check that corrections are within bounds
    for (const auto& factor : result.calibrated_state.correction_factors) {
        assert(factor.is_valid());
        assert(factor.value >= factor.lower_bound);
        assert(factor.value <= factor.upper_bound);
    }
    
    std::cout << "  ✓ Calibration fitting tests passed" << std::endl;
}

void test_calibrated_evaluator() {
    std::cout << "Testing calibrated evaluator..." << std::endl;
    
    // Create calibration state with non-identity corrections
    auto state = CalibrationState::create_default_bounded();
    auto motor_factor = state.get_factor_mut("motor_efficiency_multiplier");
    assert(motor_factor != nullptr);
    motor_factor->value = 1.05;  // 5% improvement
    
    auto drag_factor = state.get_factor_mut("profile_drag_multiplier");
    assert(drag_factor != nullptr);
    drag_factor->value = 0.95;  // 5% reduction
    
    state.confidence = ConfidenceLevel::HIGH;
    
    // Create evaluator
    CalibratedEvaluator evaluator(state);
    assert(evaluator.is_calibrated());
    assert(evaluator.get_confidence() == ConfidenceLevel::HIGH);
    
    // Create base uncertainty config
    UncertaintyConfig base_config;
    
    UncertainScalar motor_param;
    motor_param.name = "motor_efficiency_multiplier";
    motor_param.nominal_value = 1.0;
    motor_param.lower_bound = 0.8;
    motor_param.upper_bound = 1.2;
    base_config.parameters.push_back(motor_param);
    
    UncertainScalar drag_param;
    drag_param.name = "profile_drag_multiplier";
    drag_param.nominal_value = 1.0;
    drag_param.lower_bound = 0.7;
    drag_param.upper_bound = 1.3;
    base_config.parameters.push_back(drag_param);
    
    // Apply calibration
    auto calibrated_config = evaluator.apply_calibration(base_config);
    
    // Check that nominal values were adjusted
    assert(calibrated_config.parameters.size() == 2);
    
    // Motor efficiency should be 1.0 * 1.05 = 1.05
    assert(std::abs(calibrated_config.parameters[0].nominal_value - 1.05) < 1e-6);
    
    // Drag multiplier should be 1.0 * 0.95 = 0.95
    assert(std::abs(calibrated_config.parameters[1].nominal_value - 0.95) < 1e-6);
    
    std::cout << "  ✓ Calibrated evaluator tests passed" << std::endl;
}

void test_determinism() {
    std::cout << "Testing determinism..." << std::endl;
    
    // Create dataset
    CalibrationDataset dataset;
    dataset.dataset_id = "determinism_test";
    dataset.source_description = "test_data";
    
    for (int i = 0; i < 5; ++i) {
        MeasurementPoint point;
        point.design_params["param"] = static_cast<double>(i);
        point.measured_outputs["output"] = static_cast<double>(i * 2);
        dataset.measurements.push_back(point);
    }
    
    // Same seed should produce identical results
    RunConfig config1;
    config1.global_seed = 42;
    config1.run_id = "determinism_run_1";
    config1.git_commit_hash = "abc";
    
    RunConfig config2;
    config2.global_seed = 42;  // Same seed
    config2.run_id = "determinism_run_2";
    config2.git_commit_hash = "abc";
    
    auto initial_state = CalibrationState::create_default_bounded();
    
    auto result1 = CalibrationFitter::fit(dataset, config1, initial_state);
    auto result2 = CalibrationFitter::fit(dataset, config2, initial_state);
    
    // Results should be identical
    assert(result1.calibrated_state.correction_factors.size() == 
           result2.calibrated_state.correction_factors.size());
    
    for (size_t i = 0; i < result1.calibrated_state.correction_factors.size(); ++i) {
        const auto& f1 = result1.calibrated_state.correction_factors[i];
        const auto& f2 = result2.calibrated_state.correction_factors[i];
        
        assert(f1.parameter_name == f2.parameter_name);
        assert(std::abs(f1.value - f2.value) < 1e-9);
    }
    
    std::cout << "  ✓ Determinism tests passed" << std::endl;
}

void test_confidence_assessment() {
    std::cout << "Testing confidence assessment..." << std::endl;
    
    FitResult result;
    result.converged = true;
    result.residual_rms = 0.05;  // Low residual
    result.calibrated_state = CalibrationState::create_default_bounded();
    result.calibrated_state.provenance.total_observations = 20;  // Good sample size
    
    auto confidence = CalibrationFitter::assess_confidence(result);
    assert(confidence == ConfidenceLevel::HIGH);
    
    // Test low confidence due to few observations
    result.calibrated_state.provenance.total_observations = 3;
    confidence = CalibrationFitter::assess_confidence(result);
    assert(confidence == ConfidenceLevel::LOW);
    
    // Test medium confidence due to moderate residual
    result.calibrated_state.provenance.total_observations = 20;
    result.residual_rms = 0.10;
    confidence = CalibrationFitter::assess_confidence(result);
    assert(confidence == ConfidenceLevel::MEDIUM);
    
    std::cout << "  ✓ Confidence assessment tests passed" << std::endl;
}

int main() {
    std::cout << "\n=== Running Calibration Tests ===" << std::endl;
    
    test_calibration_state_creation();
    test_correction_factor_bounds();
    test_json_serialization();
    test_calibration_fitting();
    test_calibrated_evaluator();
    test_determinism();
    test_confidence_assessment();
    
    std::cout << "\n✓ All calibration tests passed!\n" << std::endl;
    return 0;
}
