#pragma once

#include <array>
#include <cstdint>
#include <iomanip>
#include <locale>
#include <map>
#include <sstream>
#include <string>
#include <string_view>

namespace v2::io {

inline constexpr std::string_view kRunIdCharset = "0123456789abcdef";

inline constexpr std::uint64_t fnv1a_64(std::string_view data) {
    std::uint64_t hash = 14695981039346656037ULL;
    for (unsigned char c : data) {
        hash ^= static_cast<std::uint64_t>(c);
        hash *= 1099511628211ULL;
    }
    return hash;
}

inline std::string canonical_scalar(double value, int precision = 12) {
    std::ostringstream oss;
    oss.imbue(std::locale::classic());
    oss << std::fixed << std::setprecision(precision) << value;
    return oss.str();
}

std::string canonicalize_kv(const std::map<std::string, std::string>& kv);
std::string canonicalize_kv(const std::map<std::string, double>& kv, int precision = 12);

std::string compute_run_id(std::string_view canonical_input);

}  // namespace v2::io
