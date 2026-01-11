/*
================================================================================
v2 Calibration — Types Implementation
FILE: v2/engine/src/calibration/types.cpp
================================================================================
*/

#include <v2/calibration/types.hpp>
#include <sstream>
#include <fstream>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <chrono>
#include <stdexcept>

namespace v2::calibration {

// CorrectionFactor methods
bool CorrectionFactor::is_valid() const {
    return value >= lower_bound && value <= upper_bound && 
           lower_bound < upper_bound;
}

void CorrectionFactor::clamp_to_bounds() {
    value = std::clamp(value, lower_bound, upper_bound);
}

// CalibrationState static methods
CalibrationState CalibrationState::create_uncalibrated() {
    CalibrationState state;
    state.calibration_id = "uncalibrated";
    state.version = 1;
    state.confidence = ConfidenceLevel::UNCALIBRATED;
    
    // Initialize 5 correction factors with identity values
    std::vector<std::string> param_names = {
        "motor_efficiency_multiplier",
        "profile_drag_multiplier",
        "induced_loss_factor",
        "mass_growth_factor",
        "air_density_offset"
    };
    
    for (const auto& name : param_names) {
        CorrectionFactor factor;
        factor.parameter_name = name;
        factor.value = (name == "air_density_offset") ? 0.0 : 1.0;  // offset vs multiplier
        factor.lower_bound = (name == "air_density_offset") ? -0.1 : 0.5;
        factor.upper_bound = (name == "air_density_offset") ? 0.1 : 1.5;
        factor.uncertainty = 0.0;
        factor.observation_count = 0;
        state.correction_factors.push_back(factor);
    }
    
    state.provenance.fit_method = "uncalibrated";
    state.provenance.total_observations = 0;
    state.provenance.residual_rms = 0.0;
    
    return state;
}

CalibrationState CalibrationState::create_default_bounded() {
    CalibrationState state = create_uncalibrated();
    state.calibration_id = "default_bounded";
    
    // Set conservative bounds as specified in EXECUTION_0.5
    for (auto& factor : state.correction_factors) {
        if (factor.parameter_name == "motor_efficiency_multiplier") {
            factor.lower_bound = 0.85;
            factor.upper_bound = 1.15;
        } else if (factor.parameter_name == "profile_drag_multiplier") {
            factor.lower_bound = 0.80;
            factor.upper_bound = 1.25;
        } else if (factor.parameter_name == "induced_loss_factor") {
            factor.lower_bound = 0.90;
            factor.upper_bound = 1.10;
        } else if (factor.parameter_name == "mass_growth_factor") {
            factor.lower_bound = 0.95;
            factor.upper_bound = 1.15;
        } else if (factor.parameter_name == "air_density_offset") {
            factor.lower_bound = -0.05;
            factor.upper_bound = 0.05;
        }
    }
    
    return state;
}

bool CalibrationState::is_valid() const {
    if (correction_factors.empty()) return false;
    
    for (const auto& factor : correction_factors) {
        if (!factor.is_valid()) return false;
    }
    
    return true;
}

const CorrectionFactor* CalibrationState::get_factor(const std::string& name) const {
    for (const auto& factor : correction_factors) {
        if (factor.parameter_name == name) {
            return &factor;
        }
    }
    return nullptr;
}

CorrectionFactor* CalibrationState::get_factor_mut(const std::string& name) {
    for (auto& factor : correction_factors) {
        if (factor.parameter_name == name) {
            return &factor;
        }
    }
    return nullptr;
}

std::string CalibrationState::to_json() const {
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(6);
    
    oss << "{\n";
    oss << "  \"calibration_id\": \"" << calibration_id << "\",\n";
    oss << "  \"version\": " << version << ",\n";
    oss << "  \"confidence\": \"";
    
    switch (confidence) {
        case ConfidenceLevel::HIGH: oss << "HIGH"; break;
        case ConfidenceLevel::MEDIUM: oss << "MEDIUM"; break;
        case ConfidenceLevel::LOW: oss << "LOW"; break;
        case ConfidenceLevel::UNCALIBRATED: oss << "UNCALIBRATED"; break;
    }
    oss << "\",\n";
    
    // Correction factors
    oss << "  \"correction_factors\": [\n";
    for (size_t i = 0; i < correction_factors.size(); ++i) {
        const auto& factor = correction_factors[i];
        oss << "    {\n";
        oss << "      \"parameter_name\": \"" << factor.parameter_name << "\",\n";
        oss << "      \"value\": " << factor.value << ",\n";
        oss << "      \"lower_bound\": " << factor.lower_bound << ",\n";
        oss << "      \"upper_bound\": " << factor.upper_bound << ",\n";
        oss << "      \"uncertainty\": " << factor.uncertainty << ",\n";
        oss << "      \"observation_count\": " << factor.observation_count << "\n";
        oss << "    }";
        if (i < correction_factors.size() - 1) oss << ",";
        oss << "\n";
    }
    oss << "  ],\n";
    
    // Provenance
    oss << "  \"provenance\": {\n";
    oss << "    \"creation_timestamp\": \"" << provenance.creation_timestamp << "\",\n";
    oss << "    \"git_commit_hash\": \"" << provenance.git_commit_hash << "\",\n";
    oss << "    \"data_source\": \"" << provenance.data_source << "\",\n";
    oss << "    \"fit_method\": \"" << provenance.fit_method << "\",\n";
    oss << "    \"total_observations\": " << provenance.total_observations << ",\n";
    oss << "    \"residual_rms\": " << provenance.residual_rms << "\n";
    oss << "  }\n";
    oss << "}\n";
    
    return oss.str();
}

CalibrationState CalibrationState::from_json(const std::string& json_str) {
    // Simplified JSON parsing - in production would use a proper JSON library
    // For now, return default state as placeholder
    return create_uncalibrated();
}

void CalibrationState::write_to_file(const std::string& filepath) const {
    std::ofstream file(filepath);
    if (!file.is_open()) {
        throw std::runtime_error("Failed to open file for writing: " + filepath);
    }
    file << to_json();
    file.close();
}

CalibrationState CalibrationState::load_from_file(const std::string& filepath) {
    std::ifstream file(filepath);
    if (!file.is_open()) {
        throw std::runtime_error("Failed to open file for reading: " + filepath);
    }
    
    std::string json_str((std::istreambuf_iterator<char>(file)),
                         std::istreambuf_iterator<char>());
    file.close();
    
    return from_json(json_str);
}

// CalibrationDataset methods
bool CalibrationDataset::is_valid() const {
    if (measurements.empty()) return false;
    
    // Check that all measurements have consistent keys
    if (!measurements[0].design_params.empty()) {
        const auto& first_params = measurements[0].design_params;
        for (const auto& meas : measurements) {
            if (meas.design_params.size() != first_params.size()) {
                return false;
            }
        }
    }
    
    return true;
}

// FitResult methods
bool FitResult::is_acceptable() const {
    return converged && 
           residual_rms < 0.1 &&  // Conservative threshold
           calibrated_state.is_valid();
}

} // namespace v2::calibration
