/*
================================================================================
v2 Calibration — Calibrated Evaluator Implementation
FILE: v2/engine/src/calibration/calibrated_evaluator.cpp
================================================================================
*/

#include <v2/calibration/calibrated_evaluator.hpp>
#include <algorithm>
#include <stdexcept>

namespace v2::calibration {

CalibratedEvaluator::CalibratedEvaluator(const CalibrationState& state)
    : state_(state)
{
    if (!state_.is_valid()) {
        throw std::runtime_error("Cannot create CalibratedEvaluator with invalid state");
    }
}

uncertainty::UncertaintyConfig CalibratedEvaluator::apply_calibration(
    const uncertainty::UncertaintyConfig& base_config
) const {
    // Create calibrated config by adjusting nominal values
    uncertainty::UncertaintyConfig calibrated_config = base_config;
    
    // Apply each correction factor to matching parameter
    for (auto& param : calibrated_config.parameters) {
        const CorrectionFactor* factor = state_.get_factor(param.name);
        
        if (factor != nullptr) {
            // Apply correction to nominal value
            if (param.name == "air_density_offset") {
                // Additive correction for offset
                param.nominal_value += factor->value;
            } else {
                // Multiplicative correction for multipliers
                param.nominal_value *= factor->value;
            }
            
            // Ensure result stays within parameter bounds
            param.nominal_value = std::clamp(param.nominal_value, 
                                            param.lower_bound, 
                                            param.upper_bound);
        }
    }
    
    return calibrated_config;
}

bool CalibratedEvaluator::is_calibrated() const {
    return state_.confidence != ConfidenceLevel::UNCALIBRATED;
}

} // namespace v2::calibration
