#include <cassert>
#include <sstream>
#include <string>

#include "v2/analysis/accuracy_gate.hpp"
#include "v2/io/run_id.hpp"

using v2::analysis::GateDecision;
using v2::analysis::RunContext;
using v2::analysis::accuracy_gate_evaluate;
using v2::analysis::evidence_payload_digest;

std::string build_base_evidence(const std::string& run_id) {
    std::ostringstream oss;
    oss << "{"
        << "\"execution_spec_version\":\"EXECUTION_1.0\","
        << "\"policy_digest\":\"policy-123\","
        << "\"run_id\":\"" << run_id << "\","
        << "\"geometry_hash\":\"geom-abc\","
        << "\"mesh_hash\":\"mesh-xyz\","
        << "\"solver_id\":\"solver-A\","
        << "\"solver_version\":\"1.2.3\","
        << "\"dataset_id\":\"dataset-42\","
        << "\"gci\":{"
        << "\"levels\":[{\"h\":0.5,\"metric\":0.1}],"
        << "\"computed_gci\":0.05,"
        << "\"pass_threshold\":0.05"
        << "},"
        << "\"validation\":{"
        << "\"metrics\":[{\"name\":\"m1\",\"value\":1.0,\"max_allowed\":2.0}]"
        << "},"
        << "\"timestamps\":{"
        << "\"monotonic_clock\":0"
        << "},"
        << "\"signatures\":{}"
        << "}";
    return oss.str();
}

int main() {
    const std::string canonical = v2::io::canonicalize_kv({{"alpha", 1.0}});
    const std::string run_id = v2::io::compute_run_id(canonical);
    const std::string base = build_base_evidence(run_id);
    const std::string evidence_hash = evidence_payload_digest(base);

    std::ostringstream full;
    full << "{"
         << "\"execution_spec_version\":\"EXECUTION_1.0\","
         << "\"policy_digest\":\"policy-123\","
         << "\"run_id\":\"" << run_id << "\","
         << "\"geometry_hash\":\"geom-abc\","
         << "\"mesh_hash\":\"mesh-xyz\","
         << "\"solver_id\":\"solver-A\","
         << "\"solver_version\":\"1.2.3\","
         << "\"dataset_id\":\"dataset-42\","
         << "\"gci\":{"
         << "\"levels\":[{\"h\":0.5,\"metric\":0.1}],"
         << "\"computed_gci\":0.05,"
         << "\"pass_threshold\":0.05"
         << "},"
         << "\"validation\":{"
         << "\"metrics\":[{\"name\":\"m1\",\"value\":1.0,\"max_allowed\":2.0}]"
         << "},"
         << "\"timestamps\":{"
         << "\"monotonic_clock\":0"
         << "},"
         << "\"signatures\":{"
         << "\"evidence_hash\":\"" << evidence_hash << "\""
         << "}"
         << "}";

    RunContext ctx{run_id};
    GateDecision ok = accuracy_gate_evaluate(full.str(), ctx);
    assert(ok.pass);
    assert(ok.reasons.empty());

    // Run ID mismatch
    RunContext wrong_ctx{"different"};
    GateDecision mismatch = accuracy_gate_evaluate(full.str(), wrong_ctx);
    assert(!mismatch.pass);
    bool found_mismatch = false;
    for (const auto& r : mismatch.reasons) {
        if (r.detail == "run_id") found_mismatch = true;
    }
    assert(found_mismatch);

    // Missing field
    std::string missing = "{\"signatures\":{},\"validation\":{},\"gci\":{}}";
    GateDecision missing_decision = accuracy_gate_evaluate(missing, ctx);
    assert(!missing_decision.pass);
    assert(!missing_decision.reasons.empty());

    return 0;
}
