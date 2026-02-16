#pragma once

#include <string>
#include <string_view>
#include <vector>

#include "v2/analysis/accuracy_gate.hpp"

namespace v2::analysis {

struct EvidenceSummary {
    std::string run_id;
    std::string evidence_hash;
    std::string lineage_id;
};

enum class CommitFailCode { ALREADY_COMMITTED, MISSING_INPUT, HASH_MISMATCH, RUN_ID_MISMATCH, LINEAGE_MISSING };

struct CommitDecision {
    bool allow_commit{false};
    std::vector<CommitFailCode> reasons;
    std::string audit_json;
};

CommitDecision commit_gate_evaluate(const RunContext& ctx, const EvidenceSummary& evidence);

}  // namespace v2::analysis
