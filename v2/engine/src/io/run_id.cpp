#include "v2/io/run_id.hpp"

#include <sstream>

namespace v2::io {

namespace {
std::string escape_string(std::string_view in) {
    std::string out;
    out.reserve(in.size());
    for (char c : in) {
        switch (c) {
            case '\\': out += "\\\\"; break;
            case '\"': out += "\\\""; break;
            default: out.push_back(c); break;
        }
    }
    return out;
}
}  // namespace

std::string canonicalize_kv(const std::map<std::string, std::string>& kv) {
    std::ostringstream oss;
    oss.imbue(std::locale::classic());
    oss << "{";
    bool first = true;
    for (const auto& [k, v] : kv) {
        if (!first) {
            oss << ",";
        }
        first = false;
        oss << "\"" << escape_string(k) << "\":\"" << escape_string(v) << "\"";
    }
    oss << "}";
    return oss.str();
}

std::string canonicalize_kv(const std::map<std::string, double>& kv, int precision) {
    std::map<std::string, std::string> as_string;
    for (const auto& [k, v] : kv) {
        as_string.emplace(k, canonical_scalar(v, precision));
    }
    return canonicalize_kv(as_string);
}

std::string compute_run_id(std::string_view canonical_input) {
    const std::uint64_t h = fnv1a_64(canonical_input);
    std::string out(16, '0');
    for (int i = 0; i < 16; ++i) {
        const auto nibble = static_cast<int>((h >> ((15 - i) * 4)) & 0xF);
        out[i] = static_cast<char>(nibble < 10 ? ('0' + nibble) : ('a' + (nibble - 10)));
    }
    return out;
}

}  // namespace v2::io
