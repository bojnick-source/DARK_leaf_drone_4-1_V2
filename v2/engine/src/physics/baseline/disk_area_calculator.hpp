#pragma once
/*
================================================================================
v2 Physics Baseline — Disk Area Calculator
FILE: v2/engine/src/physics/baseline/disk_area_calculator.hpp

Purpose:
  - Baseline (non-legacy) implementation of effective disk area
  - Deterministic, explicit, and unit-safe
================================================================================
*/

#include "v2/physics/interfaces/disk_area_calculator.hpp"

namespace v2::physics::baseline {

class DiskAreaCalculator final : public v2::physics::DiskAreaCalculator {
public:
    DiskAreaResult compute(const RotorGeometry& geometry) const override;
};

} // namespace v2::physics::baseline
