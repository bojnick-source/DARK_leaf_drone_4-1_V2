#pragma once
/*
================================================================================
Legacy 4.1 Adapter — Disk Area Calculator
FILE: v2/engine/src/physics/adapters/legacy_4_1/disk_area_adapter.hpp
================================================================================
*/

#include "v2/physics/interfaces/disk_area_calculator.hpp"

// VENDOR INCLUDES (private to this adapter)
#include "engine/physics/disk_area.hpp"
#include "engine/core/design.hpp"

namespace v2::physics::adapters {

class LegacyDiskAreaAdapter final : public v2::physics::DiskAreaCalculator {
public:
    DiskAreaResult compute(const RotorGeometry& geometry) const override;

private:
    // Translate v2 types to legacy types
    lift::Design translate_to_legacy(const RotorGeometry& geometry) const;

    // Translate legacy result to v2 types
    DiskAreaResult translate_from_legacy(const lift::DiskAreaResult& legacy_result) const;
};

} // namespace v2::physics::adapters