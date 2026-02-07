#pragma once
/*
================================================================================
Fragment 1.16 — Physics: Effective Disk Area Calculator (A_total)
FILE: cpp/engine/physics/disk_area.hpp

Purpose:
  - Compute effective actuator disk area A_total used by momentum theory and
    induced power scaling.
  - Enforces the critical rule:
      * Coaxial rotors in the SAME footprint do NOT add actuator disk area.
      * Distributed rotors in DIFFERENT locations DO add area.

Inputs:
  - Design schema (rotor_count, rotor_radius, coax flags, shroud radius, etc.)

Outputs:
  - Effective A_total for hover induced power model
  - Auxiliary per-rotor area and notes for reporting

Hardening:
  - Explicit handling for:
      * open distributed
      * coax stacks
      * shrouded (area determined by shroud inlet if provided, else rotor disk)
  - Returns a struct with a traceable explanation string for CloseoutReport.

Notes:
  - This is an *effective* disk area model for induced power.
  - It does not attempt interference modeling (wake overlap losses).
    Those are handled later via induced_k or BEMT interaction corrections.
================================================================================
*/

#include <string>

#include "engine/core/design.hpp"
#include "engine/core/errors.hpp"

namespace lift {

struct DiskAreaResult {
  double A_single_m2 = 0.0;        // area of one rotor disk or shroud inlet
  double A_total_m2 = 0.0;         // effective total disk area for induced power
  int effective_disk_count = 0;    // number of independent disks contributing
  std::string notes;              // explanation for reporting/audit
};

// Compute effective disk area for a design.
DiskAreaResult compute_effective_disk_area(const Design& d);

}  // namespace lift

