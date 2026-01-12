// ============================================================================
// Closeout Report CSV Implementation
// File: cpp/engine/analysis/closeout_report_csv.cpp
// ============================================================================

#include "engine/analysis/closeout_report_csv.hpp"
#include "engine/closeout/closeout_pipeline.hpp"

#include <ostream>
#include <string>

namespace lift::analysis {

namespace {

static std::string csv_escape(const std::string& s) {
    bool need_quotes = false;
    for (char c : s) {
        if (c == ',' || c == '"' || c == '\n' || c == '\r') {
            need_quotes = true;
            break;
        }
    }
    if (!need_quotes) return s;

    std::string out;
    out.reserve(s.size() + 2);
    out.push_back('"');
    for (char c : s) {
        if (c == '"') out.push_back('"');
        out.push_back(c);
    }
    out.push_back('"');
    return out;
}

} // namespace

void write_closeout_evidence_csv(std::ostream& os, const lift::closeout::CloseoutOutput& out) {
    out.validate();
    os << "key,value,units,source,notes\n";
    for (const auto& e : out.evidence) {
        os << csv_escape(e.key) << ","
           << csv_escape(e.value) << ","
           << csv_escape(e.units) << ","
           << csv_escape(e.source) << ","
           << csv_escape(e.notes) << "\n";
    }
}

void write_closeout_gates_csv(std::ostream& os, const lift::closeout::CloseoutOutput& out) {
    out.validate();
    os << "id,pass,value,threshold,note\n";
    for (const auto& g : out.gate.checks) {
        os << csv_escape(g.id) << ","
           << (g.pass ? "true" : "false") << ","
           << std::to_string(g.value) << ","
           << std::to_string(g.threshold) << ","
           << csv_escape(g.note) << "\n";
    }
}

} // namespace lift::analysis
