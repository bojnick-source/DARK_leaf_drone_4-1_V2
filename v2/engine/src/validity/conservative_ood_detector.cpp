/*
================================================================================
v2 Validity — Conservative OOD Detector Implementation
FILE: v2/engine/src/validity/conservative_ood_detector.cpp

This implements EXECUTION_0.6: OOD Detection + Conservative Validity Gating
================================================================================
*/

#include "v2/validity/conservative_ood_detector.hpp"
#include <algorithm>
#include <cmath>
#include <sstream>
#include <iomanip>
#include <ctime>

namespace v2::validity {

namespace {
    constexpr double EPSILON = 1e-9;
    
    std::string get_timestamp() {
        auto now = std::time(nullptr);
        char buffer[64];
        std::strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", std::gmtime(&now));
        return std::string(buffer);
    }
}

ValidityAssessment ConservativeOODDetector::assess_validity(
    const uncertainty::RiskReport& risk_report,
    const calibration::CalibrationState& calibration_state,
    const OODThresholds& thresholds
) const {
    ValidityAssessment assessment;
    
    // Traceability
    assessment.run_id = risk_report.run_id;
    assessment.seed = risk_report.seed;
    assessment.timestamp = get_timestamp();
    assessment.thresholds = thresholds;
    
    // Evaluate all OOD metrics
    std::vector<OODMetric> all_metrics;
    
    // 1. Percentile spread ratios
    auto spread_metrics = evaluate_spread_ratios(risk_report, thresholds);
    all_metrics.insert(all_metrics.end(), spread_metrics.begin(), spread_metrics.end());
    
    // 2. Coefficient of variation
    auto cv_metrics = evaluate_coeff_variation(risk_report, thresholds);
    all_metrics.insert(all_metrics.end(), cv_metrics.begin(), cv_metrics.end());
    
    // 3. Calibration drift (if calibrated)
    auto drift_metrics = evaluate_calibration_drift(risk_report, calibration_state, thresholds);
    all_metrics.insert(all_metrics.end(), drift_metrics.begin(), drift_metrics.end());
    
    // 4. Sample count adequacy
    auto sample_metric = evaluate_sample_adequacy(risk_report, thresholds);
    all_metrics.push_back(sample_metric);
    
    assessment.ood_metrics = all_metrics;
    assessment.num_metrics_evaluated = static_cast<int>(all_metrics.size());
    
    // Count flagged metrics
    assessment.num_metrics_flagged = static_cast<int>(
        std::count_if(all_metrics.begin(), all_metrics.end(),
                     [](const OODMetric& m) { return m.flagged; })
    );
    
    // Classify validity state
    assessment.state = classify_state(all_metrics, risk_report.sample_count, thresholds);
    
    // Compute confidence score (1.0 = perfect, 0.0 = completely unreliable)
    double flag_penalty = static_cast<double>(assessment.num_metrics_flagged) / 
                         std::max(1.0, static_cast<double>(assessment.num_metrics_evaluated));
    assessment.confidence_score = std::max(0.0, 1.0 - flag_penalty);
    
    // Generate rationale
    std::ostringstream rationale;
    rationale << "Evaluated " << assessment.num_metrics_evaluated << " OOD metrics. ";
    rationale << assessment.num_metrics_flagged << " flags raised. ";
    
    if (assessment.state == ValidityState::VALID) {
        rationale << "All metrics in acceptable range.";
    } else if (assessment.state == ValidityState::LOW_CONFIDENCE) {
        rationale << "Minor concerns detected - use results cautiously.";
    } else {
        rationale << "Multiple red flags - outputs unreliable.";
    }
    
    assessment.state_rationale = rationale.str();
    
    // Generate recommendations
    std::vector<OODMetric> flagged_metrics;
    std::copy_if(all_metrics.begin(), all_metrics.end(), 
                std::back_inserter(flagged_metrics),
                [](const OODMetric& m) { return m.flagged; });
    
    assessment.recommendations = generate_recommendations(assessment.state, flagged_metrics);
    
    return assessment;
}

std::vector<OODMetric> ConservativeOODDetector::evaluate_spread_ratios(
    const uncertainty::RiskReport& risk_report,
    const OODThresholds& thresholds
) const {
    std::vector<OODMetric> metrics;
    
    for (const auto& result : risk_report.output_results) {
        OODMetric metric;
        metric.metric_name = "spread_ratio_" + result.output_name;
        metric.threshold = thresholds.max_spread_ratio;
        
        // Compute spread ratio: (P95 - P5) / max(|P50|, eps)
        double spread = result.p95_value - result.p5_value;
        double reference = std::max(std::abs(result.p50_value), EPSILON);
        metric.computed_value = spread / reference;
        
        metric.flagged = (metric.computed_value > metric.threshold);
        
        if (metric.flagged) {
            metric.interpretation = "Excessive spread - distribution may be unreliable";
        } else {
            metric.interpretation = "Spread within acceptable range";
        }
        
        metrics.push_back(metric);
    }
    
    return metrics;
}

std::vector<OODMetric> ConservativeOODDetector::evaluate_coeff_variation(
    const uncertainty::RiskReport& risk_report,
    const OODThresholds& thresholds
) const {
    std::vector<OODMetric> metrics;
    
    for (const auto& result : risk_report.output_results) {
        OODMetric metric;
        metric.metric_name = "coeff_variation_" + result.output_name;
        metric.threshold = thresholds.max_coeff_variation;
        
        // Compute CV: stddev / |mean|
        double mean_abs = std::max(std::abs(result.mean_value), EPSILON);
        metric.computed_value = result.stddev_value / mean_abs;
        
        metric.flagged = (metric.computed_value > metric.threshold);
        
        if (metric.flagged) {
            metric.interpretation = "High coefficient of variation - low confidence";
        } else {
            metric.interpretation = "Coefficient of variation acceptable";
        }
        
        metrics.push_back(metric);
    }
    
    return metrics;
}

std::vector<OODMetric> ConservativeOODDetector::evaluate_calibration_drift(
    const uncertainty::RiskReport& risk_report,
    const calibration::CalibrationState& calibration_state,
    const OODThresholds& thresholds
) const {
    std::vector<OODMetric> metrics;
    
    // Only check drift if calibrated
    if (calibration_state.confidence == calibration::ConfidenceLevel::UNCALIBRATED) {
        return metrics;  // No drift check for uncalibrated state
    }
    
    for (const auto& result : risk_report.output_results) {
        OODMetric metric;
        metric.metric_name = "calibration_drift_" + result.output_name;
        metric.threshold = thresholds.max_calibration_drift;
        
        // Compute drift: |mean - nominal| / |nominal|
        double nominal_abs = std::max(std::abs(result.nominal_value), EPSILON);
        metric.computed_value = std::abs(result.mean_value - result.nominal_value) / nominal_abs;
        
        metric.flagged = (metric.computed_value > metric.threshold);
        
        if (metric.flagged) {
            metric.interpretation = "Significant drift from nominal - calibration may be out of regime";
        } else {
            metric.interpretation = "Calibration drift acceptable";
        }
        
        metrics.push_back(metric);
    }
    
    return metrics;
}

OODMetric ConservativeOODDetector::evaluate_sample_adequacy(
    const uncertainty::RiskReport& risk_report,
    const OODThresholds& thresholds
) const {
    OODMetric metric;
    metric.metric_name = "sample_count_adequacy";
    metric.threshold = static_cast<double>(thresholds.min_sample_count);
    metric.computed_value = static_cast<double>(risk_report.sample_count);
    
    metric.flagged = (risk_report.sample_count < thresholds.min_sample_count);
    
    if (metric.flagged) {
        metric.interpretation = "Insufficient samples for reliable statistics";
    } else {
        metric.interpretation = "Sample count adequate";
    }
    
    return metric;
}

ValidityState ConservativeOODDetector::classify_state(
    const std::vector<OODMetric>& all_metrics,
    uint32_t sample_count,
    const OODThresholds& thresholds
) const {
    // Count flagged metrics
    int num_flagged = static_cast<int>(
        std::count_if(all_metrics.begin(), all_metrics.end(),
                     [](const OODMetric& m) { return m.flagged; })
    );
    
    // Classification logic:
    // - OUT_OF_DISTRIBUTION: 2+ flags OR critical threshold massively exceeded
    // - LOW_CONFIDENCE: 1 flag OR marginal sample count
    // - VALID: No flags, adequate samples
    
    if (num_flagged >= 2) {
        return ValidityState::OUT_OF_DISTRIBUTION;
    }
    
    // Check for critical violations (even if only one)
    for (const auto& metric : all_metrics) {
        if (metric.flagged) {
            // Critical spread ratio: > 3x threshold
            if (metric.metric_name.find("spread_ratio") != std::string::npos &&
                metric.computed_value > 3.0 * metric.threshold) {
                return ValidityState::OUT_OF_DISTRIBUTION;
            }
            
            // Critical CV: > 2x threshold
            if (metric.metric_name.find("coeff_variation") != std::string::npos &&
                metric.computed_value > 2.0 * metric.threshold) {
                return ValidityState::OUT_OF_DISTRIBUTION;
            }
        }
    }
    
    if (num_flagged == 1) {
        return ValidityState::LOW_CONFIDENCE;
    }
    
    // Marginal sample count (even if no flags)
    if (sample_count < thresholds.min_sample_count * 1.2) {
        return ValidityState::LOW_CONFIDENCE;
    }
    
    return ValidityState::VALID;
}

std::vector<std::string> ConservativeOODDetector::generate_recommendations(
    ValidityState state,
    const std::vector<OODMetric>& flagged_metrics
) const {
    std::vector<std::string> recommendations;
    
    if (state == ValidityState::VALID) {
        recommendations.push_back("Outputs are trustworthy - proceed with confidence");
        return recommendations;
    }
    
    if (state == ValidityState::LOW_CONFIDENCE) {
        recommendations.push_back("Use results with caution - confidence is marginal");
        recommendations.push_back("Consider increasing Monte Carlo sample count");
        
        // Specific recommendations based on flagged metrics
        for (const auto& metric : flagged_metrics) {
            if (metric.metric_name.find("sample_count") != std::string::npos) {
                recommendations.push_back("Increase sample count to at least 100 for better confidence");
            }
            if (metric.metric_name.find("coeff_variation") != std::string::npos) {
                recommendations.push_back("High uncertainty detected - consider tightening input distributions");
            }
        }
        
        return recommendations;
    }
    
    // OUT_OF_DISTRIBUTION
    recommendations.push_back("Outputs are unreliable - DO NOT use for safety-critical decisions");
    recommendations.push_back("Likely outside calibrated regime or training envelope");
    recommendations.push_back("Consider one of: (1) Re-calibrate with data from this region");
    recommendations.push_back("                 (2) Collect more validation data");
    recommendations.push_back("                 (3) Mark as DEFERRED until confidence improves");
    
    // Specific recommendations
    for (const auto& metric : flagged_metrics) {
        if (metric.metric_name.find("spread_ratio") != std::string::npos) {
            recommendations.push_back("Excessive spread detected - check for numerical instabilities");
        }
        if (metric.metric_name.find("calibration_drift") != std::string::npos) {
            recommendations.push_back("Calibration drift significant - likely extrapolating beyond regime");
        }
    }
    
    return recommendations;
}

} // namespace v2::validity
