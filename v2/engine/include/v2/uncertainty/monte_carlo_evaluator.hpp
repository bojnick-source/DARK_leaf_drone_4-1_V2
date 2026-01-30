#pragma once
/*
================================================================================
v2 Uncertainty — Monte Carlo Evaluator
FILE: v2/engine/include/v2/uncertainty/monte_carlo_evaluator.hpp

Purpose:
  - Wrapper around deterministic physics evaluator
  - Perform Monte Carlo uncertainty propagation
  - Generate decision-grade risk reports
  - Preserve determinism via seeded sampling

Architecture:
  - Treats solver as pure function (no internal modifications)
  - All randomness from RunConfig.global_seed
  - Same inputs + same seed ⇒ identical distributions
================================================================================
*/

#include "v2/uncertainty/types.hpp"
#include "v2/core/run_config.hpp"
#include "v2/physics/types.hpp"
#include <memory>
#include <functional>

namespace v2::uncertainty {

/**
 * PerturbedParameters: Sampled parameter values for one MC iteration
 */
struct PerturbedParameters {
    double motor_efficiency_multiplier = 1.0;
    double profile_drag_multiplier = 1.0;
    double induced_loss_factor = 1.0;
    double mass_growth_factor = 1.0;
    double air_density_offset = 0.0;
    double rpm_tracking_error = 0.0;
};

/**
 * DeterministicEvaluationResult: Output from one physics evaluation
 * 
 * This is what the deterministic solver returns.
 * Extend as needed for actual solver integration.
 */
struct DeterministicEvaluationResult {
    double hover_power_W = 0.0;
    double disk_loading_N_per_m2 = 0.0;
    double total_mass_kg = 0.0;
    bool feasible = true;
    std::map<std::string, double> constraint_values;
};

/**
 * MonteCarloEvaluator: Uncertainty quantification wrapper
 * 
 * Usage:
 *   1. Create evaluator with uncertainty config and run config
 *   2. Provide deterministic evaluation function
 *   3. Call evaluate() to get RiskReport
 */
class MonteCarloEvaluator {
public:
    /**
     * Constructor
     * @param uncertainty_config Uncertainty parameter definitions
     * @param run_config Run configuration with seed
     */
    MonteCarloEvaluator(
        const UncertaintyConfig& uncertainty_config,
        const core::RunConfig& run_config);
    
    /**
     * Evaluate with uncertainty propagation
     * 
     * @param nominal_inputs Nominal design parameters
     * @param deterministic_evaluator Function that evaluates design deterministically
     * @return RiskReport with percentiles, violation probabilities, sensitivity
     */
    RiskReport evaluate(
        const physics::RotorGeometry& nominal_inputs,
        std::function<DeterministicEvaluationResult(const physics::RotorGeometry&, const PerturbedParameters&)> deterministic_evaluator);

private:
    UncertaintyConfig uncertainty_config_;
    core::RunConfig run_config_;
    
    /**
     * Draw one sample of perturbed parameters
     */
    PerturbedParameters sample_parameters(uint64_t sample_seed);
    
    /**
     * Compute percentiles from samples
     */
    MonteCarloResult compute_statistics(
        const std::string& output_name,
        double nominal_value,
        const std::vector<double>& samples) const;
    
    /**
     * Compute sensitivity ranking via variance contribution
     */
    std::vector<SensitivityEntry> compute_sensitivity(
        const std::vector<PerturbedParameters>& all_parameters,
        const std::vector<double>& output_samples) const;
};

} // namespace v2::uncertainty
