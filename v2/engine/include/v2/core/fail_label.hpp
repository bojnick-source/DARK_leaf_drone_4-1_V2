#pragma once

#include <array>
#include <cstdint>
#include <string_view>

namespace v2::core {

enum class FailLabel : std::uint16_t {
    AERO_SOLIDITY_FAIL,
    AERO_TIPMACH_FAIL,
    AERO_DISK_LOADING_FAIL,
    AERO_BEMT_DIVERGENCE,
    ELEC_MOTOR_CURRENT_FAIL,
    ELEC_MOTOR_THERMAL_FAIL,
    ELEC_ESC_THERMAL_FAIL,
    ELEC_BUS_CURRENT_FAIL,
    ELEC_BATTERY_INFEASIBLE,
    ELEC_BATTERY_THERMAL_FAIL,
    ENERGY_ENDURANCE_FAIL,
    ENERGY_NEGATIVE_MARGIN,
    STRUCT_STRESS_FAIL,
    STRUCT_BUCKLING_FAIL,
    STRUCT_FATIGUE_FAIL,
    SYS_CONVERGENCE_FAIL,
    SYS_NAN_FAIL,
    SYS_INFEASIBLE
};

inline constexpr std::array<FailLabel, 18> kFailLabels = {
    FailLabel::AERO_SOLIDITY_FAIL,
    FailLabel::AERO_TIPMACH_FAIL,
    FailLabel::AERO_DISK_LOADING_FAIL,
    FailLabel::AERO_BEMT_DIVERGENCE,
    FailLabel::ELEC_MOTOR_CURRENT_FAIL,
    FailLabel::ELEC_MOTOR_THERMAL_FAIL,
    FailLabel::ELEC_ESC_THERMAL_FAIL,
    FailLabel::ELEC_BUS_CURRENT_FAIL,
    FailLabel::ELEC_BATTERY_INFEASIBLE,
    FailLabel::ELEC_BATTERY_THERMAL_FAIL,
    FailLabel::ENERGY_ENDURANCE_FAIL,
    FailLabel::ENERGY_NEGATIVE_MARGIN,
    FailLabel::STRUCT_STRESS_FAIL,
    FailLabel::STRUCT_BUCKLING_FAIL,
    FailLabel::STRUCT_FATIGUE_FAIL,
    FailLabel::SYS_CONVERGENCE_FAIL,
    FailLabel::SYS_NAN_FAIL,
    FailLabel::SYS_INFEASIBLE};

inline constexpr std::string_view to_string(FailLabel label) {
    switch (label) {
        case FailLabel::AERO_SOLIDITY_FAIL:
            return "AERO_SOLIDITY_FAIL";
        case FailLabel::AERO_TIPMACH_FAIL:
            return "AERO_TIPMACH_FAIL";
        case FailLabel::AERO_DISK_LOADING_FAIL:
            return "AERO_DISK_LOADING_FAIL";
        case FailLabel::AERO_BEMT_DIVERGENCE:
            return "AERO_BEMT_DIVERGENCE";
        case FailLabel::ELEC_MOTOR_CURRENT_FAIL:
            return "ELEC_MOTOR_CURRENT_FAIL";
        case FailLabel::ELEC_MOTOR_THERMAL_FAIL:
            return "ELEC_MOTOR_THERMAL_FAIL";
        case FailLabel::ELEC_ESC_THERMAL_FAIL:
            return "ELEC_ESC_THERMAL_FAIL";
        case FailLabel::ELEC_BUS_CURRENT_FAIL:
            return "ELEC_BUS_CURRENT_FAIL";
        case FailLabel::ELEC_BATTERY_INFEASIBLE:
            return "ELEC_BATTERY_INFEASIBLE";
        case FailLabel::ELEC_BATTERY_THERMAL_FAIL:
            return "ELEC_BATTERY_THERMAL_FAIL";
        case FailLabel::ENERGY_ENDURANCE_FAIL:
            return "ENERGY_ENDURANCE_FAIL";
        case FailLabel::ENERGY_NEGATIVE_MARGIN:
            return "ENERGY_NEGATIVE_MARGIN";
        case FailLabel::STRUCT_STRESS_FAIL:
            return "STRUCT_STRESS_FAIL";
        case FailLabel::STRUCT_BUCKLING_FAIL:
            return "STRUCT_BUCKLING_FAIL";
        case FailLabel::STRUCT_FATIGUE_FAIL:
            return "STRUCT_FATIGUE_FAIL";
        case FailLabel::SYS_CONVERGENCE_FAIL:
            return "SYS_CONVERGENCE_FAIL";
        case FailLabel::SYS_NAN_FAIL:
            return "SYS_NAN_FAIL";
        case FailLabel::SYS_INFEASIBLE:
            return "SYS_INFEASIBLE";
    }
    return "UNKNOWN_FAIL_LABEL";
}

inline constexpr bool is_valid(FailLabel label) {
    return to_string(label) != "UNKNOWN_FAIL_LABEL";
}

}  // namespace v2::core
