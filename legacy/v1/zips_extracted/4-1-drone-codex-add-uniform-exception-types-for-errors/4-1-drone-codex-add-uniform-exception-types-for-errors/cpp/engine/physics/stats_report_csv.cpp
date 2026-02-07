// ============================================================================
// Fragment 1.4.27 — Stats Report CSV Implementation (C++)
// File: cpp/engine/physics/stats_report_csv.cpp
// ============================================================================

#include "engine/physics/stats_report_csv.hpp"

#include "engine/physics/bemt_require.hpp"

#include <ostream>
#include <string>
#include <vector>

namespace lift::bemt {

namespace {

static std::string csv_escape(const std::string& s) {
    bool need_quotes = false;
    for (char c : s) {
        if (c == ',' || c == '"' || c == '\n' || c == '\r') { need_quotes = true; break; }
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

void write_uncertainty_summary_csv(std::ostream& os, const BemtUncertaintyReport& rep) {
    rep.validate();
    os << "metric_key,units,mean,stdev,min,max,prob_meets_threshold\n";
    for (const auto& s : rep.summaries) {
        os << csv_escape(s.metric_key) << ","
           << csv_escape(s.units) << ","
           << std::to_string(s.mean) << ","
           << std::to_string(s.stdev) << ","
           << std::to_string(s.min) << ","
           << std::to_string(s.max) << ","
           << std::to_string(s.prob_meets_threshold) << "\n";
    }
}

void write_uncertainty_quantiles_csv(std::ostream& os, const BemtUncertaintyReport& rep) {
    rep.validate();
    os << "metric_key,q,value\n";
    for (const auto& s : rep.summaries) {
        // Quantile probabilities are not stored explicitly in BemtUncSummary.
        // Convention: assume default quantiles used by runner when lengths match (7).
        // If you later store explicit q-probs, update this to emit exact q values.
        const std::vector<double> default_q = {0.01,0.05,0.10,0.50,0.90,0.95,0.99};
        const auto& qvals = s.q;
        
        // Skip if no quantile values
        if (qvals.empty()) {
            continue;
        }
        
        const bool use_default = (qvals.size() == default_q.size());

        for (std::size_t i = 0; i < qvals.size(); ++i) {
            const double q = use_default ? default_q[i] : (static_cast<double>(i) / static_cast<double>(qvals.size() - 1));
            os << csv_escape(s.metric_key) << ","
               << std::to_string(q) << ","
               << std::to_string(qvals[i]) << "\n";
        }
    }
}

} // namespace lift::bemt
