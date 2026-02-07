#pragma once

#include <filesystem>
#include <string>
#include <string_view>
#include <vector>

namespace v2::io {

inline constexpr std::string_view kArtifactsRoot = "artifacts";
inline constexpr std::string_view kRunsSubdir = "runs";
inline constexpr std::string_view kRunOutputFile = "run_output.json";

std::filesystem::path artifact_root(std::string_view run_id, std::string_view base = kArtifactsRoot);
std::filesystem::path run_output_path(const std::filesystem::path& artifact_root);
bool ensure_artifact_dirs(const std::filesystem::path& artifact_root);

}  // namespace v2::io
