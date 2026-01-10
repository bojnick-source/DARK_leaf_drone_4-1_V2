#include "v2/io/json_emit.hpp"

#include <filesystem>
#include <fstream>
#include <locale>
#include <sstream>

#include "v2/io/artifacts.hpp"
#include "v2/io/run_id.hpp"

namespace v2::io {

std::string emit_run_output_json(const RunOutputRecord& record, int precision) {
    std::ostringstream oss;
    oss.imbue(std::locale::classic());
    oss << "{";
    oss << "\"schema\":\"" << record.schema << "\",";
    oss << "\"run_id\":\"" << record.run_id << "\",";
    oss << "\"ok\":" << (record.ok ? "true" : "false") << ",";
    oss << "\"label\":";
    if (record.ok) {
        oss << "null";
    } else if (record.label.has_value()) {
        oss << "\"" << *record.label << "\"";
    } else {
        oss << "null";
    }
    oss << ",\"inputs\":" << record.inputs_json << ",";
    oss << "\"metrics\":{";
    bool first_metric = true;
    for (const auto& [k, v] : record.metrics) {
        if (!first_metric) {
            oss << ",";
        }
        first_metric = false;
        oss << "\"" << k << "\":" << canonical_scalar(v, precision);
    }
    oss << "},";
    oss << "\"artifacts\":{";
    oss << "\"root\":\"" << record.artifact_root << "\",";
    oss << "\"paths\":[";
    for (std::size_t i = 0; i < record.artifact_paths.size(); ++i) {
        if (i != 0) {
            oss << ",";
        }
        oss << "\"" << record.artifact_paths[i] << "\"";
    }
    oss << "]";
    oss << "}";
    oss << "}";
    oss << "\n";
    return oss.str();
}

bool write_run_output_file(const RunOutputRecord& record, const std::filesystem::path& output_path, int precision) {
    std::error_code ec;
    std::filesystem::create_directories(output_path.parent_path(), ec);
    if (ec) return false;
    const auto json = emit_run_output_json(record, precision);
    std::ofstream out(output_path, std::ios::binary | std::ios::trunc);
    if (!out.is_open()) return false;
    out << json;
    return true;
}

bool write_run_output_file(const RunOutputRecord& record, int precision) {
    const auto root = record.artifact_root.empty() ? artifact_root(record.run_id) : std::filesystem::path(record.artifact_root);
    return write_run_output_file(record, run_output_path(root), precision);
}

}  // namespace v2::io
