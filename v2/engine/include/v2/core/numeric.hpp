#pragma once

#include <cmath>
#include <limits>
#include <type_traits>

namespace v2::core {

inline constexpr double kDefaultTol = 1e-9;

template <typename T>
inline constexpr bool is_finite(T value) {
    using Numeric = std::conditional_t<std::is_floating_point_v<T>, T, double>;
    return std::isfinite(static_cast<Numeric>(value));
}

template <typename T>
inline constexpr T sanitize_nan(T value, T fallback = T{0}) {
    return is_finite(value) ? value : fallback;
}

template <typename T>
inline constexpr bool near(T a, T b, T tol = static_cast<T>(kDefaultTol)) {
    return is_finite(a) && is_finite(b) && std::abs(a - b) <= tol;
}

template <typename T>
inline constexpr bool non_negative(T value, T tol = static_cast<T>(0)) {
    return is_finite(value) && value >= -tol;
}

inline constexpr double deg_to_rad(double deg) {
    constexpr double kDegToRad = 3.14159265358979323846 / 180.0;
    return sanitize_nan(deg) * kDegToRad;
}

inline constexpr double rad_to_deg(double rad) {
    constexpr double kRadToDeg = 180.0 / 3.14159265358979323846;
    return sanitize_nan(rad) * kRadToDeg;
}

}  // namespace v2::core
