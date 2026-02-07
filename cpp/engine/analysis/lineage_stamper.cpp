#include "lineage_stamper.hpp"

#include <algorithm>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <locale>
#include <sstream>

#include "v2/io/artifacts.hpp"
#include "v2/io/run_id.hpp"

namespace engine::analysis {

namespace {

constexpr const char* kLineageFile = "lineage.json";
constexpr const char* kLineageAuditFile = "lineage_audit.json";

std::string to_hex(std::uint64_t value) {
    std::ostringstream oss;
    oss << std::hex << std::nouppercase << value;
    return oss.str();
}

std::string escape_json_string(std::string_view in) {
    std::string out;
    out.reserve(in.size());
    for (char c : in) {
        switch (c) {
            case '\\': out += "\\\\"; break;
            case '\"': out += "\\\""; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default: out.push_back(c); break;
        }
    }
    return out;
}

std::string canonical_join(const std::vector<std::string>& items) {
    std::ostringstream oss;
    for (std::size_t i = 0; i < items.size(); ++i) {
        if (i != 0) oss << ",";
        oss << items[i];
    }
    return oss.str();
}

std::string build_lineage_json(const LineageInput& input, const std::string& lineage_hash) {
    std::ostringstream oss;
    oss.imbue(std::locale::classic());
    oss << "{";
    oss << "\"run_id\":\"" << input.run_id << "\",";
    oss << "\"lineage_hash\":\"" << lineage_hash << "\",";
    oss << "\"parents\":[";
    for (std::size_t i = 0; i < input.parent_run_ids.size(); ++i) {
        if (i != 0) oss << ",";
        oss << "\"" << input.parent_run_ids[i] << "\"";
    }
    oss << "],";
    oss << "\"inputs\":[";
    for (std::size_t i = 0; i < input.input_artifacts.size(); ++i) {
        if (i != 0) oss << ",";
        oss << "\"" << input.input_artifacts[i] << "\"";
    }
    oss << "],";
    oss << "\"outputs\":[";
    for (std::size_t i = 0; i < input.output_artifacts.size(); ++i) {
        if (i != 0) oss << ",";
        oss << "\"" << input.output_artifacts[i] << "\"";
    }
    oss << "],";
    oss << "\"canonical_inputs\":\"" << escape_json_string(input.canonical_inputs) << "\"";
    oss << "}";
    return oss.str();
}

std::string build_audit_json(const LineageResult& result, const std::filesystem::path& lineage_path,
                             const std::string& lineage_hash) {
    std::ostringstream oss;
    oss << "{";
    oss << "\"ok\":" << (result.ok ? "true" : "false") << ",";
    oss << "\"lineage_hash\":\"" << lineage_hash << "\",";
    oss << "\"lineage_path\":\"" << lineage_path.generic_string() << "\"";
    oss << "}";
    return oss.str();
}

std::string read_file(const std::filesystem::path& p) {
    std::ifstream in(p, std::ios::binary);
    if (!in.is_open()) return {};
    std::ostringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

}  // namespace

LineageResult stamp_lineage(const RunContext& ctx, const LineageInput& raw_input) {
    LineageResult result;

    if (raw_input.run_id != ctx.expected_run_id || raw_input.run_id.empty()) {
        result.ok = false;
        result.lineage_json = "{}";
        result.audit_json = "{\"ok\":false,\"lineage_hash\":\"\",\"lineage_path\":\"\"}";
        return result;
    }

    LineageInput input = raw_input;
    std::sort(input.parent_run_ids.begin(), input.parent_run_ids.end());
    std::sort(input.input_artifacts.begin(), input.input_artifacts.end());
    std::sort(input.output_artifacts.begin(), input.output_artifacts.end());

    const std::string fingerprint =
        input.run_id + "|" + canonical_join(input.parent_run_ids) + "|" +
        canonical_join(input.input_artifacts) + "|" + canonical_join(input.output_artifacts) + "|" +
        input.canonical_inputs;
    const std::string lineage_hash = to_hex(v2::io::fnv1a_64(fingerprint));

    const auto root = v2::io::artifact_root(input.run_id);
    const auto lineage_path = root / kLineageFile;
    const auto audit_path = root / kLineageAuditFile;

    const std::string lineage_json = build_lineage_json(input, lineage_hash);

    const bool exists = std::filesystem::exists(lineage_path);
    if (exists) {
        const std::string existing = read_file(lineage_path);
        result.ok = (existing == lineage_json);
        result.lineage_json = lineage_json;
        result.audit_json = build_audit_json(result, lineage_path, lineage_hash);
        return result;
    }

    v2::io::ensure_artifact_dirs(root);
    const std::string tmp = lineage_path.string() + ".tmp";
    {
        std::ofstream out(tmp, std::ios::binary | std::ios::trunc);
        out << lineage_json;
    }
    std::filesystem::rename(tmp, lineage_path);

    const std::string audit_tmp = audit_path.string() + ".tmp";
    result.ok = true;
    result.lineage_json = lineage_json;
    result.audit_json = build_audit_json(result, lineage_path, lineage_hash);
    {
        std::ofstream out(audit_tmp, std::ios::binary | std::ios::trunc);
        out << result.audit_json;
    }
    std::filesystem::rename(audit_tmp, audit_path);
    return result;
}

}  // namespace engine::analysis
