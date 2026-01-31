#include "commit_gate.hpp"

#include <filesystem>
#include <fstream>
#include <sstream>

#include "v2/io/artifacts.hpp"
#include "v2/io/run_id.hpp"

namespace engine::analysis {

namespace {
constexpr const char* kCommitMarkerFile = "commit.marker";
constexpr const char* kCommitAuditFile = "commit_audit.json";

std::string fail_code_to_string(CommitFailCode code) {
    switch (code) {
        case CommitFailCode::ALREADY_COMMITTED: return "ALREADY_COMMITTED";
        case CommitFailCode::MISSING_INPUT: return "MISSING_INPUT";
        case CommitFailCode::HASH_MISMATCH: return "HASH_MISMATCH";
        case CommitFailCode::LINEAGE_MISSING: return "LINEAGE_MISSING";
    }
    return "UNKNOWN";
}

std::string build_audit_json(const CommitDecision& decision, const EvidenceSummary& evidence,
                             const std::filesystem::path& marker_path) {
    std::ostringstream oss;
    oss << "{\"allow_commit\":" << (decision.allow_commit ? "true" : "false") << ","
        << "\"run_id\":\"" << evidence.run_id << "\","
        << "\"lineage_id\":\"" << evidence.lineage_id << "\","
        << "\"evidence_hash\":\"" << evidence.evidence_hash << "\","
        << "\"marker_path\":\"" << marker_path.generic_string() << "\","
        << "\"reasons\":[";
    for (std::size_t i = 0; i < decision.reasons.size(); ++i) {
        if (i != 0) oss << ",";
        oss << "\"" << fail_code_to_string(decision.reasons[i]) << "\"";
    }
    oss << "]}";
    return oss.str();
}

std::pair<std::string, std::string> read_marker(const std::filesystem::path& marker) {
    std::ifstream in(marker);
    if (!in) return {};
    std::string line;
    std::string run_id;
    std::string hash;
    while (std::getline(in, line)) {
        auto pos = line.find('=');
        if (pos == std::string::npos) continue;
        auto key = line.substr(0, pos);
        auto val = line.substr(pos + 1);
        if (key == "run_id") run_id = val;
        if (key == "evidence_hash") hash = val;
    }
    return {run_id, hash};
}

void write_marker(const std::filesystem::path& marker, const EvidenceSummary& evidence) {
    const auto tmp = marker.string() + ".tmp";
    {
        std::ofstream out(tmp, std::ios::trunc);
        out << "run_id=" << evidence.run_id << "\n";
        out << "evidence_hash=" << evidence.evidence_hash << "\n";
        out << "lineage_id=" << evidence.lineage_id << "\n";
    }
    std::filesystem::rename(tmp, marker);
}

}  // namespace

CommitDecision commit_gate_evaluate(const RunContext& ctx, const EvidenceSummary& evidence) {
    CommitDecision decision;
    std::vector<CommitFailCode> reasons;

    if (evidence.run_id.empty() || evidence.evidence_hash.empty()) {
        reasons.push_back(CommitFailCode::MISSING_INPUT);
    }
    if (evidence.run_id != ctx.expected_run_id) {
        reasons.push_back(CommitFailCode::HASH_MISMATCH);
    }
    if (evidence.lineage_id.empty()) {
        reasons.push_back(CommitFailCode::LINEAGE_MISSING);
    }

    const auto root = v2::io::artifact_root(ctx.expected_run_id);
    const auto marker = root / kCommitMarkerFile;

    if (std::filesystem::exists(marker)) {
        const auto [stored_run_id, stored_hash] = read_marker(marker);
        if (stored_run_id == ctx.expected_run_id && stored_hash == evidence.evidence_hash) {
            decision.allow_commit = reasons.empty();
        } else {
            reasons.push_back(CommitFailCode::HASH_MISMATCH);
        }
    }

    if (reasons.empty() && !std::filesystem::exists(marker)) {
        v2::io::ensure_artifact_dirs(root);
        write_marker(marker, evidence);
        decision.allow_commit = true;
    }

    // If marker existed with different hash and no previous reason, classify as already committed mismatch.
    if (!decision.allow_commit && std::filesystem::exists(marker) && reasons.empty()) {
        reasons.push_back(CommitFailCode::ALREADY_COMMITTED);
    }

    decision.reasons = std::move(reasons);
    decision.audit_json = build_audit_json(decision, evidence, marker);
    return decision;
}

}  // namespace engine::analysis
