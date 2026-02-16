/*
================================================================================
v2 Physics Factory — Implementation
FILE: v2/engine/src/physics/physics_factory.cpp
================================================================================
*/

#include "v2/physics/physics_factory.hpp"
#include "physics/baseline/disk_area_calculator.hpp"
#include "physics/baseline/hover_power_model.hpp"

namespace v2::physics {

// Concrete factory for baseline physics
class BaselinePhysicsFactory : public PhysicsFactory {
public:
    std::unique_ptr<DiskAreaCalculator> create_disk_area_calculator() const override {
        return std::make_unique<baseline::DiskAreaCalculator>();
    }
    
    std::unique_ptr<HoverPowerModel> create_hover_power_model() const override {
        return std::make_unique<baseline::HoverPowerModel>();
    }
};

// Static factory method
std::unique_ptr<PhysicsFactory> PhysicsFactory::create_baseline() {
    return std::make_unique<BaselinePhysicsFactory>();
}

std::unique_ptr<PhysicsFactory> PhysicsFactory::create_legacy_4_1() {
    return create_baseline();
}

} // namespace v2::physics
