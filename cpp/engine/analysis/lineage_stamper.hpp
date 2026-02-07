#pragma once

#include <string>
#include <vector>

#include "analysis/accuracy_gate.hpp"

namespace engine::analysis {

struct LineageInput {
    std::string run_id;
    std::vector<std::string> parent_run_ids;
    std::vector<std::string> input_artifacts;
    std::vector<std::string> output_artifacts;
    std::string canonical_inputs;
};

struct LineageResult {
    bool ok{false};
    std::string lineage_json;
    std::string audit_json;
};

LineageResult stamp_lineage(const RunContext& ctx, const LineageInput& input);

}  // namespace engine::analysis
