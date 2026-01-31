#include <cassert>
#include <filesystem>
#include <string>

#include "analysis/commit_gate.hpp"
#include "v2/io/artifacts.hpp"
#include "v2/io/run_id.hpp"

using engine::analysis::CommitDecision;
using engine::analysis::CommitFailCode;
using engine::analysis::EvidenceSummary;
using engine::analysis::RunContext;
using engine::analysis::commit_gate_evaluate;

bool has_reason(const CommitDecision& decision, CommitFailCode code) {
    for (auto r : decision.reasons) {
        if (r == code) return true;
    }
    return false;
}

int main() {
    const std::string canonical = v2::io::canonicalize_kv({{"alpha", 1.0}});
    const std::string run_id = v2::io::compute_run_id(canonical);
    const std::filesystem::path root = v2::io::artifact_root(run_id);
    std::filesystem::remove_all(root);

    RunContext ctx{run_id};
    EvidenceSummary summary{run_id, "hash-123", "lineage-1"};

    // First commit should succeed and create marker.
    CommitDecision first = commit_gate_evaluate(ctx, summary);
    assert(first.allow_commit);
    assert(first.reasons.empty());
    assert(std::filesystem::exists(root / "commit.marker"));

    // Second commit with same hash should be idempotent pass.
    CommitDecision second = commit_gate_evaluate(ctx, summary);
    assert(second.allow_commit);

    // Mismatched hash should fail.
    EvidenceSummary mismatch{run_id, "hash-zzz", "lineage-1"};
    CommitDecision third = commit_gate_evaluate(ctx, mismatch);
    assert(!third.allow_commit);
    assert(has_reason(third, CommitFailCode::HASH_MISMATCH));

    // Missing lineage should fail before writing.
    std::filesystem::remove_all(root);
    EvidenceSummary missing_lineage{run_id, "hash-abc", ""};
    CommitDecision missing = commit_gate_evaluate(ctx, missing_lineage);
    assert(!missing.allow_commit);
    assert(has_reason(missing, CommitFailCode::LINEAGE_MISSING));
    assert(!std::filesystem::exists(root / "commit.marker"));

    std::filesystem::remove_all(root);
    return 0;
}
