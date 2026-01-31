#pragma once
// ============================================================================
// Closeout Thresholds
// File: cpp/engine/analysis/closeout_thresholds.hpp
// ============================================================================
//
// Purpose:
// - Define threshold configurations for closeout gating.
// - Provide default and strict threshold sets.
//
// ============================================================================

#include "engine/analysis/closeout_types.hpp"

#include <string>

namespace lift::analysis {

// Threshold configuration for closeout gates
struct CloseoutThresholds {
    // Mass delta threshold (kg)
    double max_delta_mass_kg = kUnset;
    
    // Disk area threshold (m^2)
    double min_disk_area_m2 = kUnset;
    
    // Power/efficiency thresholds
    double min_figure_of_merit = kUnset;
    double max_power_increase_pct = kUnset;
    
    // Maneuverability thresholds
    double min_yaw_margin_ratio = kUnset;
    double min_roll_margin_ratio = kUnset;
    double min_pitch_margin_ratio = kUnset;
    
    // Sync risk thresholds (for intermeshing)
    double min_phase_tolerance_deg = kUnset;
    double max_latency_ms = kUnset;
    
    // Mission performance threshold
    double max_time_increase_pct = kUnset;
    
    std::string notes;
};

// Factory functions for threshold presets
inline CloseoutThresholds default_closeout_thresholds() {
    CloseoutThresholds t;
    t.max_delta_mass_kg = 5.0;  // Allow up to 5kg increase
    t.min_disk_area_m2 = 0.5;   // Minimum disk area
    t.min_figure_of_merit = 0.6; // Minimum FM
    t.max_power_increase_pct = 20.0; // Max 20% power increase
    t.min_yaw_margin_ratio = 1.2;
    t.min_roll_margin_ratio = 1.2;
    t.min_pitch_margin_ratio = 1.2;
    t.min_phase_tolerance_deg = 5.0;
    t.max_latency_ms = 10.0;
    t.max_time_increase_pct = 10.0;
    t.notes = "Default thresholds";
    return t;
}

inline CloseoutThresholds strict_closeout_thresholds() {
    CloseoutThresholds t;
    t.max_delta_mass_kg = 2.0;  // Stricter mass limit
    t.min_disk_area_m2 = 0.8;   // Larger minimum disk area
    t.min_figure_of_merit = 0.7; // Higher FM requirement
    t.max_power_increase_pct = 10.0; // Max 10% power increase
    t.min_yaw_margin_ratio = 1.5;
    t.min_roll_margin_ratio = 1.5;
    t.min_pitch_margin_ratio = 1.5;
    t.min_phase_tolerance_deg = 10.0;
    t.max_latency_ms = 5.0;
    t.max_time_increase_pct = 5.0;
    t.notes = "Strict thresholds";
    return t;
}

// Validation helper
inline void validate_closeout_thresholds_or_throw(
    const CloseoutThresholds& t, 
    const std::string& context) 
{
    // Basic sanity checks
    if (is_set(t.max_delta_mass_kg) && t.max_delta_mass_kg < 0.0) {
        throw lift::ValidationError(context + ": max_delta_mass_kg cannot be negative");
    }
    if (is_set(t.min_disk_area_m2) && t.min_disk_area_m2 <= 0.0) {
        throw lift::ValidationError(context + ": min_disk_area_m2 must be positive");
    }
    // Add more validation as needed
}

} // namespace lift::analysis
