#pragma once
/*
================================================================================
v2 Safety — Safety Gate Interface
FILE: v2/engine/include/v2/safety/safety_gate.hpp

Purpose:
  - Define interface for safety decision making
  - Evaluate designs against safety criteria
  - Produce auditable accept/reject/defer decisions
  - Conservative under uncertainty

Architecture:
  - Pure interface, stateless
  - Deterministic given inputs
  - Evidence-based decisions only
  - Full traceability required
================================================================================
*/

#include "v2/safety/types.hpp"
#include "v2/uncertainty/types.hpp"
#include "v2/core/run_config.hpp"
#include <memory>

namespace v2::safety {

/**
 * SafetyGate: Pure interface for safety decision making
 * 
 * Stateless: All state passed explicitly via inputs
 * Deterministic: Same inputs ⇒ same decisions
 * Auditable: Every decision has full justification
 */
class SafetyGate {
public:
    virtual ~SafetyGate() = default;
    
    /**
     * Evaluate a design for safety
     * 
     * @param risk_report Risk assessment from uncertainty quantification
     * @param thresholds Safety thresholds to apply
     * @param config Run configuration for traceability
     * @return SafetyDecisionRecord with decision and full justification
     */
    virtual SafetyDecisionRecord evaluate_safety(
        const uncertainty::RiskReport& risk_report,
        const SafetyThresholds& thresholds,
        const core::RunConfig& config) const = 0;
    
    /**
     * Get gate name for traceability
     */
    virtual std::string get_gate_name() const = 0;
};

} // namespace v2::safety
