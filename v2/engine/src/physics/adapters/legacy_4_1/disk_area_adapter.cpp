/*
================================================================================
Legacy 4.1 Adapter — Disk Area Calculator Implementation
FILE: v2/engine/src/physics/adapters/legacy_4_1/disk_area_adapter.cpp
================================================================================
*/

#include "disk_area_adapter.hpp"

#include <stdexcept>

namespace v2::physics::adapters {

lift::Design LegacyDiskAreaAdapter::translate_to_legacy(const RotorGeometry& geometry) const {
    if (geometry.rotor_radius_m <= 0.0) {
        throw std::invalid_argument("LegacyDiskAreaAdapter: rotor_radius_m must be > 0");
    }
    if (geometry.rotor_count <= 0) {
        throw std::invalid_argument("LegacyDiskAreaAdapter: rotor_count must be > 0");
    }
    if (geometry.is_coaxial && geometry.coax_pairs <= 0) {
        throw std::invalid_argument("LegacyDiskAreaAdapter: is_coaxial true but coax_pairs <= 0");
    }
    if (geometry.has_shroud && geometry.shroud_inner_radius_m <= 0.0) {
        throw std::invalid_argument("LegacyDiskAreaAdapter: has_shroud true but shroud_inner_radius_m <= 0");
    }

    lift::Design design;
    design.rotor_radius_m = geometry.rotor_radius_m;
    design.rotor_count = geometry.rotor_count;
    design.is_coaxial = geometry.is_coaxial;
    design.coax_pairs = geometry.coax_pairs;
    design.has_shroud = geometry.has_shroud;
    design.shroud_inner_radius_m = geometry.shroud_inner_radius_m;

    design.arch = lift::Architecture::Multicopter_Open;
    design.rotor_rpm = 1000.0;
    design.rotor_solidity = 0.1;
    design.coaxial_spacing_m = 0.2;

    design.mass.structural_kg = 1.0;

    return design;
}

DiskAreaResult LegacyDiskAreaAdapter::translate_from_legacy(
    const lift::DiskAreaResult& legacy_result) const {
    DiskAreaResult result;
    result.A_single_m2 = legacy_result.A_single_m2;
    result.A_total_m2 = legacy_result.A_total_m2;
    result.effective_disk_count = legacy_result.effective_disk_count;
    result.notes = legacy_result.notes;
    return result;
}

DiskAreaResult LegacyDiskAreaAdapter::compute(const RotorGeometry& geometry) const {
    try {
        lift::Design legacy_design = translate_to_legacy(geometry);
        lift::DiskAreaResult legacy_result = lift::compute_effective_disk_area(legacy_design);
        return translate_from_legacy(legacy_result);
    } catch (const lift::ValidationError& e) {
        throw std::invalid_argument(std::string("Legacy validation failed: ") + e.what());
    }
}

} // namespace v2::physics::adapters