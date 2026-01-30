/*
================================================================================
v2 Uncertainty — Types Implementation
FILE: v2/engine/src/uncertainty/types.cpp
================================================================================
*/

#include "v2/uncertainty/types.hpp"
#include <sstream>
#include <fstream>
#include <iomanip>
#include <ctime>

namespace v2::uncertainty {

void UncertaintyConfig::add_parameter(const UncertainScalar& param) {
    parameters.push_back(param);
}

UncertaintyConfig UncertaintyConfig::create_default() {
    UncertaintyConfig config;
    config.sample_count = 200;
    
    // motor_efficiency_multiplier: nominal 1.0, ±5% uncertainty
    UncertainScalar motor_eff;
    motor_eff.name = "motor_efficiency_multiplier";
    motor_eff.nominal_value = 1.0;
    motor_eff.dist_type = DistributionType::Normal;
    motor_eff.stddev = 0.02;  // ~2% standard deviation
    motor_eff.lower_bound = 0.90;
    motor_eff.upper_bound = 1.05;
    config.add_parameter(motor_eff);
    
    // profile_drag_multiplier: uncertainty in Cd0
    UncertainScalar drag_mult;
    drag_mult.name = "profile_drag_multiplier";
    drag_mult.nominal_value = 1.0;
    drag_mult.dist_type = DistributionType::Normal;
    drag_mult.stddev = 0.1;  // 10% uncertainty
    drag_mult.lower_bound = 0.8;
    drag_mult.upper_bound = 1.3;
    config.add_parameter(drag_mult);
    
    // induced_loss_factor: induced power multiplier uncertainty
    UncertainScalar induced_k;
    induced_k.name = "induced_loss_factor";
    induced_k.nominal_value = 1.15;
    induced_k.dist_type = DistributionType::Normal;
    induced_k.stddev = 0.05;
    induced_k.lower_bound = 1.05;
    induced_k.upper_bound = 1.30;
    config.add_parameter(induced_k);
    
    // mass_growth_factor: mass estimation uncertainty
    UncertainScalar mass_growth;
    mass_growth.name = "mass_growth_factor";
    mass_growth.nominal_value = 1.0;
    mass_growth.dist_type = DistributionType::Normal;
    mass_growth.stddev = 0.05;  // 5% mass uncertainty
    mass_growth.lower_bound = 0.90;
    mass_growth.upper_bound = 1.15;
    config.add_parameter(mass_growth);
    
    // air_density_offset: atmospheric uncertainty
    UncertainScalar rho_offset;
    rho_offset.name = "air_density_offset";
    rho_offset.nominal_value = 0.0;
    rho_offset.dist_type = DistributionType::Normal;
    rho_offset.stddev = 0.02;  // ±0.02 kg/m³
    rho_offset.lower_bound = -0.05;
    rho_offset.upper_bound = 0.05;
    config.add_parameter(rho_offset);
    
    return config;
}

std::string RiskReport::to_json() const {
    std::ostringstream json;
    json << std::fixed << std::setprecision(6);
    
    json << "{\n";
    json << "  \"run_id\": \"" << run_id << "\",\n";
    json << "  \"seed\": " << seed << ",\n";
    json << "  \"sample_count\": " << sample_count << ",\n";
    json << "  \"timestamp\": \"" << timestamp << "\",\n";
    
    // Distributions used
    json << "  \"distributions_used\": [\n";
    for (size_t i = 0; i < distributions_used.size(); ++i) {
        const auto& dist = distributions_used[i];
        if (i > 0) json << ",\n";
        json << "    {\n";
        json << "      \"name\": \"" << dist.name << "\",\n";
        json << "      \"nominal_value\": " << dist.nominal_value << ",\n";
        json << "      \"stddev\": " << dist.stddev << ",\n";
        json << "      \"lower_bound\": " << dist.lower_bound << ",\n";
        json << "      \"upper_bound\": " << dist.upper_bound << "\n";
        json << "    }";
    }
    json << "\n  ],\n";
    
    // Output results
    json << "  \"output_results\": [\n";
    for (size_t i = 0; i < output_results.size(); ++i) {
        const auto& result = output_results[i];
        if (i > 0) json << ",\n";
        json << "    {\n";
        json << "      \"output_name\": \"" << result.output_name << "\",\n";
        json << "      \"nominal\": " << result.nominal_value << ",\n";
        json << "      \"mean\": " << result.mean_value << ",\n";
        json << "      \"stddev\": " << result.stddev_value << ",\n";
        json << "      \"p5\": " << result.p5_value << ",\n";
        json << "      \"p50\": " << result.p50_value << ",\n";
        json << "      \"p90\": " << result.p90_value << ",\n";
        json << "      \"p95\": " << result.p95_value << "\n";
        json << "    }";
    }
    json << "\n  ],\n";
    
    // Constraint risks
    json << "  \"constraint_risks\": [\n";
    for (size_t i = 0; i < constraint_risks.size(); ++i) {
        const auto& risk = constraint_risks[i];
        if (i > 0) json << ",\n";
        json << "    {\n";
        json << "      \"constraint\": \"" << risk.constraint_name << "\",\n";
        json << "      \"nominal\": " << risk.nominal_value << ",\n";
        json << "      \"p50\": " << risk.p50_value << ",\n";
        json << "      \"p90\": " << risk.p90_value << ",\n";
        json << "      \"violation_probability\": " << risk.violation_probability << ",\n";
        json << "      \"threshold\": " << risk.threshold << "\n";
        json << "    }";
    }
    json << "\n  ],\n";
    
    // Sensitivity ranking
    json << "  \"sensitivity_ranking\": [\n";
    for (size_t i = 0; i < sensitivity_ranking.size(); ++i) {
        const auto& sens = sensitivity_ranking[i];
        if (i > 0) json << ",\n";
        json << "    {\n";
        json << "      \"parameter\": \"" << sens.parameter_name << "\",\n";
        json << "      \"contribution\": " << sens.contribution << ",\n";
        json << "      \"rank\": " << sens.rank << "\n";
        json << "    }";
    }
    json << "\n  ]\n";
    json << "}";
    
    return json.str();
}

void RiskReport::write_to_file(const std::string& filepath) const {
    std::ofstream file(filepath);
    if (!file.is_open()) {
        throw std::runtime_error("Failed to open file for writing: " + filepath);
    }
    file << to_json();
    file.close();
}

} // namespace v2::uncertainty
