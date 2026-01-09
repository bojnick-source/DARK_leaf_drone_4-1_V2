#pragma once

#include <cstdint>
#include <cmath>
#include <filesystem>
#include <charconv>
#include <fstream>
#include <iomanip>
#include <locale>
#include <map>
#include <limits>
#include <optional>
#include <sstream>
#include <utility>
#include <vector>
#include <string>
#include <string_view>

#include "v2/core/fail_label.hpp"

namespace v2::io {

inline constexpr std::string_view kRunsDir = "runs";
inline constexpr std::string_view kArtifactsDir = "artifacts";
inline constexpr std::string_view kManifestFile = "manifest.json";
inline constexpr std::string_view kInputsFile = "inputs.json";
inline constexpr std::string_view kMetricsFile = "metrics.json";
inline constexpr std::string_view kRunOutputFile = "run_output.json";
inline constexpr std::string_view kRunIdCharset = "0123456789abcdef";

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

inline std::string run_artifact_dir(std::string_view run_id) {
    std::filesystem::path path = std::filesystem::path(kArtifactsDir) / kRunsDir / run_id;
    return path.generic_string();
}

inline std::string run_output_path(std::string_view run_id) {
    std::filesystem::path path = std::filesystem::path(kArtifactsDir) / kRunsDir / run_id / kRunOutputFile;
    return path.generic_string();
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

enum class LoadError {
    NONE,
    MISSING_FILE,
    JSON_PARSE_ERROR,
    SCHEMA_VIOLATION,
    RUN_ID_MISMATCH,
    INVALID_METRIC,
    INVALID_ARTIFACT_PATH
};

struct JsonValue {
    enum class Type { Null, Bool, Number, String, Object, Array } type{Type::Null};
    bool b{false};
    double number{0.0};
    std::string str;
    std::vector<std::pair<std::string, JsonValue>> object;
    std::vector<JsonValue> array;
};

struct RunOutput {
    std::string run_id;
    bool ok{false};
    std::optional<v2::core::FailLabel> label;
    JsonValue inputs;
    std::map<std::string, double> metrics;
    std::string artifact_root;
    std::vector<std::string> artifact_paths;
};

struct LoadResult {
    bool success{false};
    LoadError code{LoadError::NONE};
    std::string message;
    RunOutput output;
};

inline bool is_lower_hex_run_id(std::string_view run_id) {
    if (run_id.size() != 16) return false;
    for (char c : run_id) {
        if (kRunIdCharset.find(c) == std::string_view::npos) return false;
    }
    return true;
}

inline std::optional<v2::core::FailLabel> fail_label_from_string(std::string_view s) {
    for (auto label : v2::core::kFailLabels) {
        if (v2::core::to_string(label) == s) {
            return label;
        }
    }
    return std::nullopt;
}

class JsonParser {
   public:
    explicit JsonParser(std::string_view src) : s_(src) {}

    std::optional<JsonValue> parse() {
        skip_ws();
        auto v = parse_value();
        if (!v.has_value()) return std::nullopt;
        skip_ws();
        if (pos_ != s_.size()) return std::nullopt;
        return v;
    }

   private:
    std::optional<JsonValue> parse_value() {
        skip_ws();
        if (pos_ >= s_.size()) return std::nullopt;
        char c = s_[pos_];
        if (c == 'n') return parse_null();
        if (c == 't' || c == 'f') return parse_bool();
        if (c == '"') return parse_string();
        if (c == '{') return parse_object();
        if (c == '[') return parse_array();
        if (c == '-' || (c >= '0' && c <= '9')) return parse_number();
        return std::nullopt;
    }

    std::optional<JsonValue> parse_null() {
        if (s_.substr(pos_, 4) != "null") return std::nullopt;
        pos_ += 4;
        return JsonValue{};
    }

    std::optional<JsonValue> parse_bool() {
        if (s_.substr(pos_, 4) == "true") {
            pos_ += 4;
            JsonValue v;
            v.type = JsonValue::Type::Bool;
            v.b = true;
            return v;
        }
        if (s_.substr(pos_, 5) == "false") {
            pos_ += 5;
            JsonValue v;
            v.type = JsonValue::Type::Bool;
            v.b = false;
            return v;
        }
        return std::nullopt;
    }

    std::optional<JsonValue> parse_string() {
        if (s_[pos_] != '"') return std::nullopt;
        ++pos_;
        std::string out;
        while (pos_ < s_.size()) {
            char c = s_[pos_++];
            if (c == '"') {
                JsonValue v;
                v.type = JsonValue::Type::String;
                v.str = std::move(out);
                return v;
            }
            if (c == '\\') {
                if (pos_ >= s_.size()) return std::nullopt;
                char esc = s_[pos_++];
                switch (esc) {
                    case '"': out.push_back('"'); break;
                    case '\\': out.push_back('\\'); break;
                    case '/': out.push_back('/'); break;
                    case 'b': out.push_back('\b'); break;
                    case 'f': out.push_back('\f'); break;
                    case 'n': out.push_back('\n'); break;
                    case 'r': out.push_back('\r'); break;
                    case 't': out.push_back('\t'); break;
                    default: return std::nullopt;
                }
            } else {
                out.push_back(c);
            }
        }
        return std::nullopt;
    }

    std::optional<JsonValue> parse_number() {
        std::size_t start = pos_;
        if (s_[pos_] == '-') ++pos_;
        while (pos_ < s_.size() && std::isdigit(static_cast<unsigned char>(s_[pos_]))) ++pos_;
        if (pos_ < s_.size() && s_[pos_] == '.') {
            ++pos_;
            while (pos_ < s_.size() && std::isdigit(static_cast<unsigned char>(s_[pos_]))) ++pos_;
        }
        if (pos_ < s_.size() && (s_[pos_] == 'e' || s_[pos_] == 'E')) {
            ++pos_;
            if (pos_ < s_.size() && (s_[pos_] == '+' || s_[pos_] == '-')) ++pos_;
            while (pos_ < s_.size() && std::isdigit(static_cast<unsigned char>(s_[pos_]))) ++pos_;
        }
        std::string_view num_sv = s_.substr(start, pos_ - start);
        double value{};
        auto res = std::from_chars(num_sv.data(), num_sv.data() + num_sv.size(), value);
        if (res.ec == std::errc::result_out_of_range) {
            value = std::numeric_limits<double>::infinity();
        } else if (res.ec != std::errc()) {
            return std::nullopt;
        }
        JsonValue v;
        v.type = JsonValue::Type::Number;
        v.number = value;
        return v;
    }

    std::optional<JsonValue> parse_object() {
        if (s_[pos_] != '{') return std::nullopt;
        ++pos_;
        JsonValue v;
        v.type = JsonValue::Type::Object;
        skip_ws();
        if (pos_ < s_.size() && s_[pos_] == '}') {
            ++pos_;
            return v;
        }
        while (true) {
            auto key = parse_string();
            if (!key.has_value() || key->type != JsonValue::Type::String) return std::nullopt;
            skip_ws();
            if (pos_ >= s_.size() || s_[pos_] != ':') return std::nullopt;
            ++pos_;
            auto val = parse_value();
            if (!val.has_value()) return std::nullopt;
            v.object.emplace_back(std::move(key->str), std::move(*val));
            skip_ws();
            if (pos_ >= s_.size()) return std::nullopt;
            if (s_[pos_] == '}') {
                ++pos_;
                break;
            }
            if (s_[pos_] != ',') return std::nullopt;
            ++pos_;
            skip_ws();
        }
        return v;
    }

    std::optional<JsonValue> parse_array() {
        if (s_[pos_] != '[') return std::nullopt;
        ++pos_;
        JsonValue v;
        v.type = JsonValue::Type::Array;
        skip_ws();
        if (pos_ < s_.size() && s_[pos_] == ']') {
            ++pos_;
            return v;
        }
        while (true) {
            auto elem = parse_value();
            if (!elem.has_value()) return std::nullopt;
            v.array.emplace_back(std::move(*elem));
            skip_ws();
            if (pos_ >= s_.size()) return std::nullopt;
            if (s_[pos_] == ']') {
                ++pos_;
                break;
            }
            if (s_[pos_] != ',') return std::nullopt;
            ++pos_;
            skip_ws();
        }
        return v;
    }

    void skip_ws() {
        while (pos_ < s_.size()) {
            char c = s_[pos_];
            if (c == ' ' || c == '\n' || c == '\r' || c == '\t') {
                ++pos_;
            } else {
                break;
            }
        }
    }

    std::string_view s_;
    std::size_t pos_{0};
};

inline bool is_relative_clean_path(const std::string& path) {
    namespace fs = std::filesystem;
    if (path.empty()) return false;
    if (!path.empty() && fs::path(path).is_absolute()) return false;
    fs::path p(path);
    for (const auto& part : p) {
        if (part == "..") return false;
    }
    return true;
}

inline LoadResult load_run_output(
    const std::string& run_id,
    const std::string& artifact_root_override = "",
    bool strict = true) {
    LoadResult result;
    if (!is_lower_hex_run_id(run_id)) {
        result.code = LoadError::RUN_ID_MISMATCH;
        result.message = "run_id format invalid";
        return result;
    }

    const std::string artifact_root =
        artifact_root_override.empty() ? run_artifact_dir(run_id) : artifact_root_override;
    const auto manifest_path = (std::filesystem::path(artifact_root) / kRunOutputFile).generic_string();

    std::ifstream in(manifest_path, std::ios::binary);
    if (!in.is_open()) {
        result.code = LoadError::MISSING_FILE;
        result.message = "run_output.json missing";
        return result;
    }
    std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());

    JsonParser parser(content);
    auto root_opt = parser.parse();
    if (!root_opt.has_value() || root_opt->type != JsonValue::Type::Object) {
        result.code = LoadError::JSON_PARSE_ERROR;
        result.message = "invalid JSON";
        return result;
    }

    const auto& root = *root_opt;
    std::map<std::string, JsonValue> fields;
    for (const auto& [k, v] : root.object) {
        if (fields.count(k)) {
            result.code = LoadError::SCHEMA_VIOLATION;
            result.message = "duplicate field";
            return result;
        }
        fields.emplace(k, v);
    }

    auto require_field = [&](const std::string& key, JsonValue::Type t) -> std::optional<JsonValue> {
        auto it = fields.find(key);
        if (it == fields.end() || it->second.type != t) return std::nullopt;
        return it->second;
    };

    auto run_id_field = require_field("run_id", JsonValue::Type::String);
    auto ok_field = require_field("ok", JsonValue::Type::Bool);
    auto label_field_it = fields.find("label");
    auto inputs_field = require_field("inputs", JsonValue::Type::Object);
    auto metrics_field = require_field("metrics", JsonValue::Type::Object);

    if (!run_id_field || !ok_field || label_field_it == fields.end() || !inputs_field || !metrics_field) {
        result.code = LoadError::SCHEMA_VIOLATION;
        result.message = "missing required fields";
        return result;
    }

    if (!is_lower_hex_run_id(run_id_field->str) || run_id_field->str != run_id) {
        result.code = LoadError::RUN_ID_MISMATCH;
        result.message = "run_id mismatch";
        return result;
    }

    const JsonValue& label_value = label_field_it->second;

    bool ok = ok_field->b;
    std::optional<v2::core::FailLabel> label;
    if (ok) {
        if (label_value.type != JsonValue::Type::Null) {
            result.code = LoadError::SCHEMA_VIOLATION;
            result.message = "label must be null when ok";
            return result;
        }
    } else {
        if (label_value.type != JsonValue::Type::String) {
            result.code = LoadError::SCHEMA_VIOLATION;
            result.message = "label must be string when !ok";
            return result;
        }
        auto fl = fail_label_from_string(label_value.str);
        if (!fl.has_value()) {
            result.code = LoadError::SCHEMA_VIOLATION;
            result.message = "invalid fail label";
            return result;
        }
        label = fl;
    }

    RunOutput out;
    out.run_id = run_id;
    out.ok = ok;
    out.label = label;
    out.inputs = *inputs_field;

    for (const auto& [k, v] : metrics_field->object) {
        if (v.type != JsonValue::Type::Number || !std::isfinite(v.number)) {
            result.code = LoadError::INVALID_METRIC;
            result.message = "metric invalid";
            return result;
        }
        out.metrics[k] = v.number;
    }

    std::string artifacts_root = artifact_root;
    std::vector<std::string> artifacts_paths;
    auto artifacts_it = fields.find("artifacts");
    if (artifacts_it != fields.end()) {
        if (artifacts_it->second.type != JsonValue::Type::Object) {
            result.code = LoadError::SCHEMA_VIOLATION;
            result.message = "artifacts must be object";
            return result;
        }
        std::map<std::string, JsonValue> art_fields;
        for (const auto& [k, v] : artifacts_it->second.object) {
            art_fields.emplace(k, v);
        }
        auto root_it = art_fields.find("root");
        if (root_it != art_fields.end()) {
            if (root_it->second.type != JsonValue::Type::String) {
                result.code = LoadError::SCHEMA_VIOLATION;
                result.message = "artifacts.root must be string";
                return result;
            }
            artifacts_root = root_it->second.str;
        }
        auto paths_it = art_fields.find("paths");
        if (paths_it != art_fields.end()) {
            if (paths_it->second.type != JsonValue::Type::Array) {
                result.code = LoadError::SCHEMA_VIOLATION;
                result.message = "artifacts.paths must be array";
                return result;
            }
            for (const auto& elem : paths_it->second.array) {
                if (elem.type != JsonValue::Type::String) {
                    result.code = LoadError::SCHEMA_VIOLATION;
                    result.message = "artifact path must be string";
                    return result;
                }
                const auto& p = elem.str;
                bool valid = is_relative_clean_path(p);
                if (!valid) {
                    if (strict) {
                        result.code = LoadError::INVALID_ARTIFACT_PATH;
                        result.message = "artifact path invalid";
                        return result;
                    }
                }
                artifacts_paths.push_back(p);
            }
        }
    }
    out.artifact_root = artifacts_root;
    out.artifact_paths = std::move(artifacts_paths);

    for (const auto& [k, _] : fields) {
        if (k != "run_id" && k != "ok" && k != "label" && k != "inputs" && k != "metrics" &&
            k != "artifacts") {
            result.code = LoadError::SCHEMA_VIOLATION;
            result.message = "unknown top-level field";
            return result;
        }
    }

    result.success = true;
    result.code = LoadError::NONE;
    result.output = std::move(out);
    return result;
}

inline bool write_run_output(
    const std::string& run_id,
    const std::string& inputs_json,
    const std::map<std::string, double>& metrics,
    bool ok,
    std::optional<v2::core::FailLabel> label = std::nullopt,
    const std::vector<std::string>& artifact_paths = {},
    const std::string& artifact_root_override = "",
    int precision = 12) {
    namespace fs = std::filesystem;

    const auto base_dir = run_artifact_dir(run_id);
    fs::create_directories(base_dir);

    const std::string artifact_root = artifact_root_override.empty() ? base_dir : artifact_root_override;
    const auto output_path = run_output_path(run_id);
    fs::path tmp_path = fs::path(output_path).concat(".tmp");

    std::ostringstream oss;
    oss.imbue(std::locale::classic());
    oss << "{\"run_id\":\"" << run_id << "\",";
    oss << "\"ok\":" << (ok ? "true" : "false") << ",";
    oss << "\"label\":";
    if (ok) {
        oss << "null";
    } else if (label.has_value()) {
        oss << "\"" << v2::core::to_string(*label) << "\"";
    } else {
        oss << "null";
    }
    oss << ",\"inputs\":" << inputs_json << ",";

    oss << "\"metrics\":{";
    bool first_metric = true;
    for (const auto& [k, v] : metrics) {
        if (!first_metric) {
            oss << ",";
        }
        first_metric = false;
        oss << "\"" << k << "\":" << format_scalar(v, precision);
    }
    oss << "},";

    oss << "\"artifacts\":{";
    oss << "\"root\":\"" << artifact_root << "\",";
    oss << "\"paths\":[";
    for (std::size_t i = 0; i < artifact_paths.size(); ++i) {
        if (i != 0) {
            oss << ",";
        }
        oss << "\"" << artifact_paths[i] << "\"";
    }
    oss << "]";
    oss << "}";

    oss << "}";

    {
        std::ofstream out(tmp_path, std::ios::binary | std::ios::trunc);
        if (!out.is_open()) {
            return false;
        }
        out << oss.str() << "\n";
    }

    fs::rename(tmp_path, output_path);
    return true;
}

}  // namespace v2::io
