#pragma once
/*
================================================================================
v2 Physics Types — Authoritative Data Structures
FILE: v2/engine/include/v2/physics/types.hpp

Purpose:
  - Define v2-owned types for physics computations
  - Provide explicit units and deterministic semantics
  - Isolate v2 from vendor type dependencies

These types define the LANGUAGE of physics for v2.
They are minimal, explicit, and unit-safe.
================================================================================
*/

#include <string>

namespace v2::physics {

// ----------------------------- Geometry Input --------------------------------

struct RotorGeometry {
    double rotor_radius_m = 0.0;
    double rotor_count = 0;
    bool is_coaxial = false;
    int coax_pairs = 0;
    
    // Shroud parameters
    bool has_shroud = false;
    double shroud_inner_radius_m = 0.0;
};

// ----------------------------- Atmosphere Input ------------------------------

struct AtmosphereConditions {
    double rho_kg_m3 = 1.225;  // Air density (standard sea level)
};

// ----------------------------- Rotor Performance Input -----------------------

struct RotorPerformance {
    double hover_FM = 0.75;        // Figure of merit (0..1]
    double induced_k = 1.15;       // Induced power multiplier [1.0..]
};

// ----------------------------- Disk Area Output ------------------------------

struct DiskAreaResult {
    double A_single_m2 = 0.0;        // Area of one rotor disk or shroud inlet
    double A_total_m2 = 0.0;         // Effective total disk area for induced power
    int effective_disk_count = 0;    // Number of independent disks contributing
    std::string notes;               // Explanation for reporting/audit
};

// ----------------------------- Hover Power Output ----------------------------

struct HoverPowerResult {
    double thrust_N = 0.0;
    double A_total_m2 = 0.0;
    double disk_loading_N_per_m2 = 0.0;
    
    double P_induced_ideal_W = 0.0;
    double P_induced_W = 0.0;      // With induced_k
    double P_total_W = 0.0;        // With FM
    
    double FM_used = 0.0;
    double rho_used_kg_m3 = 0.0;
};

} // namespace v2::physics
