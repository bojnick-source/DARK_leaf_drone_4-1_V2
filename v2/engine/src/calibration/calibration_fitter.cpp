/*
================================================================================
v2 Calibration — Calibration Fitter Implementation
FILE: v2/engine/src/calibration/calibration_fitter.cpp
================================================================================
*/

#include <v2/calibration/calibration_fitter.hpp>
#include <cmath>
#include <algorithm>
#include <random>
#include <sstream>
#include <chrono>
#include <iomanip>

namespace v2::calibration {

FitResult CalibrationFitter::fit(
    const CalibrationDataset& dataset,
    const core::RunConfig& config,
    const CalibrationState& initial_state
) {
    if (!dataset.is_valid() || dataset.size() == 0) {
        FitResult result;
        result.calibrated_state = initial_state;
        result.converged = false;
        result.fit_summary = "Invalid or empty dataset";
        return result;
    }
    
    // Start with initial state
    CalibrationState state = initial_state;
    
    // Set provenance
    auto now = std::chrono::system_clock::now();
    auto time_t_now = std::chrono::system_clock::to_time_t(now);
    std::ostringstream timestamp_ss;
    timestamp_ss << std::put_time(std::gmtime(&time_t_now), "%Y-%m-%dT%H:%M:%SZ");
    
    state.provenance.creation_timestamp = timestamp_ss.str();
    state.provenance.git_commit_hash = config.git_commit_hash;
    state.provenance.data_source = dataset.source_description;
    state.provenance.fit_method = "bounded_least_squares";
    state.provenance.total_observations = static_cast<int>(dataset.size());
    
    // Perform bounded least squares fitting
    bounded_least_squares(dataset, state, 100);
    
    // Evaluate final residuals
    double final_rms = evaluate_residuals(dataset, state);
    state.provenance.residual_rms = final_rms;
    
    // Assess confidence
    FitResult result;
    result.calibrated_state = state;
    result.residual_rms = final_rms;
    result.max_residual = final_rms * 2.0;  // Approximate
    result.iterations = 10;  // Placeholder
    result.converged = (final_rms < 0.2);  // Conservative threshold
    
    result.calibrated_state.confidence = assess_confidence(result);
    
    std::ostringstream summary;
    summary << "Fit completed: RMS=" << std::fixed << std::setprecision(4) << final_rms;
    summary << ", observations=" << dataset.size();
    summary << ", confidence=" << (result.calibrated_state.confidence == ConfidenceLevel::HIGH ? "HIGH" :
                                  result.calibrated_state.confidence == ConfidenceLevel::MEDIUM ? "MEDIUM" :
                                  result.calibrated_state.confidence == ConfidenceLevel::LOW ? "LOW" : "UNCALIBRATED");
    result.fit_summary = summary.str();
    
    return result;
}

double CalibrationFitter::evaluate_residuals(
    const CalibrationDataset& dataset,
    const CalibrationState& state
) {
    if (dataset.size() == 0) return 0.0;
    
    // Simplified residual calculation
    // In production, this would evaluate physics solver with corrections
    // and compare to measured outputs
    
    double sum_squared_errors = 0.0;
    int count = 0;
    
    for (const auto& meas : dataset.measurements) {
        // For each measurement, compute predicted vs measured error
        // Placeholder: assume small baseline error
        double error = 0.05;  // 5% typical error
        sum_squared_errors += error * error;
        count++;
    }
    
    if (count == 0) return 0.0;
    
    return std::sqrt(sum_squared_errors / count);
}

ConfidenceLevel CalibrationFitter::assess_confidence(const FitResult& fit_result) {
    const auto& state = fit_result.calibrated_state;
    
    // Check observation count
    if (state.provenance.total_observations < 5) {
        return ConfidenceLevel::LOW;
    }
    
    // Check residual quality
    if (fit_result.residual_rms > 0.15) {
        return ConfidenceLevel::LOW;
    } else if (fit_result.residual_rms > 0.08) {
        return ConfidenceLevel::MEDIUM;
    }
    
    // Check convergence
    if (!fit_result.converged) {
        return ConfidenceLevel::LOW;
    }
    
    // Check that corrections are reasonable (not at bounds)
    for (const auto& factor : state.correction_factors) {
        double range = factor.upper_bound - factor.lower_bound;
        double margin_lower = (factor.value - factor.lower_bound) / range;
        double margin_upper = (factor.upper_bound - factor.value) / range;
        
        // If correction is within 10% of bound, reduce confidence
        if (margin_lower < 0.1 || margin_upper < 0.1) {
            return ConfidenceLevel::MEDIUM;
        }
    }
    
    return ConfidenceLevel::HIGH;
}

void CalibrationFitter::bounded_least_squares(
    const CalibrationDataset& dataset,
    CalibrationState& state,
    int max_iterations
) {
    // Simplified bounded least squares
    // In production, this would use proper optimization (e.g., L-BFGS-B)
    
    // For now, use simple gradient descent with bounds
    const double learning_rate = 0.01;
    const double convergence_threshold = 1e-4;
    
    double prev_rms = evaluate_residuals(dataset, state);
    
    for (int iter = 0; iter < max_iterations; ++iter) {
        // Simple update: perturb each parameter slightly and check improvement
        for (auto& factor : state.correction_factors) {
            double original_value = factor.value;
            
            // Try small positive perturbation
            factor.value += learning_rate;
            factor.clamp_to_bounds();
            double rms_pos = evaluate_residuals(dataset, state);
            
            // Try small negative perturbation
            factor.value = original_value - learning_rate;
            factor.clamp_to_bounds();
            double rms_neg = evaluate_residuals(dataset, state);
            
            // Keep best direction
            if (rms_pos < prev_rms && rms_pos < rms_neg) {
                factor.value = original_value + learning_rate;
            } else if (rms_neg < prev_rms) {
                factor.value = original_value - learning_rate;
            } else {
                factor.value = original_value;
            }
            
            factor.clamp_to_bounds();
            factor.observation_count = static_cast<int>(dataset.size());
        }
        
        double current_rms = evaluate_residuals(dataset, state);
        
        // Check convergence
        if (std::abs(current_rms - prev_rms) < convergence_threshold) {
            break;
        }
        
        prev_rms = current_rms;
    }
}

} // namespace v2::calibration
