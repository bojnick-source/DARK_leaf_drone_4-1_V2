#pragma once
/*
================================================================================
v2 Sampling — Uncertainty-Driven Sampling Policy
FILE: v2/engine/include/v2/sampling/uncertainty_driven_policy.hpp

Purpose:
  - Concrete implementation of SamplingPolicy
  - Proposes designs that maximize information gain
  - Balances exploration (high uncertainty) vs boundary discovery
  - Deterministic and reproducible

Strategy:
  - Exploration: Sample where uncertainty is highest
  - Boundary: Sample near constraint boundaries
  - Diversity: Avoid clustering proposals
================================================================================
*/

#include "v2/sampling/sampling_policy.hpp"
#include <random>

namespace v2::sampling {

/**
 * UncertaintyDrivenPolicy: Sample to reduce uncertainty and find boundaries
 * 
 * Acquisition function combines:
 * 1. Uncertainty: P90-P50 spread (epistemic uncertainty proxy)
 * 2. Boundary proximity: Distance to nearest active constraint
 * 3. Diversity: Penalty for designs too similar to existing evaluations
 */
class UncertaintyDrivenPolicy : public SamplingPolicy {
public:
    struct Parameters {
        double exploration_weight;             // Weight for uncertainty term
        double boundary_weight;                // Weight for boundary proximity
        double diversity_weight;               // Weight for diversity
        double boundary_margin_threshold;      // Consider constraints within threshold as "boundary"
        size_t perturbation_attempts;          // Candidate perturbations per proposal
        
        Parameters() 
            : exploration_weight(0.4)
            , boundary_weight(0.4)
            , diversity_weight(0.2)
            , boundary_margin_threshold(0.1)
            , perturbation_attempts(100) {}
    };
    
    /**
     * Constructor with configurable parameters
     */
    explicit UncertaintyDrivenPolicy(const Parameters& params = Parameters());
    
    /**
     * Propose next candidates based on uncertainty and boundaries
     */
    std::vector<ProposedDesign> propose_next_candidates(
        const std::vector<EvaluatedDesign>& evaluated_designs,
        const core::RunConfig& config,
        size_t proposal_count) const override;
    
    /**
     * Get policy name
     */
    std::string get_policy_name() const override {
        return "UncertaintyDrivenPolicy";
    }

private:
    Parameters params_;
    
    /**
     * Compute acquisition score for a candidate design
     */
    AcquisitionScore compute_acquisition_score(
        const physics::RotorGeometry& candidate,
        const std::vector<EvaluatedDesign>& evaluated_designs) const;
    
    /**
     * Generate candidate perturbations from evaluated designs
     */
    std::vector<physics::RotorGeometry> generate_candidates(
        const std::vector<EvaluatedDesign>& evaluated_designs,
        const core::RunConfig& config,
        size_t count) const;
    
    /**
     * Compute diversity penalty (similarity to existing designs)
     */
    double compute_diversity_penalty(
        const physics::RotorGeometry& candidate,
        const std::vector<EvaluatedDesign>& evaluated_designs) const;
    
    /**
     * Find boundary proximity for a candidate
     */
    std::vector<BoundaryProximity> estimate_boundary_proximity(
        const physics::RotorGeometry& candidate,
        const std::vector<EvaluatedDesign>& evaluated_designs) const;
};

} // namespace v2::sampling
