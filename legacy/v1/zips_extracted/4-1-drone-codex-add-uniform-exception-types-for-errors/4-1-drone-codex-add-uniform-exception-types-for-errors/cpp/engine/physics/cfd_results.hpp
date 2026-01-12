#pragma once
// ============================================================================
// CFD Results Data Structures
// Fragment 1.4.24 — CFD Results Data Containers (C++)
// File: cpp/engine/physics/cfd_results.hpp
// ============================================================================
//
// Purpose:
// - Define data containers for CFD simulation results.
// - Header-only data structures for now (implementation minimal).
// - Provide stable, header-only data structures for CFD result ingestion.
// - Designed to hold rotor performance maps, flow-field snapshots, or
//   BEMT-to-CFD comparison metrics.
//
// ============================================================================

#include <string>
#include <vector>

namespace lift::cfd {

// Placeholder CFD result structures
// These would be populated by CFD analysis tools

struct CfdCase {
    std::string case_id;
    double mach = 0.0;
    double reynolds = 0.0;
    double alpha_deg = 0.0;
    double cl = 0.0;
    double cd = 0.0;
    double cm = 0.0;
};

struct CfdResults {
    std::string geometry_id;
    std::vector<CfdCase> cases;
// Simple container for CFD result metadata
struct CfdResultMeta {
    std::string case_id;
    std::string solver_version;
    double timestamp = 0.0;
    std::string notes;
};

// Placeholder for CFD rotor performance data
struct CfdRotorPerformance {
    double thrust_N = 0.0;
    double torque_Nm = 0.0;
    double power_W = 0.0;
    double rpm = 0.0;
    double pitch_deg = 0.0;
};

// Container for a CFD result case
struct CfdResult {
    CfdResultMeta meta;
    std::vector<CfdRotorPerformance> rotor_data;
    
    void validate() const {
        // Placeholder for future validation
    }
};

} // namespace lift::cfd
