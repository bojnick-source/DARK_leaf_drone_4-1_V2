#include "v2/io/artifacts.hpp"

namespace v2::io {

std::filesystem::path artifact_root(std::string_view run_id, std::string_view base) {
    return std::filesystem::path(base) / kRunsSubdir / std::filesystem::path(run_id);
}

std::filesystem::path run_output_path(const std::filesystem::path& root) {
    return root / kRunOutputFile;
}

bool ensure_artifact_dirs(const std::filesystem::path& root) {
    std::error_code ec;
    std::filesystem::create_directories(root, ec);
    return !ec;
}

}  // namespace v2::io
