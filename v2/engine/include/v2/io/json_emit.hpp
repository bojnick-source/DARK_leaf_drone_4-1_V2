#pragma once

#include <filesystem>
#include <map>
#include <optional>
#include <string>
#include <vector>

#include "v2/io/artifacts.hpp"
#include "v2/io/run_id.hpp"

namespace v2::io {

struct RunOutputRecord {
    std::string run_id;
    std::string inputs_json;
    std::map<std::string, double> metrics;
    bool ok{true};
    std::optional<std::string> label;
    std::string artifact_root;
    std::vector<std::string> artifact_paths;
    std::string schema = "dark/v2/io/run_output/2.0";
};

std::string emit_run_output_json(const RunOutputRecord& record, int precision = 12);
bool write_run_output_file(const RunOutputRecord& record, const std::filesystem::path& output_path, int precision = 12);
bool write_run_output_file(const RunOutputRecord& record, int precision = 12);

}  // namespace v2::io
