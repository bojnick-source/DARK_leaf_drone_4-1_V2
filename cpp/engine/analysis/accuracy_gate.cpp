#include "accuracy_gate.hpp"

#include <charconv>
#include <cctype>
#include <map>
#include <optional>
#include <set>
#include <sstream>

#include "v2/io/run_id.hpp"

namespace engine::analysis {

namespace {

struct JsonValue {
    enum class Type { OBJECT, ARRAY, STRING, NUMBER, BOOL, NIL };
    Type type{Type::NIL};
    std::map<std::string, JsonValue> object;
    std::vector<JsonValue> array;
    std::string string;
    double number{0.0};
    bool is_integer{false};
    bool boolean{false};
};

struct Parser {
    std::string_view src;
    std::size_t pos{0};

    void skip_ws() {
        while (pos < src.size() && std::isspace(static_cast<unsigned char>(src[pos]))) ++pos;
    }

    bool consume(char c) {
        skip_ws();
        if (pos < src.size() && src[pos] == c) {
            ++pos;
            return true;
        }
        return false;
    }

    std::optional<std::string> parse_string() {
        skip_ws();
        if (pos >= src.size() || src[pos] != '"') return std::nullopt;
        ++pos;
        std::string out;
        while (pos < src.size()) {
            char c = src[pos++];
            if (c == '"') return out;
            if (c == '\\' && pos < src.size()) {
                char esc = src[pos++];
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

    std::optional<JsonValue> parse_value() {
        skip_ws();
        if (pos >= src.size()) return std::nullopt;
        char c = src[pos];
        if (c == '{') return parse_object();
        if (c == '[') return parse_array();
        if (c == '"') {
            auto s = parse_string();
            if (!s) return std::nullopt;
            JsonValue v;
            v.type = JsonValue::Type::STRING;
            v.string = std::move(*s);
            return v;
        }
        if (std::isdigit(static_cast<unsigned char>(c)) || c == '-' || c == '+') {
            return parse_number();
        }
        if (src.substr(pos, 4) == "true") {
            pos += 4;
            JsonValue v;
            v.type = JsonValue::Type::BOOL;
            v.boolean = true;
            return v;
        }
        if (src.substr(pos, 5) == "false") {
            pos += 5;
            JsonValue v;
            v.type = JsonValue::Type::BOOL;
            v.boolean = false;
            return v;
        }
        if (src.substr(pos, 4) == "null") {
            pos += 4;
            JsonValue v;
            v.type = JsonValue::Type::NIL;
            return v;
        }
        return std::nullopt;
    }

    std::optional<JsonValue> parse_number() {
        skip_ws();
        std::size_t start = pos;
        bool has_dot = false;
        while (pos < src.size()) {
            char c = src[pos];
            if (std::isdigit(static_cast<unsigned char>(c)) || c == '-' || c == '+' || c == 'e' || c == 'E') {
                if (c == '.' || c == 'e' || c == 'E') has_dot = true;
                ++pos;
            } else if (c == '.') {
                has_dot = true;
                ++pos;
            } else {
                break;
            }
        }
        std::string_view token = src.substr(start, pos - start);
        double number = 0.0;
        auto res = std::from_chars(token.data(), token.data() + token.size(), number);
        if (res.ec != std::errc()) return std::nullopt;
        JsonValue v;
        v.type = JsonValue::Type::NUMBER;
        v.number = number;
        v.is_integer = !has_dot && token.find_first_of("eE") == std::string_view::npos;
        return v;
    }

    std::optional<JsonValue> parse_array() {
        if (!consume('[')) return std::nullopt;
        JsonValue v;
        v.type = JsonValue::Type::ARRAY;
        skip_ws();
        if (consume(']')) return v;
        while (true) {
            auto maybe_val = parse_value();
            if (!maybe_val) return std::nullopt;
            v.array.emplace_back(std::move(*maybe_val));
            skip_ws();
            if (consume(']')) break;
            if (!consume(',')) return std::nullopt;
        }
        return v;
    }

    std::optional<JsonValue> parse_object() {
        if (!consume('{')) return std::nullopt;
        JsonValue v;
        v.type = JsonValue::Type::OBJECT;
        skip_ws();
        if (consume('}')) return v;
        while (true) {
            auto key = parse_string();
            if (!key) return std::nullopt;
            if (!consume(':')) return std::nullopt;
            auto maybe_val = parse_value();
            if (!maybe_val) return std::nullopt;
            v.object.emplace(std::move(*key), std::move(*maybe_val));
            skip_ws();
            if (consume('}')) break;
            if (!consume(',')) return std::nullopt;
        }
        return v;
    }
};

const JsonValue* get_path(const JsonValue& root, const std::vector<std::string>& path) {
    const JsonValue* current = &root;
    for (const auto& key : path) {
        if (current->type != JsonValue::Type::OBJECT) return nullptr;
        auto it = current->object.find(key);
        if (it == current->object.end()) return nullptr;
        current = &it->second;
    }
    return current;
}

std::string fail_code_to_string(GateFailCode code) {
    switch (code) {
        case GateFailCode::MISSING_FIELD: return "MISSING_FIELD";
        case GateFailCode::INVALID_VALUE: return "INVALID_VALUE";
        case GateFailCode::RUN_ID_MISMATCH: return "RUN_ID_MISMATCH";
        case GateFailCode::HASH_MISMATCH: return "HASH_MISMATCH";
        case GateFailCode::GCI_FAIL: return "GCI_FAIL";
        case GateFailCode::VALIDATION_FAIL: return "VALIDATION_FAIL";
    }
    return "UNKNOWN";
}

void append_reason(std::vector<GateReason>& reasons, GateFailCode code, std::string detail) {
    reasons.push_back(GateReason{code, std::move(detail)});
}

std::string serialize_value(const JsonValue& v, bool include_signature, const std::string& parent_key = "");

std::string serialize_object(const JsonValue& v, bool include_signature, const std::string& parent_key) {
    std::ostringstream oss;
    oss << "{";
    bool first = true;
    for (const auto& [k, val] : v.object) {
        if (parent_key == "signatures" && k == "evidence_hash" && !include_signature) {
            continue;
        }
        if (!first) oss << ",";
        first = false;
        oss << "\"" << k << "\":" << serialize_value(val, include_signature, k);
    }
    oss << "}";
    return oss.str();
}

std::string serialize_array(const JsonValue& v, bool include_signature) {
    std::ostringstream oss;
    oss << "[";
    for (std::size_t i = 0; i < v.array.size(); ++i) {
        if (i != 0) oss << ",";
        oss << serialize_value(v.array[i], include_signature);
    }
    oss << "]";
    return oss.str();
}

std::string serialize_value(const JsonValue& v, bool include_signature, const std::string& parent_key) {
    switch (v.type) {
        case JsonValue::Type::OBJECT: return serialize_object(v, include_signature, parent_key);
        case JsonValue::Type::ARRAY: return serialize_array(v, include_signature);
        case JsonValue::Type::STRING: {
            std::ostringstream oss;
            oss << "\"" << v.string << "\"";
            return oss.str();
        }
        case JsonValue::Type::NUMBER: {
            if (v.is_integer) {
                std::ostringstream oss;
                oss << static_cast<long long>(v.number);
                return oss.str();
            }
            return v2::io::canonical_scalar(v.number);
        }
        case JsonValue::Type::BOOL: return v.boolean ? "true" : "false";
        case JsonValue::Type::NIL: return "null";
    }
    return "null";
}

bool starts_with(std::string_view value, std::string_view prefix) {
    return value.size() >= prefix.size() && value.compare(0, prefix.size(), prefix) == 0;
}

}  // namespace

std::string evidence_payload_digest(std::string_view evidence_json) {
    Parser parser{evidence_json};
    auto parsed = parser.parse_value();
    if (!parsed) return {};
    const auto payload = serialize_value(*parsed, /*include_signature=*/false);
    return v2::io::compute_run_id(payload);
}

GateDecision accuracy_gate_evaluate(std::string_view evidence_json, const RunContext& ctx) {
    GateDecision decision;
    Parser parser{evidence_json};
    auto parsed = parser.parse_value();
    if (!parsed) {
        append_reason(decision.reasons, GateFailCode::INVALID_VALUE, "evidence_json.parse");
    } else {
        const JsonValue& root = *parsed;
        // Required strings
        const std::vector<std::string> required_strings = {"execution_spec_version", "policy_digest", "run_id",
                                                           "geometry_hash", "mesh_hash", "solver_id",
                                                           "solver_version", "dataset_id"};
        for (const auto& key : required_strings) {
            const JsonValue* node = get_path(root, {key});
            if (!node) {
                append_reason(decision.reasons, GateFailCode::MISSING_FIELD, key);
                continue;
            }
            if (node->type != JsonValue::Type::STRING || node->string.empty()) {
                append_reason(decision.reasons, GateFailCode::INVALID_VALUE, key);
            }
        }

        const JsonValue* spec = get_path(root, {"execution_spec_version"});
        if (spec && spec->type == JsonValue::Type::STRING && !starts_with(spec->string, "EXECUTION_1.")) {
            append_reason(decision.reasons, GateFailCode::INVALID_VALUE, "execution_spec_version");
        }

        const JsonValue* run_id = get_path(root, {"run_id"});
        if (run_id && run_id->type == JsonValue::Type::STRING) {
            if (run_id->string != ctx.expected_run_id) {
                append_reason(decision.reasons, GateFailCode::RUN_ID_MISMATCH, "run_id");
            }
        }

        // GCI checks
        const JsonValue* gci = get_path(root, {"gci"});
        if (!gci || gci->type != JsonValue::Type::OBJECT) {
            append_reason(decision.reasons, GateFailCode::MISSING_FIELD, "gci");
        } else {
            const JsonValue* levels = get_path(*gci, {"levels"});
            if (!levels || levels->type != JsonValue::Type::ARRAY || levels->array.empty()) {
                append_reason(decision.reasons, GateFailCode::MISSING_FIELD, "gci.levels");
            } else {
                for (std::size_t i = 0; i < levels->array.size(); ++i) {
                    const auto& item = levels->array[i];
                    if (item.type != JsonValue::Type::OBJECT) {
                        append_reason(decision.reasons, GateFailCode::INVALID_VALUE, "gci.levels[" + std::to_string(i) + "]");
                        continue;
                    }
                    const JsonValue* h = get_path(item, {"h"});
                    const JsonValue* metric = get_path(item, {"metric"});
                    if (!h || !metric) {
                        append_reason(decision.reasons, GateFailCode::MISSING_FIELD, "gci.levels[" + std::to_string(i) + "]");
                        continue;
                    }
                    if (h->type != JsonValue::Type::NUMBER || metric->type != JsonValue::Type::NUMBER) {
                        append_reason(decision.reasons, GateFailCode::INVALID_VALUE, "gci.levels[" + std::to_string(i) + "]");
                    }
                }
            }
            const JsonValue* computed = get_path(*gci, {"computed_gci"});
            const JsonValue* threshold = get_path(*gci, {"pass_threshold"});
            if (!computed) append_reason(decision.reasons, GateFailCode::MISSING_FIELD, "gci.computed_gci");
            if (!threshold) append_reason(decision.reasons, GateFailCode::MISSING_FIELD, "gci.pass_threshold");
            if (computed && threshold && computed->type == JsonValue::Type::NUMBER && threshold->type == JsonValue::Type::NUMBER) {
                if (computed->number < threshold->number) {
                    append_reason(decision.reasons, GateFailCode::GCI_FAIL, "gci.computed_gci");
                }
            }
        }

        // Validation metrics
        const JsonValue* validation = get_path(root, {"validation"});
        if (!validation || validation->type != JsonValue::Type::OBJECT) {
            append_reason(decision.reasons, GateFailCode::MISSING_FIELD, "validation.metrics");
        } else {
            const JsonValue* metrics = get_path(*validation, {"metrics"});
            if (!metrics || metrics->type != JsonValue::Type::ARRAY || metrics->array.empty()) {
                append_reason(decision.reasons, GateFailCode::MISSING_FIELD, "validation.metrics");
            } else {
                for (std::size_t i = 0; i < metrics->array.size(); ++i) {
                    const auto& item = metrics->array[i];
                    if (item.type != JsonValue::Type::OBJECT) {
                        append_reason(decision.reasons, GateFailCode::INVALID_VALUE, "validation.metrics[" + std::to_string(i) + "]");
                        continue;
                    }
                    const JsonValue* name = get_path(item, {"name"});
                    const JsonValue* value = get_path(item, {"value"});
                    const JsonValue* max_allowed = get_path(item, {"max_allowed"});
                    if (!name || !value || !max_allowed) {
                        append_reason(decision.reasons, GateFailCode::MISSING_FIELD, "validation.metrics[" + std::to_string(i) + "]");
                        continue;
                    }
                    if (name->type != JsonValue::Type::STRING || value->type != JsonValue::Type::NUMBER ||
                        max_allowed->type != JsonValue::Type::NUMBER) {
                        append_reason(decision.reasons, GateFailCode::INVALID_VALUE, "validation.metrics[" + std::to_string(i) + "]");
                        continue;
                    }
                    if (value->number > max_allowed->number) {
                        append_reason(decision.reasons, GateFailCode::VALIDATION_FAIL, name->string);
                    }
                }
            }
        }

        // Timestamp
        const JsonValue* ts = get_path(root, {"timestamps", "monotonic_clock"});
        if (!ts) {
            append_reason(decision.reasons, GateFailCode::MISSING_FIELD, "timestamps.monotonic_clock");
        } else if (ts->type != JsonValue::Type::NUMBER || (!ts->is_integer && ts->number != static_cast<long long>(ts->number))) {
            append_reason(decision.reasons, GateFailCode::INVALID_VALUE, "timestamps.monotonic_clock");
        }

        // Hash check
        const JsonValue* signatures = get_path(root, {"signatures"});
        if (!signatures || signatures->type != JsonValue::Type::OBJECT) {
            append_reason(decision.reasons, GateFailCode::MISSING_FIELD, "signatures.evidence_hash");
        } else {
            const JsonValue* evidence_hash = get_path(*signatures, {"evidence_hash"});
            if (!evidence_hash) {
                append_reason(decision.reasons, GateFailCode::MISSING_FIELD, "signatures.evidence_hash");
            } else if (evidence_hash->type != JsonValue::Type::STRING) {
                append_reason(decision.reasons, GateFailCode::INVALID_VALUE, "signatures.evidence_hash");
            } else {
                const auto expected = evidence_payload_digest(evidence_json);
                if (expected != evidence_hash->string) {
                    append_reason(decision.reasons, GateFailCode::HASH_MISMATCH, "signatures.evidence_hash");
                }
            }
        }
    }

    decision.pass = decision.reasons.empty();

    std::ostringstream audit;
    audit << "{\"pass\":" << (decision.pass ? "true" : "false") << ",\"reasons\":[";
    for (std::size_t i = 0; i < decision.reasons.size(); ++i) {
        if (i != 0) audit << ",";
        audit << "{\"code\":\"" << fail_code_to_string(decision.reasons[i].code) << "\",\"detail\":\""
              << decision.reasons[i].detail << "\"}";
    }
    audit << "]}";
    decision.audit_json = audit.str();
    return decision;
}

}  // namespace engine::analysis
