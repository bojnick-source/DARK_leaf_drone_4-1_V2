/*
================================================================================
v2 Physics Factory — Implementation
FILE: v2/engine/src/physics/physics_factory.cpp
================================================================================
*/

#include "v2/physics/physics_factory.hpp"
#include "physics/adapters/legacy_4_1/disk_area_adapter.hpp"
#include "physics/adapters/legacy_4_1/hover_power_adapter.hpp"

namespace v2::physics {

// Concrete factory for legacy 4.1 physics
class Legacy41PhysicsFactory : public PhysicsFactory {
public:
    std::unique_ptr<DiskAreaCalculator> create_disk_area_calculator() const override {
        return std::make_unique<adapters::LegacyDiskAreaAdapter>();
    }
    
    std::unique_ptr<HoverPowerModel> create_hover_power_model() const override {
        return std::make_unique<adapters::LegacyHoverPowerAdapter>();
    }
};

// Static factory method
std::unique_ptr<PhysicsFactory> PhysicsFactory::create_legacy_4_1() {
    return std::make_unique<Legacy41PhysicsFactory>();
}

} // namespace v2::physics
