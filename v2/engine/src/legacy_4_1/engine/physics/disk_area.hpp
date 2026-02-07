#pragma once
/*
================================================================================
Legacy 4.1 — Physics: Effective Disk Area Calculator (A_total)
FILE: engine/physics/disk_area.hpp
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