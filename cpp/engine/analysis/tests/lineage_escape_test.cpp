// Standalone test for the json_escape_string helper used in lineage_stamper.cpp.
// This validates that canonical_inputs containing JSON quotes, backslashes,
// and control characters are properly escaped before embedding in lineage JSON.

#include <cassert>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

namespace {

// Extracted from lineage_stamper.cpp for isolated testing.
std::string json_escape_string(const std::string& s) {
    std::ostringstream o;
    for (char c : s) {
        switch (c) {
            case '\\': o << "\\\\"; break;
            case '"':  o << "\\\""; break;
            case '\b': o << "\\b";  break;
            case '\f': o << "\\f";  break;
            case '\n': o << "\\n";  break;
            case '\r': o << "\\r";  break;
            case '\t': o << "\\t";  break;
            default:
                if (static_cast<unsigned char>(c) < 0x20) {
                    o << "\\u"
                      << std::hex << std::uppercase
                      << std::setw(4) << std::setfill('0')
                      << static_cast<int>(static_cast<unsigned char>(c));
                } else {
                    o << c;
                }
        }
    }
    return o.str();
}

void test_empty() {
    assert(json_escape_string("") == "");
    std::cout << "  PASS: empty string\n";
}

void test_no_special_chars() {
    assert(json_escape_string("hello world") == "hello world");
    std::cout << "  PASS: no special characters\n";
}

void test_quotes() {
    // Input:  {"alpha":"1.0"}    (contains literal quote characters)
    // After escape each " becomes \"
    std::string input = "{\"alpha\":\"1.0\"}";
    std::string expected = "{\\\"alpha\\\":\\\"1.0\\\"}";
    std::string result = json_escape_string(input);
    assert(result == expected);
    std::cout << "  PASS: quotes escaped\n";
}

void test_backslash() {
    std::string result = json_escape_string("path\\to\\file");
    assert(result == "path\\\\to\\\\file");
    std::cout << "  PASS: backslashes escaped\n";
}

void test_control_characters() {
    std::string input = "line1\nline2\ttab";
    std::string result = json_escape_string(input);
    assert(result == "line1\\nline2\\ttab");
    std::cout << "  PASS: control characters escaped\n";
}

void test_canonical_inputs_json() {
    // This is the exact scenario from the bug report:
    // canonical_inputs produced by v2::io::canonicalize_kv returns JSON like
    // { "alpha":"1.0" } containing quotes.
    std::string canonical = R"({ "alpha":"1.0", "beta":"2.5" })";
    std::string escaped = json_escape_string(canonical);

    // The escaped result should be embeddable in a JSON string
    std::string json = "\"canonical_inputs\":\"" + escaped + "\"";

    // Verify no unescaped quotes appear inside the value
    // (skip first and last quote of the JSON string)
    std::string value_portion = json.substr(20, json.size() - 21);
    for (std::size_t i = 0; i < value_portion.size(); ++i) {
        if (value_portion[i] == '"') {
            // Must be preceded by backslash
            assert(i > 0 && value_portion[i - 1] == '\\');
        }
    }
    std::cout << "  PASS: canonical inputs with JSON content properly escaped\n";
}

void test_mixed_special() {
    std::string input = "a\"b\\c\nd\te\rf";
    std::string result = json_escape_string(input);
    assert(result == "a\\\"b\\\\c\\nd\\te\\rf");
    std::cout << "  PASS: mixed special characters\n";
}

}  // namespace

int main() {
    std::cout << "lineage_stamper json_escape_string tests:\n";
    test_empty();
    test_no_special_chars();
    test_quotes();
    test_backslash();
    test_control_characters();
    test_canonical_inputs_json();
    test_mixed_special();
    std::cout << "All tests passed.\n";
    return 0;
}
