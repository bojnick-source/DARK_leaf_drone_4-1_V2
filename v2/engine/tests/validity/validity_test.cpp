/*
================================================================================
v2 Validity — OOD Detection Tests
FILE: v2/engine/tests/validity/validity_test.cpp

Tests for EXECUTION_0.6: OOD Detection + Conservative Validity Gating
================================================================================
*/

#include "v2/validity/conservative_ood_detector.hpp"
#include "v2/uncertainty/types.hpp"
#include "v2/calibration/types.hpp"
#include <cassert>
#include <iostream>
#include <cmath>

using namespace v2::validity;
using namespace v2::uncertainty;
using namespace v2::calibration;

namespace {
    constexpr double EPSILON = 1e-9;
    
    bool approx_equal(double a, double b, double tol = 1e-6) {
        return std::abs(a - b) < tol;
    }
    
    // Helper to create mock RiskReport
    RiskReport create_mock_risk_report(
        uint64_t seed,
        uint32_t sample_count,
        double nominal, double mean, double stddev,
        double p5, double p50, double p95
    ) {
        RiskReport report;
        report.run_id = "test_run_001";
        report.seed = seed;
        report.sample_count = sample_count;
        report.timestamp = "2026-01-11T00:00:00Z";
        
        MonteCarloResult result;
        result.output_name = "hover_power_W";
        result.nominal_value = nominal;
        result.mean_value = mean;
        result.stddev_value = stddev;
        result.p5_value = p5;
        result.p50_value = p50;
        result.p95_value = p95;
        
        report.output_results.push_back(result);
        
        return report;
    }
    
    // Helper to create uncalibrated state
    CalibrationState create_uncalibrated_state() {
        CalibrationState state;
        state.confidence = ConfidenceLevel::UNCALIBRATED;
        state.provenance.data_source = "none";
        state.provenance.creation_timestamp = "never";
        return state;
    }
    
    // Helper to create calibrated state
    CalibrationState create_calibrated_state() {
        CalibrationState state;
        state.confidence = ConfidenceLevel::MEDIUM;
        state.provenance.data_source = "test_data_001";
        state.provenance.creation_timestamp = "2026-01-10T00:00:00Z";
        
        // Add some correction factors
        CorrectionFactor factor;
        factor.parameter_name = "motor_efficiency_multiplier";
        factor.value = 1.05;
        factor.lower_bound = 0.85;
        factor.upper_bound = 1.15;
        state.correction_factors.push_back(factor);
        
        return state;
    }
}

void test_valid_state() {
    std::cout << "TEST: Valid state (no flags)" << std::endl;
    
    // Create well-behaved risk report
    // Nominal=1000, tight distribution around 1000
    auto report = create_mock_risk_report(
        12345, 200,
        1000.0, 1000.0, 50.0,  // nominal, mean, stddev
        900.0, 1000.0, 1100.0   // p5, p50, p95
    );
    
    auto calib_state = create_uncalibrated_state();
    auto thresholds = OODThresholds::create_default();
    
    ConservativeOODDetector detector;
    auto assessment = detector.assess_validity(report, calib_state, thresholds);
    
    // Should be VALID
    assert(assessment.state == ValidityState::VALID);
    assert(assessment.num_metrics_flagged == 0);
    assert(assessment.confidence_score > 0.9);
    
    std::cout << "  State: VALID" << std::endl;
    std::cout << "  Confidence: " << assessment.confidence_score << std::endl;
    std::cout << "  Rationale: " << assessment.state_rationale << std::endl;
    std::cout << "  PASSED" << std::endl << std::endl;
}

void test_low_confidence_state() {
    std::cout << "TEST: Low confidence state (high CV)" << std::endl;
    
    // Create report with high coefficient of variation
    // CV = 250 / 1000 = 0.25, below default threshold of 0.5
    // But increase to trigger: CV = 600 / 1000 = 0.6 > 0.5
    auto report = create_mock_risk_report(
        12345, 200,
        1000.0, 1000.0, 600.0,  // nominal, mean, large stddev
        400.0, 1000.0, 1600.0    // p5, p50, p95
    );
    
    auto calib_state = create_uncalibrated_state();
    auto thresholds = OODThresholds::create_default();
    
    ConservativeOODDetector detector;
    auto assessment = detector.assess_validity(report, calib_state, thresholds);
    
    // Should be LOW_CONFIDENCE (1 flag: high CV)
    assert(assessment.state == ValidityState::LOW_CONFIDENCE);
    assert(assessment.num_metrics_flagged >= 1);
    assert(assessment.confidence_score < 1.0);
    
    std::cout << "  State: LOW_CONFIDENCE" << std::endl;
    std::cout << "  Flags: " << assessment.num_metrics_flagged << std::endl;
    std::cout << "  Confidence: " << assessment.confidence_score << std::endl;
    std::cout << "  PASSED" << std::endl << std::endl;
}

void test_ood_state() {
    std::cout << "TEST: Out-of-distribution state (multiple flags)" << std::endl;
    
    // Create report with extreme spread and high CV
    // Spread ratio = (3000 - 100) / 1000 = 2.9 > 2.0
    // CV = 800 / 1000 = 0.8 > 0.5
    auto report = create_mock_risk_report(
        12345, 200,
        1000.0, 1000.0, 800.0,  // nominal, mean, very large stddev
        100.0, 1000.0, 3000.0    // p5, p50, p95 - extreme spread
    );
    
    auto calib_state = create_uncalibrated_state();
    auto thresholds = OODThresholds::create_default();
    
    ConservativeOODDetector detector;
    auto assessment = detector.assess_validity(report, calib_state, thresholds);
    
    // Should be OUT_OF_DISTRIBUTION (2+ flags)
    assert(assessment.state == ValidityState::OUT_OF_DISTRIBUTION);
    assert(assessment.num_metrics_flagged >= 2);
    assert(assessment.confidence_score < 0.7);
    
    std::cout << "  State: OUT_OF_DISTRIBUTION" << std::endl;
    std::cout << "  Flags: " << assessment.num_metrics_flagged << std::endl;
    std::cout << "  Confidence: " << assessment.confidence_score << std::endl;
    std::cout << "  PASSED" << std::endl << std::endl;
}

void test_insufficient_samples() {
    std::cout << "TEST: Insufficient samples" << std::endl;
    
    // Create report with too few samples
    auto report = create_mock_risk_report(
        12345, 30,  // Only 30 samples, below min of 50
        1000.0, 1000.0, 50.0,
        900.0, 1000.0, 1100.0
    );
    
    auto calib_state = create_uncalibrated_state();
    auto thresholds = OODThresholds::create_default();
    
    ConservativeOODDetector detector;
    auto assessment = detector.assess_validity(report, calib_state, thresholds);
    
    // Should be LOW_CONFIDENCE due to insufficient samples
    assert(assessment.state == ValidityState::LOW_CONFIDENCE);
    assert(assessment.num_metrics_flagged >= 1);
    
    // Check that sample_count_adequacy is flagged
    bool sample_flag_found = false;
    for (const auto& metric : assessment.ood_metrics) {
        if (metric.metric_name == "sample_count_adequacy" && metric.flagged) {
            sample_flag_found = true;
            break;
        }
    }
    assert(sample_flag_found);
    
    std::cout << "  State: LOW_CONFIDENCE (insufficient samples)" << std::endl;
    std::cout << "  Sample count: " << report.sample_count << std::endl;
    std::cout << "  PASSED" << std::endl << std::endl;
}

void test_calibration_drift() {
    std::cout << "TEST: Calibration drift detection" << std::endl;
    
    // Create report with significant drift from nominal
    // Drift = |1400 - 1000| / 1000 = 0.4 > 0.3
    auto report = create_mock_risk_report(
        12345, 200,
        1000.0, 1400.0, 80.0,  // nominal=1000, mean=1400 (40% drift!)
        1250.0, 1400.0, 1550.0
    );
    
    auto calib_state = create_calibrated_state();  // Use calibrated state
    auto thresholds = OODThresholds::create_default();
    
    ConservativeOODDetector detector;
    auto assessment = detector.assess_validity(report, calib_state, thresholds);
    
    // Should flag calibration drift
    bool drift_flag_found = false;
    for (const auto& metric : assessment.ood_metrics) {
        if (metric.metric_name.find("calibration_drift") != std::string::npos && metric.flagged) {
            drift_flag_found = true;
            break;
        }
    }
    assert(drift_flag_found);
    
    std::cout << "  Calibration drift flag: " << (drift_flag_found ? "YES" : "NO") << std::endl;
    std::cout << "  PASSED" << std::endl << std::endl;
}

void test_determinism() {
    std::cout << "TEST: Deterministic validity assessment" << std::endl;
    
    // Same inputs should produce identical results
    auto report = create_mock_risk_report(
        42, 200,
        1000.0, 1000.0, 100.0,
        800.0, 1000.0, 1200.0
    );
    
    auto calib_state = create_uncalibrated_state();
    auto thresholds = OODThresholds::create_default();
    
    ConservativeOODDetector detector;
    auto assessment1 = detector.assess_validity(report, calib_state, thresholds);
    auto assessment2 = detector.assess_validity(report, calib_state, thresholds);
    
    // Results should be identical
    assert(assessment1.state == assessment2.state);
    assert(assessment1.num_metrics_flagged == assessment2.num_metrics_flagged);
    assert(approx_equal(assessment1.confidence_score, assessment2.confidence_score));
    
    std::cout << "  Same inputs => same outputs: VERIFIED" << std::endl;
    std::cout << "  PASSED" << std::endl << std::endl;
}

void test_json_serialization() {
    std::cout << "TEST: JSON serialization" << std::endl;
    
    auto report = create_mock_risk_report(
        12345, 200,
        1000.0, 1000.0, 50.0,
        900.0, 1000.0, 1100.0
    );
    
    auto calib_state = create_uncalibrated_state();
    
    ConservativeOODDetector detector;
    auto assessment = detector.assess_validity(report, calib_state);
    
    // Serialize to JSON
    std::string json = assessment.to_json();
    
    // Basic validation
    assert(json.find("\"run_id\"") != std::string::npos);
    assert(json.find("\"state\"") != std::string::npos);
    assert(json.find("\"ood_metrics\"") != std::string::npos);
    assert(json.find("\"recommendations\"") != std::string::npos);
    
    std::cout << "  JSON serialization: OK" << std::endl;
    std::cout << "  JSON length: " << json.length() << " bytes" << std::endl;
    std::cout << "  PASSED" << std::endl << std::endl;
}

void test_recommendations() {
    std::cout << "TEST: Recommendation generation" << std::endl;
    
    // Test OOD state recommendations
    auto report = create_mock_risk_report(
        12345, 200,
        1000.0, 1000.0, 900.0,  // Very high stddev
        50.0, 1000.0, 3500.0    // Extreme spread
    );
    
    auto calib_state = create_uncalibrated_state();
    
    ConservativeOODDetector detector;
    auto assessment = detector.assess_validity(report, calib_state);
    
    // Should have recommendations
    assert(!assessment.recommendations.empty());
    
    // OOD state should have strong warnings
    if (assessment.state == ValidityState::OUT_OF_DISTRIBUTION) {
        bool found_warning = false;
        for (const auto& rec : assessment.recommendations) {
            if (rec.find("unreliable") != std::string::npos || 
                rec.find("DO NOT use") != std::string::npos) {
                found_warning = true;
                break;
            }
        }
        assert(found_warning);
    }
    
    std::cout << "  Recommendations count: " << assessment.recommendations.size() << std::endl;
    std::cout << "  PASSED" << std::endl << std::endl;
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "v2 Validity — OOD Detection Tests" << std::endl;
    std::cout << "EXECUTION_0.6" << std::endl;
    std::cout << "========================================" << std::endl << std::endl;
    
    try {
        test_valid_state();
        test_low_confidence_state();
        test_ood_state();
        test_insufficient_samples();
        test_calibration_drift();
        test_determinism();
        test_json_serialization();
        test_recommendations();
        
        std::cout << "========================================" << std::endl;
        std::cout << "ALL TESTS PASSED" << std::endl;
        std::cout << "========================================" << std::endl;
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "TEST FAILED: " << e.what() << std::endl;
        return 1;
    }
}
