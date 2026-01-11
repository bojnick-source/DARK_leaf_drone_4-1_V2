#pragma once
/*
================================================================================
v2 Physics Factory — Instantiation Control
FILE: v2/engine/include/v2/physics/physics_factory.hpp

Purpose:
  - Centralized factory for creating physics components
  - Explicit selection of physics implementation (legacy, new, etc.)
  - No global flags, no preprocessor spaghetti
  - Auditable instantiation logic

Usage:
  auto factory = PhysicsFactory::create_legacy_4_1();
  auto disk_calc = factory->create_disk_area_calculator();
  auto hover_model = factory->create_hover_power_model();

EXTENSIBILITY:
  - To add new physics backend: add new create_XXX() method
  - To compare solvers: instantiate both and run side-by-side
  - To validate: create factory pair and assert outputs match
================================================================================
*/

#include <memory>
#include "v2/physics/interfaces/disk_area_calculator.hpp"
#include "v2/physics/interfaces/hover_power_model.hpp"

namespace v2::physics {

class PhysicsFactory {
public:
    virtual ~PhysicsFactory() = default;
    
    // Factory methods for physics components
    virtual std::unique_ptr<DiskAreaCalculator> create_disk_area_calculator() const = 0;
    virtual std::unique_ptr<HoverPowerModel> create_hover_power_model() const = 0;
    
    // Static factory methods for different implementations
    static std::unique_ptr<PhysicsFactory> create_legacy_4_1();
};

} // namespace v2::physics
