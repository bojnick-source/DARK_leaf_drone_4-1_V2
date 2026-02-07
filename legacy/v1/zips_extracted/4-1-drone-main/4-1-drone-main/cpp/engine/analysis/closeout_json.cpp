/*
================================================================================
Fragment 2.3 — Analysis: Closeout JSON Serializer (Implementation)
FILE: cpp/engine/analysis/closeout_json.cpp
================================================================================
*/

#include "engine/analysis/closeout_json.hpp"

#include <cmath>
#include <fstream>
#include <sstream>
#include <vector>

namespace lift {

static inline bool is_set(double x) {
  return std::isfinite(x);
}

static std::string json_escape(const std::string& s) {
  std::ostringstream o;
  o << '"';
  for (char c : s) {
    switch (c) {
      case '\\': o << "\\\\"; break;
      case '"':  o << "\\\""; break;
      case '\b': o << "\\b";  break;
      case '\f': o << "\\f";  break;
      case '\n': o << "\\n";  break;
      case '\r': o << "\\r";  break;
      case '\t': o << "\\t";  break;
      default:
        if (static_cast<unsigned char>(c) < 0x20) {
          o << "\\u"
            << std::hex << std::uppercase
            << static_cast<int>(static_cast<unsigned char>(c));
        } else {
          o << c;
        }
    }
  }
  o << '"';
  return o.str();
}

struct J {
  std::ostringstream out;
  int indent = 2;
  int level = 0;

  void nl() {
    out << "\n" << std::string(level * indent, ' ');
  }

  void obj_begin() { out << "{"; level++; }
  void obj_end()   { level--; nl(); out << "}"; }

  void arr_begin() { out << "["; level++; }
  void arr_end()   { level--; nl(); out << "]"; }

  void key(const std::string& k) {
    out << json_escape(k) << ": ";
  }

  void comma() { out << ","; }

  void str(const std::string& v) { out << json_escape(v); }
  void b(bool v) { out << (v ? "true" : "false"); }
  void n_null() { out << "null"; }

  void num(double v) {
    if (!is_set(v)) { n_null(); return; }
    out.setf(std::ios::fixed);
    out.precision(6);
    out << v;
  }

  void num_i(int v) { out << v; }
};

static const char* concept_name(VariantConcept c) {
  switch (c) {
    case VariantConcept::Unknown: return "Unknown";
    case VariantConcept::Quad_OpenRotor: return "Quad_OpenRotor";
    case VariantConcept::Hex_OpenRotor: return "Hex_OpenRotor";
    case VariantConcept::Octo_OpenRotor: return "Octo_OpenRotor";
    case VariantConcept::Coaxial_Stacked: return "Coaxial_Stacked";
    case VariantConcept::Tandem_Twin: return "Tandem_Twin";
    case VariantConcept::Shrouded_Variants: return "Shrouded_Variants";
    case VariantConcept::Intermeshing_Synchropter: return "Intermeshing_Synchropter";
    case VariantConcept::Quad_With_SFCS: return "Quad_With_SFCS";
    case VariantConcept::Other: return "Other";
    default: return "Unknown";
  }
}

static const char* decision_name(GateDecision d) {
  switch (d) {
    case GateDecision::Go: return "Go";
    case GateDecision::NoGo: return "NoGo";
    case GateDecision::NeedsData: return "NeedsData";
    default: return "NeedsData";
  }
}

static void emit_mass_delta(J& j, const MassDeltaBreakdown& md) {
  j.obj_begin(); j.nl();

  j.key("baseline_aircraft_mass_kg"); j.num(md.baseline_aircraft_mass_kg); j.comma(); j.nl();
  j.key("baseline_payload_ratio"); j.num(md.baseline_payload_ratio); j.comma(); j.nl();

  j.key("items"); j.arr_begin();
  for (size_t i = 0; i < md.items.size(); ++i) {
    j.nl(); j.obj_begin(); j.nl();
    j.key("category"); j.str(md.items[i].category); j.comma(); j.nl();
    j.key("delta_mass_kg"); j.num(md.items[i].delta_mass_kg); j.comma(); j.nl();
    j.key("notes"); j.str(md.items[i].notes);
    j.obj_end();
    if (i + 1 < md.items.size()) j.comma();
  }
  j.arr_end(); j.comma(); j.nl();

  j.key("delta_mass_total_kg"); j.num(md.delta_mass_total_kg); j.comma(); j.nl();
  j.key("resulting_aircraft_mass_kg"); j.num(md.resulting_aircraft_mass_kg); j.comma(); j.nl();
  j.key("resulting_payload_ratio"); j.num(md.resulting_payload_ratio); j.comma(); j.nl();

  j.key("delta_cg_m"); j.obj_begin(); j.nl();
  j.key("x"); j.num(md.delta_cg_x_m); j.comma(); j.nl();
  j.key("y"); j.num(md.delta_cg_y_m); j.comma(); j.nl();
  j.key("z"); j.num(md.delta_cg_z_m);
  j.obj_end(); j.comma(); j.nl();

  j.key("delta_inertia_kgm2"); j.obj_begin(); j.nl();
  j.key("Ixx"); j.num(md.delta_Ixx_kgm2); j.comma(); j.nl();
  j.key("Iyy"); j.num(md.delta_Iyy_kgm2); j.comma(); j.nl();
  j.key("Izz"); j.num(md.delta_Izz_kgm2);
  j.obj_end();

  j.obj_end();
}

static void emit_disk(J& j, const DiskAreaCloseout& d) {
  j.obj_begin(); j.nl();
  j.key("A_total_m2"); j.num(d.A_total_m2); j.comma(); j.nl();
  j.key("disk_loading_N_per_m2"); j.num(d.disk_loading_N_per_m2); j.comma(); j.nl();
  j.key("P_hover_induced_W"); j.num(d.P_hover_induced_W); j.comma(); j.nl();
  j.key("P_hover_profile_W"); j.num(d.P_hover_profile_W); j.comma(); j.nl();
  j.key("P_hover_total_W"); j.num(d.P_hover_total_W); j.comma(); j.nl();
  j.key("P_sized_W"); j.num(d.P_sized_W); j.comma(); j.nl();
  j.key("FM_used"); j.num(d.FM_used); j.comma(); j.nl();
  j.key("rho_used"); j.num(d.rho_used);
  j.obj_end();
}

static void emit_parasite(J& j, const ParasiteCloseout& p) {
  j.obj_begin(); j.nl();
  j.key("P_parasite_W"); j.num(p.P_parasite_W); j.comma(); j.nl();
  j.key("delta_P_parasite_W"); j.num(p.delta_P_parasite_W); j.comma(); j.nl();
  j.key("CdS_m2"); j.num(p.CdS_m2); j.comma(); j.nl();
  j.key("delta_CdS_m2"); j.num(p.delta_CdS_m2); j.comma(); j.nl();
  j.key("V_cruise_mps"); j.num(p.V_cruise_mps);
  j.obj_end();
}

static void emit_maneuver(J& j, const ManeuverabilityCloseout& m) {
  j.obj_begin(); j.nl();

  j.key("authority"); j.obj_begin(); j.nl();
  j.key("yaw_margin_ratio"); j.num(m.authority.yaw_margin_ratio); j.comma(); j.nl();
  j.key("roll_margin_ratio"); j.num(m.authority.roll_margin_ratio); j.comma(); j.nl();
  j.key("pitch_margin_ratio"); j.num(m.authority.pitch_margin_ratio); j.comma(); j.nl();
  j.key("yaw_moment_reserve_Nm"); j.num(m.authority.yaw_moment_reserve_Nm); j.comma(); j.nl();
  j.key("roll_moment_reserve_Nm"); j.num(m.authority.roll_moment_reserve_Nm); j.comma(); j.nl();
  j.key("pitch_moment_reserve_Nm"); j.num(m.authority.pitch_moment_reserve_Nm);
  j.obj_end(); j.comma(); j.nl();

  j.key("bandwidth_hz"); j.obj_begin(); j.nl();
  j.key("roll"); j.num(m.roll_bandwidth_hz); j.comma(); j.nl();
  j.key("pitch"); j.num(m.pitch_bandwidth_hz); j.comma(); j.nl();
  j.key("yaw"); j.num(m.yaw_bandwidth_hz);
  j.obj_end(); j.comma(); j.nl();

  j.key("min_turn_radius_m"); j.num(m.min_turn_radius_m);

  j.obj_end();
}

static void emit_sync_risk(J& j, const SyncRiskCloseout& s) {
  j.obj_begin(); j.nl();
  j.key("phase_tolerance_deg"); j.num(s.phase_tolerance_deg); j.comma(); j.nl();
  j.key("estimated_latency_ms"); j.num(s.estimated_latency_ms); j.comma(); j.nl();
  j.key("worst_case_disturbance_notes"); j.str(s.worst_case_disturbance_notes); j.comma(); j.nl();
  j.key("fault_tree_notes"); j.str(s.fault_tree_notes);
  j.obj_end();
}

static void emit_structure(J& j, const StructuralCloseout& s) {
  j.obj_begin(); j.nl();
  j.key("mast_bending_margin_ratio"); j.num(s.mast_bending_margin_ratio); j.comma(); j.nl();
  j.key("gearbox_backlash_deg"); j.num(s.gearbox_backlash_deg); j.comma(); j.nl();
  j.key("gearbox_mass_kg"); j.num(s.gearbox_mass_kg); j.comma(); j.nl();
  j.key("notes"); j.str(s.notes);
  j.obj_end();
}

static void emit_mission(J& j, const MissionCloseout& m) {
  j.obj_begin(); j.nl();
  j.key("baseline_time_s"); j.num(m.baseline_time_s); j.comma(); j.nl();
  j.key("resulting_time_s"); j.num(m.resulting_time_s); j.comma(); j.nl();
  j.key("baseline_energy_Wh"); j.num(m.baseline_energy_Wh); j.comma(); j.nl();
  j.key("resulting_energy_Wh"); j.num(m.resulting_energy_Wh); j.comma(); j.nl();
  j.key("scoring_notes"); j.str(m.scoring_notes);
  j.obj_end();
}

static void emit_rules(J& j, const RulesCloseout& r) {
  j.obj_begin(); j.nl();
  j.key("ruleset_name"); j.str(r.ruleset_name); j.comma(); j.nl();
  j.key("ruleset_version"); j.str(r.ruleset_version); j.comma(); j.nl();

  j.key("clause_citations"); j.arr_begin();
  for (size_t i = 0; i < r.clause_citations.size(); ++i) {
    j.nl(); j.str(r.clause_citations[i]);
    if (i + 1 < r.clause_citations.size()) j.comma();
  }
  j.arr_end(); j.comma(); j.nl();

  j.key("notes"); j.str(r.notes);
  j.obj_end();
}

static void emit_sfcs(J& j, const SfcsIntegrationCloseout& s) {
  j.obj_begin(); j.nl();
  j.key("corridor_routing_notes"); j.str(s.corridor_routing_notes); j.comma(); j.nl();
  j.key("emi_isolation_notes"); j.str(s.emi_isolation_notes); j.comma(); j.nl();
  j.key("serviceability_notes"); j.str(s.serviceability_notes);
  j.obj_end();
}

static void emit_gates(J& j, const GoNoGoGates& g) {
  j.obj_begin(); j.nl();
  j.key("max_delta_mass_kg"); j.num(g.max_delta_mass_kg); j.comma(); j.nl();
  j.key("min_A_total_m2"); j.num(g.min_A_total_m2); j.comma(); j.nl();
  j.key("min_parasite_power_reduction_pct"); j.num(g.min_parasite_power_reduction_pct); j.comma(); j.nl();
  j.key("min_yaw_margin_ratio"); j.num(g.min_yaw_margin_ratio); j.comma(); j.nl();
  j.key("min_phase_tolerance_deg"); j.num(g.min_phase_tolerance_deg); j.comma(); j.nl();
  j.key("max_latency_ms"); j.num(g.max_latency_ms); j.comma(); j.nl();
  j.key("max_time_increase_pct"); j.num(g.max_time_increase_pct); j.comma(); j.nl();
  j.key("notes"); j.str(g.notes);
  j.obj_end();
}

static void emit_gate_result(J& j, const GateResult& g) {
  j.obj_begin(); j.nl();
  j.key("decision"); j.str(decision_name(g.decision)); j.comma(); j.nl();

  j.key("failed_gates"); j.arr_begin();
  for (size_t i = 0; i < g.failed_gates.size(); ++i) {
    j.nl(); j.str(g.failed_gates[i]);
    if (i + 1 < g.failed_gates.size()) j.comma();
  }
  j.arr_end(); j.comma(); j.nl();

  j.key("missing_data"); j.arr_begin();
  for (size_t i = 0; i < g.missing_data.size(); ++i) {
    j.nl(); j.str(g.missing_data[i]);
    if (i + 1 < g.missing_data.size()) j.comma();
  }
  j.arr_end(); j.comma(); j.nl();

  j.key("notes"); j.str(g.notes);
  j.obj_end();
}

std::string closeout_to_json(const CloseoutReport& r, int indent_spaces) {
  J j;
  j.indent = indent_spaces;
  j.level = 0;

  j.obj_begin(); j.nl();

  j.key("concept"); j.str(concept_name(r.concept)); j.comma(); j.nl();
  j.key("variant_name"); j.str(r.variant_name); j.comma(); j.nl();
  j.key("geom_hash"); j.str(r.geom_hash); j.comma(); j.nl();
  j.key("eval_hash"); j.str(r.eval_hash); j.comma(); j.nl();

  j.key("mass_delta"); emit_mass_delta(j, r.mass_delta); j.comma(); j.nl();
  j.key("disk"); emit_disk(j, r.disk); j.comma(); j.nl();
  j.key("parasite"); emit_parasite(j, r.parasite); j.comma(); j.nl();
  j.key("maneuver"); emit_maneuver(j, r.maneuver); j.comma(); j.nl();
  j.key("sync_risk"); emit_sync_risk(j, r.sync_risk); j.comma(); j.nl();
  j.key("structure"); emit_structure(j, r.structure); j.comma(); j.nl();
  j.key("mission"); emit_mission(j, r.mission); j.comma(); j.nl();
  j.key("rules"); emit_rules(j, r.rules); j.comma(); j.nl();
  j.key("sfcs"); emit_sfcs(j, r.sfcs); j.comma(); j.nl();

  j.key("gates"); emit_gates(j, r.gates); j.comma(); j.nl();
  j.key("gate_result"); emit_gate_result(j, r.gate_result);

  j.obj_end();
  j.out << "\n";
  return j.out.str();
}

bool write_closeout_json_file(const CloseoutReport& r,
                              const std::string& file_path,
                              int indent_spaces) {
  std::ofstream f(file_path, std::ios::out | std::ios::trunc);
  if (!f.is_open()) return false;
  f << closeout_to_json(r, indent_spaces);
  f.close();
  return true;
}

} // namespace lift
