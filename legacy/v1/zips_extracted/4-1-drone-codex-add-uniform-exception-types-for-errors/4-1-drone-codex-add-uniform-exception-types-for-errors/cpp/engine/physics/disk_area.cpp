#include "engine/physics/disk_area.hpp"

#include <cmath>
#include <sstream>

namespace lift {

namespace {

inline double disk_area(double radius_m) {
  return M_PI * radius_m * radius_m;
}

}  // namespace

DiskAreaResult compute_effective_disk_area(const Design& d) {
  d.validate_or_throw();

  DiskAreaResult r{};

  // Determine the effective single-disk radius:
  // - For shrouded designs, induced power area is governed by inlet area.
  // - Use shroud inner radius if provided; else rotor radius.
  const bool use_shroud = d.has_shroud && d.shroud_inner_radius_m > 0.0;
  const double effective_radius = use_shroud ? d.shroud_inner_radius_m : d.rotor_radius_m;

  if (!(effective_radius > 0.0)) {
    throw ValidationError("compute_effective_disk_area: effective_radius must be > 0");
  }

  r.A_single_m2 = disk_area(effective_radius);

  std::ostringstream notes;

  if (d.is_coaxial) {
    // Coaxial stacks share footprint: effective disks = number of distinct footprints.
    if (d.coax_pairs <= 0) {
      throw ValidationError("compute_effective_disk_area: is_coaxial true but coax_pairs <= 0");
    }
    r.effective_disk_count = d.coax_pairs;
    r.A_total_m2 = r.A_single_m2 * static_cast<double>(d.coax_pairs);
    notes << "Coaxial stacks: footprint counted per stack, not per stage; "
          << "coax_pairs=" << d.coax_pairs
          << ", effective_radius_m=" << effective_radius
          << (use_shroud ? " (shroud inlet used)" : " (rotor disk used)")
          << ".";
  } else {
    // Distributed rotors: areas add linearly.
    r.effective_disk_count = d.rotor_count;
    r.A_total_m2 = r.A_single_m2 * static_cast<double>(d.rotor_count);
    notes << "Distributed rotors: A_total = rotor_count * A_single; "
          << "effective_radius_m=" << effective_radius
          << (use_shroud ? " (shroud inlet used)" : " (rotor disk used)")
          << ".";
  }

  r.notes = notes.str();
  return r;
}

}  // namespace lift
