/*
================================================================================
v2 Physics Tests — Hover Power Model
FILE: v2/engine/tests/physics/hover_power_test.cpp

Purpose:
  - Verify hover power computation through v2 interface
  - Assert deterministic outputs for fixed inputs
  - Assert non-zero, physically plausible results
  - Never reference vendor internals directly
================================================================================
*/

#include "v2/physics/physics_factory.hpp"
#include <iostream>
#include <cassert>
#include <cmath>

void test_hover_power_basic() {
    std::cout << "Test: Basic hover power computation..." << std::endl;
    
    auto factory = v2::physics::PhysicsFactory::create_legacy_4_1();
    auto model = factory->create_hover_power_model();
    
    v2::physics::AtmosphereConditions atmo;
    atmo.rho_kg_m3 = 1.225;  // Sea level
    
    v2::physics::RotorPerformance perf;
    perf.hover_FM = 0.75;
    perf.induced_k = 1.15;
    
    double thrust_N = 100.0;      // 100N thrust (~10kg)
    double A_total_m2 = 1.0;      // 1 m² total disk area
    
    auto result = model->compute_power(thrust_N, A_total_m2, atmo, perf);
    
    // Verify outputs are non-zero and plausible
    assert(result.thrust_N == thrust_N);
    assert(result.A_total_m2 == A_total_m2);
    assert(result.disk_loading_N_per_m2 > 0.0);
    assert(result.P_induced_ideal_W > 0.0);
    assert(result.P_induced_W > result.P_induced_ideal_W);  // induced_k > 1
    assert(result.P_total_W > result.P_induced_W);          // FM < 1
    assert(result.FM_used == 0.75);
    assert(result.rho_used_kg_m3 == 1.225);
    
    // Disk loading = thrust / area
    assert(std::fabs(result.disk_loading_N_per_m2 - 100.0) < 0.01);
    
    // Induced power should be reasonable (order of magnitude check)
    // P_i = T^(3/2) / sqrt(2*rho*A) ≈ 1000 / sqrt(2*1.225*1) ≈ 639 W
    assert(result.P_induced_ideal_W > 600.0 && result.P_induced_ideal_W < 700.0);
    
    std::cout << "  thrust_N: " << result.thrust_N << std::endl;
    std::cout << "  A_total_m2: " << result.A_total_m2 << std::endl;
    std::cout << "  disk_loading_N_per_m2: " << result.disk_loading_N_per_m2 << std::endl;
    std::cout << "  P_induced_ideal_W: " << result.P_induced_ideal_W << std::endl;
    std::cout << "  P_induced_W: " << result.P_induced_W << std::endl;
    std::cout << "  P_total_W: " << result.P_total_W << std::endl;
    std::cout << "  PASS" << std::endl;
}

void test_hover_power_sized() {
    std::cout << "Test: Sized hover power with reserve..." << std::endl;
    
    auto factory = v2::physics::PhysicsFactory::create_legacy_4_1();
    auto model = factory->create_hover_power_model();
    
    v2::physics::AtmosphereConditions atmo;
    atmo.rho_kg_m3 = 1.225;
    
    v2::physics::RotorPerformance perf;
    perf.hover_FM = 0.75;
    perf.induced_k = 1.15;
    
    double thrust_N = 100.0;
    double A_total_m2 = 1.0;
    double reserve_mult = 1.2;  // 20% reserve
    
    // Compute both unsized and sized
    auto result_unsized = model->compute_power(thrust_N, A_total_m2, atmo, perf);
    auto result_sized = model->compute_power_sized(thrust_N, A_total_m2, atmo, perf, reserve_mult);
    
    // Verify sizing multiplier applied
    assert(std::fabs(result_sized.P_total_W - result_unsized.P_total_W * 1.2) < 0.01);
    assert(std::fabs(result_sized.P_induced_W - result_unsized.P_induced_W * 1.2) < 0.01);
    assert(std::fabs(result_sized.P_induced_ideal_W - result_unsized.P_induced_ideal_W * 1.2) < 0.01);
    
    std::cout << "  P_total_W (unsized): " << result_unsized.P_total_W << std::endl;
    std::cout << "  P_total_W (sized): " << result_sized.P_total_W << std::endl;
    std::cout << "  Reserve multiplier: " << reserve_mult << std::endl;
    std::cout << "  PASS" << std::endl;
}

void test_hover_power_determinism() {
    std::cout << "Test: Deterministic hover power..." << std::endl;
    
    auto factory = v2::physics::PhysicsFactory::create_legacy_4_1();
    auto model = factory->create_hover_power_model();
    
    v2::physics::AtmosphereConditions atmo;
    atmo.rho_kg_m3 = 1.225;
    
    v2::physics::RotorPerformance perf;
    perf.hover_FM = 0.75;
    perf.induced_k = 1.15;
    
    double thrust_N = 100.0;
    double A_total_m2 = 1.0;
    
    // Compute twice with same inputs
    auto result1 = model->compute_power(thrust_N, A_total_m2, atmo, perf);
    auto result2 = model->compute_power(thrust_N, A_total_m2, atmo, perf);
    
    // Verify bit-for-bit identical
    assert(result1.P_total_W == result2.P_total_W);
    assert(result1.P_induced_W == result2.P_induced_W);
    assert(result1.P_induced_ideal_W == result2.P_induced_ideal_W);
    assert(result1.disk_loading_N_per_m2 == result2.disk_loading_N_per_m2);
    
    std::cout << "  P_total_W (run 1): " << result1.P_total_W << std::endl;
    std::cout << "  P_total_W (run 2): " << result2.P_total_W << std::endl;
    std::cout << "  PASS (deterministic)" << std::endl;
}

int main() {
    std::cout << "=== Hover Power Model Tests ===" << std::endl;
    
    test_hover_power_basic();
    test_hover_power_sized();
    test_hover_power_determinism();
    
    std::cout << "\nAll hover power tests passed!" << std::endl;
    return 0;
}
