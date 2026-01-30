#pragma once
/*
================================================================================
v2 Sampling — Sampling Policy Interface
FILE: v2/engine/include/v2/sampling/sampling_policy.hpp

Purpose:
  - Define interface for next-experiment proposers
  - Select high-value evaluation points using uncertainty and constraints
  - Deterministic, auditable, reporting-only
  - Improve sample efficiency and expose feasibility boundaries

This implements EXECUTION_0.3: Agentic Sampling and Boundary Discovery
================================================================================
*/

#include "v2/sampling/types.hpp"
#include "v2/uncertainty/types.hpp"
#include "v2/physics/types.hpp"
#include "v2/core/run_config.hpp"
#include <vector>
#include <memory>

namespace v2::sampling {

/**
 * SamplingPolicy: Pure interface for proposing next experiments
 * 
 * Stateless: All state passed explicitly via inputs
 * Deterministic: Same inputs + same seed ⇒ same proposals
 * Reporting-only: Never makes automatic accept/reject decisions
 */
class SamplingPolicy {
public:
    virtual ~SamplingPolicy() = default;
    
    /**
     * Propose next candidate designs to evaluate
     * 
     * @param evaluated_designs Previously evaluated designs with risk reports
     * @param config Run configuration with seed for determinism
     * @param proposal_count Number of proposals to generate
     * @return Ranked list of proposed designs (highest value first)
     */
    virtual std::vector<ProposedDesign> propose_next_candidates(
        const std::vector<EvaluatedDesign>& evaluated_designs,
        const core::RunConfig& config,
        size_t proposal_count) const = 0;
    
    /**
     * Get policy name for traceability
     */
    virtual std::string get_policy_name() const = 0;
};

} // namespace v2::sampling
