#pragma once
/*
================================================================================
Fragment 1.10 — Core: Units + Conversions (Hardened)
FILE: cpp/engine/core/units.hpp

Purpose:
  - Provide explicit unit conversion helpers so physics code stays readable and
    avoids silent unit bugs (lb vs kg, ft vs m, rpm vs rad/s, etc.).
  - Centralize constants used repeatedly across hover/cruise/BEMT/etc.

Hardening:
  - Header-only constexpr constants (no runtime overhead).
  - No implicit "magic numbers" scattered through the code.
================================================================================
*/

#include <cmath>

namespace lift::units {

// Length
inline constexpr double ft_to_m = 0.3048;
inline constexpr double m_to_ft = 1.0 / ft_to_m;

inline constexpr double in_to_m = 0.0254;
inline constexpr double m_to_in = 1.0 / in_to_m;

inline constexpr double nmi_to_m = 1852.0;
inline constexpr double m_to_nmi = 1.0 / nmi_to_m;

// Mass
inline constexpr double lb_to_kg = 0.45359237;
inline constexpr double kg_to_lb = 1.0 / lb_to_kg;

// Force
inline constexpr double g0 = 9.80665; // m/s^2
inline constexpr double lbf_to_N = 4.4482216152605;
inline constexpr double N_to_lbf = 1.0 / lbf_to_N;

// Power
inline constexpr double hp_to_W = 745.69987158227022;
inline constexpr double W_to_hp = 1.0 / hp_to_W;

inline constexpr double kW_to_W = 1000.0;
inline constexpr double W_to_kW = 1.0 / kW_to_W;

// Energy
inline constexpr double Wh_to_J = 3600.0;
inline constexpr double J_to_Wh = 1.0 / Wh_to_J;

// Angle
inline constexpr double deg_to_rad = M_PI / 180.0;
inline constexpr double rad_to_deg = 180.0 / M_PI;

// Rotational speed
inline constexpr double rpm_to_rad_s = (2.0 * M_PI) / 60.0;
inline constexpr double rad_s_to_rpm = 1.0 / rpm_to_rad_s;

// Speed
inline constexpr double kts_to_m_s = 0.514444;
inline constexpr double m_s_to_kts = 1.0 / kts_to_m_s;

// Pressure / density common
inline constexpr double rho_sl = 1.225;     // kg/m^3, sea level standard
inline constexpr double a_sl   = 340.29;    // m/s, speed of sound sea level approx

// Helpers
constexpr double sqr(double x) { return x * x; }
constexpr double cube(double x) { return x * x * x; }

} // namespace lift::units

