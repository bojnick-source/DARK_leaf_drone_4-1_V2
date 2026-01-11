/*
================================================================================
v2 Uncertainty — Monte Carlo Evaluator Implementation
FILE: v2/engine/src/uncertainty/monte_carlo_evaluator.cpp
================================================================================
*/

#include "v2/uncertainty/monte_carlo_evaluator.hpp"
#include <random>
#include <algorithm>
#include <numeric>
#include <cmath>
#include <sstream>
#include <iomanip>
#include <ctime>

namespace v2::uncertainty {

MonteCarloEvaluator::MonteCarloEvaluator(
    const UncertaintyConfig& uncertainty_config,
    const core::RunConfig& run_config)
    : uncertainty_config_(uncertainty_config)
    , run_config_(run_config) {
}

PerturbedParameters MonteCarloEvaluator::sample_parameters(uint64_t sample_seed) {
    std::mt19937_64 rng(sample_seed);
    
    PerturbedParameters perturbed;
    
    for (const auto& param : uncertainty_config_.parameters) {
        double value = param.nominal_value;
        
        if (param.dist_type == DistributionType::Normal) {
            std::normal_distribution<double> dist(param.nominal_value, param.stddev);
            value = dist(rng);
            // Clamp to bounds
            value = std::max(param.lower_bound, std::min(param.upper_bound, value));
        } else if (param.dist_type == DistributionType::Uniform) {
            std::uniform_real_distribution<double> dist(param.lower_bound, param.upper_bound);
            value = dist(rng);
        }
        
        // Map to PerturbedParameters fields
        if (param.name == "motor_efficiency_multiplier") {
            perturbed.motor_efficiency_multiplier = value;
        } else if (param.name == "profile_drag_multiplier") {
            perturbed.profile_drag_multiplier = value;
        } else if (param.name == "induced_loss_factor") {
            perturbed.induced_loss_factor = value;
        } else if (param.name == "mass_growth_factor") {
            perturbed.mass_growth_factor = value;
        } else if (param.name == "air_density_offset") {
            perturbed.air_density_offset = value;
        } else if (param.name == "rpm_tracking_error") {
            perturbed.rpm_tracking_error = value;
        }
    }
    
    return perturbed;
}

MonteCarloResult MonteCarloEvaluator::compute_statistics(
    const std::string& output_name,
    double nominal_value,
    const std::vector<double>& samples) const {
    
    MonteCarloResult result;
    result.output_name = output_name;
    result.nominal_value = nominal_value;
    result.samples = samples;
    
    if (samples.empty()) {
        return result;
    }
    
    // Compute mean
    double sum = std::accumulate(samples.begin(), samples.end(), 0.0);
    result.mean_value = sum / samples.size();
    
    // Compute standard deviation
    double sq_sum = 0.0;
    for (double val : samples) {
        double diff = val - result.mean_value;
        sq_sum += diff * diff;
    }
    result.stddev_value = std::sqrt(sq_sum / samples.size());
    
    // Compute percentiles
    std::vector<double> sorted_samples = samples;
    std::sort(sorted_samples.begin(), sorted_samples.end());
    
    auto percentile = [&sorted_samples](double p) -> double {
        size_t idx = static_cast<size_t>(p * (sorted_samples.size() - 1));
        return sorted_samples[idx];
    };
    
    result.p5_value = percentile(0.05);
    result.p50_value = percentile(0.50);
    result.p90_value = percentile(0.90);
    result.p95_value = percentile(0.95);
    
    return result;
}

std::vector<SensitivityEntry> MonteCarloEvaluator::compute_sensitivity(
    const std::vector<PerturbedParameters>& all_parameters,
    const std::vector<double>& output_samples) const {
    
    std::vector<SensitivityEntry> sensitivities;
    
    if (all_parameters.empty() || output_samples.empty()) {
        return sensitivities;
    }
    
    // Compute output mean and variance
    double output_mean = std::accumulate(output_samples.begin(), output_samples.end(), 0.0) / output_samples.size();
    double output_var = 0.0;
    for (double val : output_samples) {
        double diff = val - output_mean;
        output_var += diff * diff;
    }
    output_var /= output_samples.size();
    
    if (output_var < 1e-12) {
        return sensitivities;  // No variance to explain
    }
    
    // For each uncertain parameter, compute correlation-based contribution
    for (const auto& param : uncertainty_config_.parameters) {
        // Extract parameter values from all samples
        std::vector<double> param_values;
        for (const auto& perturbed : all_parameters) {
            double val = 1.0;  // Default
            if (param.name == "motor_efficiency_multiplier") {
                val = perturbed.motor_efficiency_multiplier;
            } else if (param.name == "profile_drag_multiplier") {
                val = perturbed.profile_drag_multiplier;
            } else if (param.name == "induced_loss_factor") {
                val = perturbed.induced_loss_factor;
            } else if (param.name == "mass_growth_factor") {
                val = perturbed.mass_growth_factor;
            } else if (param.name == "air_density_offset") {
                val = perturbed.air_density_offset;
            } else if (param.name == "rpm_tracking_error") {
                val = perturbed.rpm_tracking_error;
            }
            param_values.push_back(val);
        }
        
        // Compute correlation coefficient
        double param_mean = std::accumulate(param_values.begin(), param_values.end(), 0.0) / param_values.size();
        double covariance = 0.0;
        double param_var = 0.0;
        
        for (size_t i = 0; i < param_values.size(); ++i) {
            double param_diff = param_values[i] - param_mean;
            double output_diff = output_samples[i] - output_mean;
            covariance += param_diff * output_diff;
            param_var += param_diff * param_diff;
        }
        
        covariance /= param_values.size();
        param_var /= param_values.size();
        
        double correlation = 0.0;
        if (param_var > 1e-12) {
            correlation = covariance / std::sqrt(param_var * output_var);
        }
        
        SensitivityEntry entry;
        entry.parameter_name = param.name;
        entry.contribution = std::abs(correlation);  // Absolute correlation as importance
        sensitivities.push_back(entry);
    }
    
    // Sort by contribution (descending) and assign ranks
    std::sort(sensitivities.begin(), sensitivities.end(),
              [](const SensitivityEntry& a, const SensitivityEntry& b) {
                  return a.contribution > b.contribution;
              });
    
    for (size_t i = 0; i < sensitivities.size(); ++i) {
        sensitivities[i].rank = static_cast<int>(i + 1);
    }
    
    return sensitivities;
}

RiskReport MonteCarloEvaluator::evaluate(
    const physics::RotorGeometry& nominal_inputs,
    std::function<DeterministicEvaluationResult(const physics::RotorGeometry&, const PerturbedParameters&)> deterministic_evaluator) {
    
    RiskReport report;
    report.run_id = run_config_.run_id;
    report.seed = run_config_.global_seed;
    report.sample_count = uncertainty_config_.sample_count;
    report.distributions_used = uncertainty_config_.parameters;
    
    // Generate timestamp
    std::time_t now = std::time(nullptr);
    char timestamp_buf[100];
    std::strftime(timestamp_buf, sizeof(timestamp_buf), "%Y-%m-%d %H:%M:%S", std::localtime(&now));
    report.timestamp = timestamp_buf;
    
    // Evaluate nominal case (deterministic)
    PerturbedParameters nominal_perturbed;  // All at nominal values
    auto nominal_result = deterministic_evaluator(nominal_inputs, nominal_perturbed);
    
    // Monte Carlo sampling
    std::vector<DeterministicEvaluationResult> all_results;
    std::vector<PerturbedParameters> all_perturbed_params;
    
    for (uint32_t i = 0; i < uncertainty_config_.sample_count; ++i) {
        // Generate deterministic seed for this sample
        uint64_t sample_seed = run_config_.global_seed + i + 1;
        
        // Sample perturbed parameters
        PerturbedParameters perturbed = sample_parameters(sample_seed);
        all_perturbed_params.push_back(perturbed);
        
        // Evaluate with perturbed parameters
        auto result = deterministic_evaluator(nominal_inputs, perturbed);
        all_results.push_back(result);
    }
    
    // Extract samples for each output
    std::vector<double> hover_power_samples;
    std::vector<double> disk_loading_samples;
    std::vector<double> mass_samples;
    
    for (const auto& result : all_results) {
        hover_power_samples.push_back(result.hover_power_W);
        disk_loading_samples.push_back(result.disk_loading_N_per_m2);
        mass_samples.push_back(result.total_mass_kg);
    }
    
    // Compute statistics for outputs
    report.output_results.push_back(
        compute_statistics("hover_power_W", nominal_result.hover_power_W, hover_power_samples));
    report.output_results.push_back(
        compute_statistics("disk_loading_N_per_m2", nominal_result.disk_loading_N_per_m2, disk_loading_samples));
    report.output_results.push_back(
        compute_statistics("total_mass_kg", nominal_result.total_mass_kg, mass_samples));
    
    // Compute sensitivity ranking (using hover power as primary output)
    report.sensitivity_ranking = compute_sensitivity(all_perturbed_params, hover_power_samples);
    
    return report;
}

} // namespace v2::uncertainty
