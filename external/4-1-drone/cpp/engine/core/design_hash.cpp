#include "engine/core/design_hash.hpp"

#include <string_view>

namespace lift {

namespace {

inline void add_tag(Fnv1a64& h, std::string_view tag) {
  h.update_string(tag);
  h.update_u8(0x1F);
}

}  // namespace

Hash64 hash_design_schema(const Design& d) {
  d.validate_or_throw();

  Fnv1a64 h;
  add_tag(h, "DesignSchema/v1");

  // Identity & architecture
  add_tag(h, "Identity");
  h.update_string(d.name);
  h.update_enum(d.arch);

  // Rotor geometry
  add_tag(h, "RotorGeom");
  h.update_i32(d.rotor_count);
  h.update_f64(d.rotor_radius_m);
  h.update_f64(d.rotor_solidity);
  h.update_f64(d.rotor_tip_speed_mps);
  h.update_f64(d.rotor_rpm);

  // Coaxial
  add_tag(h, "Coaxial");
  h.update_bool(d.is_coaxial);
  h.update_f64(d.coaxial_spacing_m);
  h.update_i32(d.coax_pairs);

  // Shroud
  add_tag(h, "Shroud");
  h.update_bool(d.has_shroud);
  h.update_f64(d.shroud_inner_radius_m);
  h.update_f64(d.shroud_exit_area_ratio);

  // Layout nodes (if provided)
  add_tag(h, "Nodes");
  h.update_u64(static_cast<uint64_t>(d.nodes.size()));
  for (const auto& n : d.nodes) {
    h.update_f64(n.x_m);
    h.update_f64(n.y_m);
    h.update_f64(n.z_m);

    h.update_f64(n.ax);
    h.update_f64(n.ay);
    h.update_f64(n.az);

    h.update_i32(n.spin_dir);
    h.update_u8(0x1E); // per-node separator
  }

  // Mass model knobs
  add_tag(h, "MassModel");
  h.update_f64(d.mass.structural_kg);
  h.update_f64(d.mass.propulsion_kg);
  h.update_f64(d.mass.energy_kg);
  h.update_f64(d.mass.avionics_kg);
  h.update_f64(d.mass.payload_interface_kg);
  h.update_f64(d.mass.misc_kg);

  // Aero model knobs
  add_tag(h, "AeroModel");
  h.update_f64(d.aero.CdS_m2);
  h.update_f64(d.aero.lift_to_drag);

  // Power system knobs
  add_tag(h, "PowerSystem");
  h.update_f64(d.power.rotor_max_shaft_W);
  h.update_f64(d.power.rotor_cont_shaft_W);
  h.update_f64(d.power.bus_voltage_V);

  return Hash64{h.value()};
}

std::string hash_design_schema_hex(const Design& d) {
  return hash_to_hex(hash_design_schema(d));
}

}  // namespace lift
