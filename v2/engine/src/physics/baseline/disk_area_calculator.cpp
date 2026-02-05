/*
================================================================================
v2 Physics Baseline — Disk Area Calculator Implementation
FILE: v2/engine/src/physics/baseline/disk_area_calculator.cpp
================================================================================
*/

#include "physics/baseline/disk_area_calculator.hpp"

#include <cmath>
#include <sstream>
#include <stdexcept>

namespace v2::physics::baseline {

namespace {
constexpr double kPi = 3.14159265358979323846;
constexpr double kRotorCountTolerance = 1e-6;
}

DiskAreaResult DiskAreaCalculator::compute(const RotorGeometry& geometry) const {
    if (geometry.rotor_radius_m <= 0.0) {
        throw std::invalid_argument("DiskAreaCalculator: rotor_radius_m must be > 0");
    }
    if (geometry.rotor_count <= 0.0) {
        throw std::invalid_argument("DiskAreaCalculator: rotor_count must be > 0");
    }

    const double rotor_count_rounded = std::round(geometry.rotor_count);
    if (std::abs(rotor_count_rounded - geometry.rotor_count) > kRotorCountTolerance) {
        throw std::invalid_argument("DiskAreaCalculator: rotor_count must be an integer value");
    }

    const int rotor_count = static_cast<int>(rotor_count_rounded);

    int effective_disk_count = rotor_count;
    if (geometry.is_coaxial) {
        if (geometry.coax_pairs > 0) {
            effective_disk_count = geometry.coax_pairs;
        } else if (rotor_count % 2 == 0) {
            effective_disk_count = rotor_count / 2;
        } else {
            throw std::invalid_argument("DiskAreaCalculator: coaxial rotors require an even rotor_count or explicit coax_pairs");
        }
    }

    double effective_radius = geometry.rotor_radius_m;
    std::ostringstream notes;
    if (geometry.has_shroud) {
        if (geometry.shroud_inner_radius_m <= 0.0) {
            throw std::invalid_argument("DiskAreaCalculator: shroud_inner_radius_m must be > 0 when has_shroud is true");
        }
        effective_radius = geometry.shroud_inner_radius_m;
        notes << "Using shroud inlet radius for disk area.";
    } else {
        notes << "Using rotor radius for disk area.";
    }

    const double A_single = kPi * effective_radius * effective_radius;
    const double A_total = A_single * static_cast<double>(effective_disk_count);

    if (geometry.is_coaxial) {
        if (!notes.str().empty()) {
            notes << " ";
        }
        notes << "Coaxial configuration uses shared footprint count=" << effective_disk_count << ".";
    }

    DiskAreaResult result;
    result.A_single_m2 = A_single;
    result.A_total_m2 = A_total;
    result.effective_disk_count = effective_disk_count;
    result.notes = notes.str();
    return result;
}

} // namespace v2::physics::baseline
