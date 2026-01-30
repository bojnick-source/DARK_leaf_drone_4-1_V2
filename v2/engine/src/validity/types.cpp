/*
================================================================================
v2 Validity — Types Implementation
FILE: v2/engine/src/validity/types.cpp

This implements EXECUTION_0.6: OOD Detection + Conservative Validity Gating
================================================================================
*/

#include "v2/validity/types.hpp"
#include <sstream>
#include <fstream>
#include <iomanip>
#include <ctime>

namespace v2::validity {

// ---- OODThresholds ----

OODThresholds OODThresholds::create_default() {
    OODThresholds thresholds;
    thresholds.max_spread_ratio = 2.0;
    thresholds.max_coeff_variation = 0.5;
    thresholds.max_calibration_drift = 0.3;
    thresholds.min_sample_count = 50;
    return thresholds;
}

OODThresholds OODThresholds::create_relaxed() {
    OODThresholds thresholds;
    thresholds.max_spread_ratio = 3.0;         // More relaxed
    thresholds.max_coeff_variation = 0.75;     // More relaxed
    thresholds.max_calibration_drift = 0.5;    // More relaxed
    thresholds.min_sample_count = 30;          // Lower requirement
    return thresholds;
}

// ---- ValidityAssessment ----

std::string ValidityAssessment::to_json() const {
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(6);
    
    oss << "{\n";
    oss << "  \"run_id\": \"" << run_id << "\",\n";
    oss << "  \"seed\": " << seed << ",\n";
    oss << "  \"timestamp\": \"" << timestamp << "\",\n";
    
    // Validity state
    oss << "  \"state\": \"";
    switch (state) {
        case ValidityState::VALID:
            oss << "VALID";
            break;
        case ValidityState::LOW_CONFIDENCE:
            oss << "LOW_CONFIDENCE";
            break;
        case ValidityState::OUT_OF_DISTRIBUTION:
            oss << "OUT_OF_DISTRIBUTION";
            break;
    }
    oss << "\",\n";
    
    oss << "  \"state_rationale\": \"" << state_rationale << "\",\n";
    oss << "  \"confidence_score\": " << confidence_score << ",\n";
    
    // Summary
    oss << "  \"num_metrics_evaluated\": " << num_metrics_evaluated << ",\n";
    oss << "  \"num_metrics_flagged\": " << num_metrics_flagged << ",\n";
    
    // OOD metrics
    oss << "  \"ood_metrics\": [\n";
    for (size_t i = 0; i < ood_metrics.size(); ++i) {
        const auto& metric = ood_metrics[i];
        oss << "    {\n";
        oss << "      \"metric_name\": \"" << metric.metric_name << "\",\n";
        oss << "      \"computed_value\": " << metric.computed_value << ",\n";
        oss << "      \"threshold\": " << metric.threshold << ",\n";
        oss << "      \"flagged\": " << (metric.flagged ? "true" : "false") << ",\n";
        oss << "      \"interpretation\": \"" << metric.interpretation << "\"\n";
        oss << "    }";
        if (i < ood_metrics.size() - 1) oss << ",";
        oss << "\n";
    }
    oss << "  ],\n";
    
    // Thresholds
    oss << "  \"thresholds\": {\n";
    oss << "    \"max_spread_ratio\": " << thresholds.max_spread_ratio << ",\n";
    oss << "    \"max_coeff_variation\": " << thresholds.max_coeff_variation << ",\n";
    oss << "    \"max_calibration_drift\": " << thresholds.max_calibration_drift << ",\n";
    oss << "    \"min_sample_count\": " << thresholds.min_sample_count << "\n";
    oss << "  },\n";
    
    // Recommendations
    oss << "  \"recommendations\": [\n";
    for (size_t i = 0; i < recommendations.size(); ++i) {
        oss << "    \"" << recommendations[i] << "\"";
        if (i < recommendations.size() - 1) oss << ",";
        oss << "\n";
    }
    oss << "  ]\n";
    
    oss << "}";
    return oss.str();
}

void ValidityAssessment::write_to_file(const std::string& filepath) const {
    std::ofstream ofs(filepath);
    if (!ofs.is_open()) {
        throw std::runtime_error("Failed to open file for writing: " + filepath);
    }
    ofs << to_json();
    ofs.close();
}

} // namespace v2::validity
