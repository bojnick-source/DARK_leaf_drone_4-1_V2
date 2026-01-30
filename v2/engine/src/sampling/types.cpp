/*
================================================================================
v2 Sampling — Types Implementation
FILE: v2/engine/src/sampling/types.cpp
================================================================================
*/

#include "v2/sampling/types.hpp"
#include <sstream>
#include <fstream>
#include <iomanip>

namespace v2::sampling {

std::string SamplingReport::to_json() const {
    std::ostringstream json;
    json << std::fixed << std::setprecision(6);
    
    json << "{\n";
    json << "  \"run_id\": \"" << run_id << "\",\n";
    json << "  \"seed\": " << seed << ",\n";
    json << "  \"policy_name\": \"" << policy_name << "\",\n";
    json << "  \"timestamp\": \"" << timestamp << "\",\n";
    json << "  \"num_evaluated_designs\": " << num_evaluated_designs << ",\n";
    
    // Evaluated design IDs
    json << "  \"evaluated_design_ids\": [";
    for (size_t i = 0; i < evaluated_design_ids.size(); ++i) {
        if (i > 0) json << ", ";
        json << "\"" << evaluated_design_ids[i] << "\"";
    }
    json << "],\n";
    
    // Proposals
    json << "  \"proposals\": [\n";
    for (size_t i = 0; i < proposals.size(); ++i) {
        const auto& prop = proposals[i];
        if (i > 0) json << ",\n";
        json << "    {\n";
        json << "      \"proposal_id\": \"" << prop.proposal_id << "\",\n";
        json << "      \"rank\": " << prop.rank << ",\n";
        json << "      \"acquisition_score\": {\n";
        json << "        \"total\": " << prop.acquisition_score.total_value << ",\n";
        json << "        \"exploration\": " << prop.acquisition_score.exploration_value << ",\n";
        json << "        \"exploitation\": " << prop.acquisition_score.exploitation_value << ",\n";
        json << "        \"boundary\": " << prop.acquisition_score.boundary_value << ",\n";
        json << "        \"strategy\": \"" << prop.acquisition_score.strategy_used << "\"\n";
        json << "      },\n";
        json << "      \"rationale\": \"" << prop.rationale << "\",\n";
        json << "      \"parent_design_id\": \"" << prop.parent_design_id << "\",\n";
        json << "      \"geometry\": {\n";
        json << "        \"rotor_radius_m\": " << prop.geometry.rotor_radius_m << ",\n";
        json << "        \"rotor_count\": " << prop.geometry.rotor_count << "\n";
        json << "      }\n";
        json << "    }";
    }
    json << "\n  ],\n";
    
    // Summary
    json << "  \"summary\": {\n";
    json << "    \"best_acquisition_value\": " << best_acquisition_value << ",\n";
    json << "    \"mean_acquisition_value\": " << mean_acquisition_value << ",\n";
    json << "    \"dominant_strategy\": \"" << dominant_strategy << "\"\n";
    json << "  }\n";
    json << "}";
    
    return json.str();
}

void SamplingReport::write_to_file(const std::string& filepath) const {
    std::ofstream file(filepath);
    if (!file.is_open()) {
        throw std::runtime_error("Failed to open file for writing: " + filepath);
    }
    file << to_json();
    file.close();
}

} // namespace v2::sampling
