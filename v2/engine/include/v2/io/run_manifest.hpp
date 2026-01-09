#pragma once

#include <cstdint>
#include <cmath>
#include <iomanip>
#include <locale>
#include <map>
#include <sstream>
#include <string>
#include <string_view>

namespace v2::io {

inline constexpr std::string_view kRunsDir = "runs";
inline constexpr std::string_view kArtifactsDir = "artifacts";
inline constexpr std::string_view kManifestFile = "manifest.json";
inline constexpr std::string_view kInputsFile = "inputs.json";
inline constexpr std::string_view kMetricsFile = "metrics.json";

inline constexpr std::uint64_t fnv1a_64(std::string_view data) {
    std::uint64_t hash = 14695981039346656037ULL;
    for (unsigned char c : data) {
        hash ^= static_cast<std::uint64_t>(c);
        hash *= 1099511628211ULL;
    }
    return hash;
}

inline std::string run_id_from_seed(std::string_view seed) {
    const std::uint64_t h = fnv1a_64(seed);
    std::string out(16, '0');
    for (int i = 0; i < 16; ++i) {
        const auto nibble = static_cast<int>((h >> ((15 - i) * 4)) & 0xF);
        out[i] = static_cast<char>(nibble < 10 ? ('0' + nibble) : ('a' + (nibble - 10)));
    }
    return out;
}

inline std::string manifest_path(std::string_view run_id) {
    std::string path;
    path.reserve(kRunsDir.size() + 1 + run_id.size() + 1 + kManifestFile.size());
    path.append(kRunsDir).push_back('/');
    path.append(run_id).push_back('/');
    path.append(kManifestFile);
    return path;
}

inline std::string artifact_dir(std::string_view run_id) {
    std::string path;
    path.reserve(kRunsDir.size() + 1 + run_id.size() + 1 + kArtifactsDir.size());
    path.append(kRunsDir).push_back('/');
    path.append(run_id).push_back('/');
    path.append(kArtifactsDir);
    return path;
}

inline std::string format_scalar(double value, int precision = 12) {
    if (!std::isfinite(value)) {
        return "nan";
    }
    std::ostringstream oss;
    oss.imbue(std::locale::classic());
    oss << std::fixed << std::setprecision(precision) << value;
    return oss.str();
}

inline std::string canonicalize_inputs(const std::map<std::string, double>& scalars,
                                       const std::map<std::string, std::string>& text = {}) {
    std::ostringstream oss;
    oss.imbue(std::locale::classic());
    oss << "{";
    bool first = true;
    for (const auto& [k, v] : scalars) {
        if (!first) {
            oss << ",";
        }
        first = false;
        oss << "\"s:" << k << "\":" << "\"" << format_scalar(v) << "\"";
    }
    for (const auto& [k, v] : text) {
        if (!first) {
            oss << ",";
        }
        first = false;
        oss << "\"t:" << k << "\":\"" << v << "\"";
    }
    oss << "}";
    return oss.str();
}

inline std::string run_id_from_inputs(const std::map<std::string, double>& scalars,
                                      const std::map<std::string, std::string>& text = {}) {
    return run_id_from_seed(canonicalize_inputs(scalars, text));
}

}  // namespace v2::io
