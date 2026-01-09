#pragma once

#include "numeric.hpp"

namespace v2::core {

template <typename Tag>
class Quantity {
public:
    constexpr explicit Quantity(double v = 0.0) : value_(sanitize_nan(v)) {}

    [[nodiscard]] constexpr double value() const { return value_; }
    [[nodiscard]] constexpr bool finite() const { return is_finite(value_); }

private:
    double value_;
};

// Strong types
struct LengthTag {};
struct MassTag {};
struct TimeTag {};
struct ForceTag {};
struct PowerTag {};

using Length = Quantity<LengthTag>;
using Mass = Quantity<MassTag>;
using Time = Quantity<TimeTag>;
using Force = Quantity<ForceTag>;
using Power = Quantity<PowerTag>;

// Basic arithmetic (same dimension)
template <typename Tag>
[[nodiscard]] constexpr Quantity<Tag> operator+(Quantity<Tag> a, Quantity<Tag> b) {
    return Quantity<Tag>(a.value() + b.value());
}

template <typename Tag>
[[nodiscard]] constexpr Quantity<Tag> operator-(Quantity<Tag> a, Quantity<Tag> b) {
    return Quantity<Tag>(a.value() - b.value());
}

template <typename Tag>
[[nodiscard]] constexpr Quantity<Tag> operator*(Quantity<Tag> q, double scalar) {
    return Quantity<Tag>(q.value() * scalar);
}

template <typename Tag>
[[nodiscard]] constexpr Quantity<Tag> operator*(double scalar, Quantity<Tag> q) {
    return Quantity<Tag>(scalar * q.value());
}

template <typename Tag>
[[nodiscard]] constexpr Quantity<Tag> operator/(Quantity<Tag> q, double scalar) {
    return Quantity<Tag>(q.value() / scalar);
}

template <typename Tag>
[[nodiscard]] constexpr double operator/(Quantity<Tag> num, Quantity<Tag> den) {
    return num.value() / den.value();
}

// Comparisons (same dimension)
template <typename Tag>
[[nodiscard]] constexpr bool operator==(Quantity<Tag> a, Quantity<Tag> b) {
    return near(a.value(), b.value());
}

template <typename Tag>
[[nodiscard]] constexpr bool operator!=(Quantity<Tag> a, Quantity<Tag> b) {
    return !(a == b);
}

// Unit helpers (SI base)
[[nodiscard]] constexpr Length meters(double v) { return Length(v); }
[[nodiscard]] constexpr Mass kilograms(double v) { return Mass(v); }
[[nodiscard]] constexpr Time seconds(double v) { return Time(v); }
[[nodiscard]] constexpr Force newtons(double v) { return Force(v); }
[[nodiscard]] constexpr Power watts(double v) { return Power(v); }

}  // namespace v2::core
