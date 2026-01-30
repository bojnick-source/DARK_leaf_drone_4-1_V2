#pragma once
/*
================================================================================
v2 Sampling — Types and Data Structures
FILE: v2/engine/include/v2/sampling/types.hpp

Purpose:
  - Define data structures for agentic sampling
  - Store evaluated designs with risk assessments
  - Represent proposed designs with value scores
  - Maintain full audit trail

This implements EXECUTION_0.3: Agentic Sampling and Boundary Discovery
================================================================================
*/

#include "v2/physics/types.hpp"
#include "v2/uncertainty/types.hpp"
#include <string>
#include <vector>
#include <map>

namespace v2::sampling {

/**
 * EvaluatedDesign: A design that has been evaluated with uncertainty quantification
 */
struct EvaluatedDesign {
    // Design parameters
    physics::RotorGeometry geometry;
    
    // Uncertainty quantification results
    uncertainty::RiskReport risk_report;
    
    // Constraint satisfaction (for boundary discovery)
    std::map<std::string, double> constraint_margins;  // Distance from constraint boundaries
    
    // Metadata
    std::string design_id;
    double evaluation_time_s = 0.0;
};

/**
 * AcquisitionScore: Value metrics for proposing next experiments
 */
struct AcquisitionScore {
    double total_value = 0.0;           // Overall acquisition value
    double exploration_value = 0.0;     // Value from exploring uncertain regions
    double exploitation_value = 0.0;    // Value from exploiting promising regions
    double boundary_value = 0.0;        // Value from constraint boundary proximity
    std::string strategy_used;          // Which acquisition function was used
};

/**
 * ProposedDesign: A candidate design proposed for next evaluation
 */
struct ProposedDesign {
    // Proposed design parameters
    physics::RotorGeometry geometry;
    
    // Acquisition scoring
    AcquisitionScore acquisition_score;
    
    // Rationale for proposal
    std::string rationale;              // Human-readable explanation
    int rank = 0;                       // Rank among proposals (1 = highest value)
    
    // Metadata
    std::string proposal_id;
    std::string parent_design_id;       // Which evaluated design inspired this
};

/**
 * SamplingReport: Complete audit trail for sampling decisions
 */
struct SamplingReport {
    // Traceability
    std::string run_id;
    uint64_t seed = 0;
    std::string policy_name;
    std::string timestamp;
    
    // Input state
    size_t num_evaluated_designs = 0;
    std::vector<std::string> evaluated_design_ids;
    
    // Proposals
    std::vector<ProposedDesign> proposals;
    
    // Summary statistics
    double best_acquisition_value = 0.0;
    double mean_acquisition_value = 0.0;
    std::string dominant_strategy;      // exploration vs exploitation vs boundary
    
    /**
     * Serialize to JSON for artifact emission
     */
    std::string to_json() const;
    
    /**
     * Write report to file
     */
    void write_to_file(const std::string& filepath) const;
};

/**
 * BoundaryProximity: Metrics for how close a design is to constraints
 */
struct BoundaryProximity {
    std::string constraint_name;
    double current_value = 0.0;
    double threshold = 0.0;
    double margin = 0.0;                // Positive = safe, negative = violated
    double margin_fraction = 0.0;       // Margin as fraction of threshold
    bool is_active = false;             // Is this constraint near the boundary?
};

} // namespace v2::sampling
