#pragma once

#include <string>
#include <string_view>
#include <vector>

namespace v2::analysis {

struct RunContext {
    std::string expected_run_id;
};

enum class GateFailCode {
    MISSING_FIELD,
    INVALID_VALUE,
    RUN_ID_MISMATCH,
    HASH_MISMATCH,
    GCI_FAIL,
    VALIDATION_FAIL
};

struct GateReason {
    GateFailCode code;
    std::string detail;
};

struct GateDecision {
    bool pass{false};
    std::vector<GateReason> reasons;
    std::string audit_json;
};

GateDecision accuracy_gate_evaluate(std::string_view evidence_json, const RunContext& ctx);
std::string evidence_payload_digest(std::string_view evidence_json);

}  // namespace v2::analysis
