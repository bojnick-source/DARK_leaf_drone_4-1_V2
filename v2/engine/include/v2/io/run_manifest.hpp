#pragma once

#include <cstdint>
#include <cmath>
#include <iomanip>
#include <locale>
#include <map>
#include <sstream>
#include <utility>
#include <vector>
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

inline std::string format_array(const std::vector<double>& values, int precision = 12) {
    std::ostringstream oss;
    oss.imbue(std::locale::classic());
    oss << "[";
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i != 0) {
            oss << ",";
        }
        oss << format_scalar(values[i], precision);
    }
    oss << "]";
    return oss.str();
}

inline std::string canonicalize_inputs(
    const std::map<std::string, double>& scalars,
    const std::map<std::string, std::string>& text = {},
    const std::map<std::string, std::vector<double>>& arrays = {},
    const std::map<std::string, std::pair<double, std::string>>& units = {},
    int precision = 12) {
    std::ostringstream oss;
    oss.imbue(std::locale::classic());
    oss << "{";
    bool first = true;
    for (const auto& [k, v] : scalars) {
        if (!first) {
            oss << ",";
        }
        first = false;
        oss << "\"s:" << k << "\":" << "\"" << format_scalar(v, precision) << "\"";
    }
    for (const auto& [k, v] : text) {
        if (!first) {
            oss << ",";
        }
        first = false;
        oss << "\"t:" << k << "\":\"" << v << "\"";
    }
    for (const auto& [k, v] : arrays) {
        if (!first) {
            oss << ",";
        }
        first = false;
        oss << "\"a:" << k << "\":\"" << format_array(v, precision) << "\"";
    }
    for (const auto& [k, v] : units) {
        if (!first) {
            oss << ",";
        }
        first = false;
        oss << "\"u:" << k << "\":\"" << format_scalar(v.first, precision) << " " << v.second
            << "\"";
    }
    oss << "}";
    return oss.str();
}

inline std::string run_id_from_inputs(
    const std::map<std::string, double>& scalars,
    const std::map<std::string, std::string>& text = {},
    const std::map<std::string, std::vector<double>>& arrays = {},
    const std::map<std::string, std::pair<double, std::string>>& units = {},
    int precision = 12) {
    return run_id_from_seed(canonicalize_inputs(scalars, text, arrays, units, precision));
}

}  // namespace v2::io
