/*
================================================================================
v2 Physics Tests — Disk Area Calculator
FILE: v2/engine/tests/physics/disk_area_test.cpp

Purpose:
  - Verify disk area calculation through v2 interface
  - Assert deterministic outputs for fixed inputs
  - Assert non-zero, physically plausible results
  - Never reference vendor internals directly
================================================================================
*/

#include "v2/physics/physics_factory.hpp"
#include <iostream>
#include <cassert>
#include <cmath>

void test_distributed_rotors() {
    std::cout << "Test: Distributed rotors disk area..." << std::endl;
    
    auto factory = v2::physics::PhysicsFactory::create_baseline();
    auto calculator = factory->create_disk_area_calculator();
    
    v2::physics::RotorGeometry geom;
    geom.rotor_radius_m = 0.5;  // 0.5m radius
    geom.rotor_count = 4;
    geom.is_coaxial = false;
    geom.has_shroud = false;
    
    auto result = calculator->compute(geom);
    
    // Expected: A_single = π * 0.5^2 = 0.785398 m²
    // Expected: A_total = 4 * A_single = 3.14159 m²
    assert(std::fabs(result.A_single_m2 - 0.785398) < 0.001);
    assert(std::fabs(result.A_total_m2 - 3.14159) < 0.001);
    assert(result.effective_disk_count == 4);
    assert(!result.notes.empty());
    
    std::cout << "  A_single_m2: " << result.A_single_m2 << std::endl;
    std::cout << "  A_total_m2: " << result.A_total_m2 << std::endl;
    std::cout << "  effective_disk_count: " << result.effective_disk_count << std::endl;
    std::cout << "  notes: " << result.notes << std::endl;
    std::cout << "  PASS" << std::endl;
}

void test_coaxial_rotors() {
    std::cout << "Test: Coaxial rotors disk area..." << std::endl;
    
    auto factory = v2::physics::PhysicsFactory::create_baseline();
    auto calculator = factory->create_disk_area_calculator();
    
    v2::physics::RotorGeometry geom;
    geom.rotor_radius_m = 0.5;  // 0.5m radius
    geom.rotor_count = 4;       // 4 total rotors
    geom.is_coaxial = true;
    geom.coax_pairs = 2;        // 2 coaxial pairs (2 footprints)
    geom.has_shroud = false;
    
    auto result = calculator->compute(geom);
    
    // Expected: A_total = 2 * π * 0.5^2 = 1.5708 m² (only 2 footprints count)
    assert(std::fabs(result.A_single_m2 - 0.785398) < 0.001);
    assert(std::fabs(result.A_total_m2 - 1.5708) < 0.001);
    assert(result.effective_disk_count == 2);
    assert(!result.notes.empty());
    
    std::cout << "  A_single_m2: " << result.A_single_m2 << std::endl;
    std::cout << "  A_total_m2: " << result.A_total_m2 << std::endl;
    std::cout << "  effective_disk_count: " << result.effective_disk_count << std::endl;
    std::cout << "  notes: " << result.notes << std::endl;
    std::cout << "  PASS" << std::endl;
}

void test_shrouded_rotors() {
    std::cout << "Test: Shrouded rotors disk area..." << std::endl;
    
    auto factory = v2::physics::PhysicsFactory::create_baseline();
    auto calculator = factory->create_disk_area_calculator();
    
    v2::physics::RotorGeometry geom;
    geom.rotor_radius_m = 0.5;
    geom.rotor_count = 4;
    geom.is_coaxial = false;
    geom.has_shroud = true;
    geom.shroud_inner_radius_m = 0.6;  // Shroud is larger
    
    auto result = calculator->compute(geom);
    
    // Expected: A_single = π * 0.6^2 = 1.13097 m² (uses shroud radius)
    // Expected: A_total = 4 * A_single = 4.5239 m²
    assert(std::fabs(result.A_single_m2 - 1.13097) < 0.001);
    assert(std::fabs(result.A_total_m2 - 4.5239) < 0.001);
    assert(result.effective_disk_count == 4);
    assert(!result.notes.empty());
    
    std::cout << "  A_single_m2: " << result.A_single_m2 << std::endl;
    std::cout << "  A_total_m2: " << result.A_total_m2 << std::endl;
    std::cout << "  effective_disk_count: " << result.effective_disk_count << std::endl;
    std::cout << "  notes: " << result.notes << std::endl;
    std::cout << "  PASS" << std::endl;
}

int main() {
    std::cout << "=== Disk Area Calculator Tests ===" << std::endl;
    
    test_distributed_rotors();
    test_coaxial_rotors();
    test_shrouded_rotors();
    
    std::cout << "\nAll disk area tests passed!" << std::endl;
    return 0;
}
