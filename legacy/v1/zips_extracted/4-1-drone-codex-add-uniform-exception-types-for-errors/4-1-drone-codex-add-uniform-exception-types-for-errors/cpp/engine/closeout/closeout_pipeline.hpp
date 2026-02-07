#pragma once
// ============================================================================
// Closeout Pipeline
// File: cpp/engine/closeout/closeout_pipeline.hpp
// ============================================================================
//
// Purpose:
// - Define input/output structures for closeout pipeline.
// - Minimal working skeleton for compilation.
//
// ============================================================================

#include <string>
#include <vector>

namespace lift::closeout {

// Evidence item - a key-value pair with metadata
struct EvidenceItem {
    std::string key;
    std::string value;
    std::string units;
    std::string source;
    std::string notes;
};

// Gate check result
struct GateCheck {
    std::string id;
    bool pass = false;
    double value = kUnset;
    double threshold = kUnset;
    std::string note;
};

// Complete closeout output
struct CloseoutOutput {
    std::vector<EvidenceItem> evidence;
    
    // Gate check details for CSV export
    struct {
        std::vector<GateCheck> checks;
    } gate;
    
    void validate() const {
        // Placeholder validation
    }
};

// Input configuration for closeout pipeline
struct CloseoutInput {
    // Design/candidate identification
    std::string design_id;
    
    // Thresholds to apply
    lift::analysis::CloseoutThresholds thresholds;
    
    // Additional configuration as needed
    std::string notes;
};

// Main pipeline function (currently a stub)
inline CloseoutOutput run_closeout_pipeline(const CloseoutInput& input) {
    CloseoutOutput out;
    // Stub implementation - will be filled in later milestones
    out.validate();
    return out;
}

} // namespace lift::closeout
