#pragma once
/*
================================================================================
v2 Physics Interface — Disk Area Calculator
FILE: v2/engine/include/v2/physics/interfaces/disk_area_calculator.hpp

Purpose:
  - Abstract interface for computing effective actuator disk area
  - Used by momentum theory and induced power scaling
  - Enforces critical rule: coaxial rotors in SAME footprint do NOT add area

This interface defines the contract for disk area computation.
Implementations may use different models (legacy, analytical, ML-based, etc.)
================================================================================
*/

#include "v2/physics/types.hpp"

namespace v2::physics {

class DiskAreaCalculator {
public:
    virtual ~DiskAreaCalculator() = default;
    
    /**
     * Compute effective actuator disk area for a rotor configuration.
     * 
     * @param geometry Rotor geometry parameters
     * @return DiskAreaResult with A_total_m2, effective disk count, and notes
     * @throws std::invalid_argument if inputs are invalid
     */
    virtual DiskAreaResult compute(const RotorGeometry& geometry) const = 0;
};

} // namespace v2::physics
