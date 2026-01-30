/*
================================================================================
v2 Sampling — Uncertainty-Driven Policy Implementation
FILE: v2/engine/src/sampling/uncertainty_driven_policy.cpp
================================================================================
*/

#include "v2/sampling/uncertainty_driven_policy.hpp"
#include <algorithm>
#include <numeric>
#include <cmath>
#include <sstream>
#include <ctime>

namespace v2::sampling {

UncertaintyDrivenPolicy::UncertaintyDrivenPolicy(const Parameters& params)
    : params_(params) {
}

std::vector<physics::RotorGeometry> UncertaintyDrivenPolicy::generate_candidates(
    const std::vector<EvaluatedDesign>& evaluated_designs,
    const core::RunConfig& config,
    size_t count) const {
    
    std::vector<physics::RotorGeometry> candidates;
    
    if (evaluated_designs.empty()) {
        // No prior evaluations: return baseline candidates
        for (size_t i = 0; i < count; ++i) {
            physics::RotorGeometry geom;
            geom.rotor_radius_m = 0.5 + (i * 0.1);  // Vary radius
            geom.rotor_count = 4;
            geom.is_coaxial = false;
            geom.has_shroud = false;
            candidates.push_back(geom);
        }
        return candidates;
    }
    
    // Generate perturbations of existing designs
    std::mt19937_64 rng(config.global_seed + 1000);  // Offset seed for sampling
    
    for (size_t i = 0; i < params_.perturbation_attempts && candidates.size() < count * 10; ++i) {
        // Pick a random evaluated design
        std::uniform_int_distribution<size_t> design_dist(0, evaluated_designs.size() - 1);
        const auto& base_design = evaluated_designs[design_dist(rng)];
        
        // Perturb parameters
        std::normal_distribution<double> perturbation(0.0, 0.1);  // 10% perturbation
        
        physics::RotorGeometry perturbed = base_design.geometry;
        perturbed.rotor_radius_m *= (1.0 + perturbation(rng));
        perturbed.rotor_radius_m = std::max(0.1, std::min(2.0, perturbed.rotor_radius_m));
        
        candidates.push_back(perturbed);
    }
    
    return candidates;
}

double UncertaintyDrivenPolicy::compute_diversity_penalty(
    const physics::RotorGeometry& candidate,
    const std::vector<EvaluatedDesign>& evaluated_designs) const {
    
    if (evaluated_designs.empty()) {
        return 0.0;  // No penalty if no evaluations
    }
    
    // Compute minimum distance to any evaluated design
    double min_distance = std::numeric_limits<double>::max();
    
    for (const auto& eval : evaluated_designs) {
        // Simple Euclidean distance in normalized parameter space
        double radius_diff = (candidate.rotor_radius_m - eval.geometry.rotor_radius_m) / 1.0;  // Normalize
        double count_diff = static_cast<double>(candidate.rotor_count - eval.geometry.rotor_count) / 8.0;
        
        double distance = std::sqrt(radius_diff * radius_diff + count_diff * count_diff);
        min_distance = std::min(min_distance, distance);
    }
    
    // Convert to penalty: closer = higher penalty
    double diversity_score = min_distance;  // Higher distance = higher score
    return diversity_score;
}

std::vector<BoundaryProximity> UncertaintyDrivenPolicy::estimate_boundary_proximity(
    const physics::RotorGeometry& candidate,
    const std::vector<EvaluatedDesign>& evaluated_designs) const {
    
    std::vector<BoundaryProximity> proximities;
    
    // Estimate constraint proximity based on nearby evaluated designs
    // This is a placeholder - real implementation would interpolate from evaluated designs
    
    // Example: disk loading constraint
    BoundaryProximity disk_loading_prox;
    disk_loading_prox.constraint_name = "max_disk_loading";
    disk_loading_prox.threshold = 150.0;  // Example threshold
    disk_loading_prox.current_value = 100.0;  // Estimated (would interpolate from evaluations)
    disk_loading_prox.margin = disk_loading_prox.threshold - disk_loading_prox.current_value;
    disk_loading_prox.margin_fraction = disk_loading_prox.margin / disk_loading_prox.threshold;
    disk_loading_prox.is_active = std::abs(disk_loading_prox.margin_fraction) < params_.boundary_margin_threshold;
    proximities.push_back(disk_loading_prox);
    
    return proximities;
}

AcquisitionScore UncertaintyDrivenPolicy::compute_acquisition_score(
    const physics::RotorGeometry& candidate,
    const std::vector<EvaluatedDesign>& evaluated_designs) const {
    
    AcquisitionScore score;
    
    // 1. Exploration value: uncertainty in nearby designs
    // Estimate uncertainty from evaluated designs (higher uncertainty = higher exploration value)
    double max_uncertainty = 0.0;
    for (const auto& eval : evaluated_designs) {
        for (const auto& output : eval.risk_report.output_results) {
            double uncertainty_measure = (output.p90_value - output.p50_value) / output.p50_value;
            max_uncertainty = std::max(max_uncertainty, uncertainty_measure);
        }
    }
    score.exploration_value = max_uncertainty;
    
    // 2. Boundary value: proximity to constraints
    auto proximities = estimate_boundary_proximity(candidate, evaluated_designs);
    double boundary_score = 0.0;
    for (const auto& prox : proximities) {
        if (prox.is_active) {
            // Higher score for designs near boundaries
            boundary_score += 1.0 / (1.0 + std::abs(prox.margin_fraction));
        }
    }
    score.boundary_value = boundary_score;
    
    // 3. Diversity value
    double diversity = compute_diversity_penalty(candidate, evaluated_designs);
    
    // 4. Total acquisition value (weighted combination)
    score.total_value = 
        params_.exploration_weight * score.exploration_value +
        params_.boundary_weight * score.boundary_value +
        params_.diversity_weight * diversity;
    
    // Determine dominant strategy
    if (score.exploration_value > score.boundary_value && score.exploration_value > diversity) {
        score.strategy_used = "exploration";
    } else if (score.boundary_value > diversity) {
        score.strategy_used = "boundary";
    } else {
        score.strategy_used = "diversity";
    }
    
    return score;
}

std::vector<ProposedDesign> UncertaintyDrivenPolicy::propose_next_candidates(
    const std::vector<EvaluatedDesign>& evaluated_designs,
    const core::RunConfig& config,
    size_t proposal_count) const {
    
    // Generate candidate designs
    auto candidates = generate_candidates(evaluated_designs, config, proposal_count);
    
    // Score all candidates
    std::vector<std::pair<physics::RotorGeometry, AcquisitionScore>> scored_candidates;
    for (const auto& candidate : candidates) {
        auto score = compute_acquisition_score(candidate, evaluated_designs);
        scored_candidates.emplace_back(candidate, score);
    }
    
    // Sort by acquisition value (descending)
    std::sort(scored_candidates.begin(), scored_candidates.end(),
              [](const auto& a, const auto& b) {
                  return a.second.total_value > b.second.total_value;
              });
    
    // Take top N proposals
    std::vector<ProposedDesign> proposals;
    for (size_t i = 0; i < std::min(proposal_count, scored_candidates.size()); ++i) {
        ProposedDesign prop;
        prop.geometry = scored_candidates[i].first;
        prop.acquisition_score = scored_candidates[i].second;
        prop.rank = static_cast<int>(i + 1);
        
        // Generate proposal ID
        std::ostringstream oss;
        oss << "proposal_" << config.run_id << "_" << (i + 1);
        prop.proposal_id = oss.str();
        
        // Generate rationale
        std::ostringstream rationale_oss;
        rationale_oss << "Strategy: " << prop.acquisition_score.strategy_used
                      << " (value=" << prop.acquisition_score.total_value << ")";
        prop.rationale = rationale_oss.str();
        
        // Parent design (closest evaluated design)
        if (!evaluated_designs.empty()) {
            prop.parent_design_id = evaluated_designs[0].design_id;  // Simplified
        }
        
        proposals.push_back(prop);
    }
    
    return proposals;
}

} // namespace v2::sampling
