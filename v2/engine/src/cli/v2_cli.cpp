#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <map>
#include <string>
#include <vector>

#include "engine/analysis/closeout_eval.hpp"
#include "engine/analysis/closeout_json.hpp"
#include "engine/analysis/closeout_types.hpp"
#include "v2/io/artifacts.hpp"
#include "v2/io/json_emit.hpp"
#include "v2/io/run_id.hpp"

namespace {

struct Args {
    std::string canonical_input;
    std::string artifact_root;
    bool write{true};
};

Args parse_args(int argc, char** argv) {
    Args args;
    for (int i = 1; i < argc; ++i) {
        std::string_view token(argv[i]);
        if (token == "--canonical-input" && i + 1 < argc) {
            args.canonical_input = argv[++i];
        } else if (token == "--artifact-root" && i + 1 < argc) {
            args.artifact_root = argv[++i];
        } else if (token == "--no-write") {
            args.write = false;
        } else if (token == "--help") {
            std::cout << "Usage: v2_engine_cli --canonical-input \"{...}\" [--artifact-root <path>] [--no-write]\n"
                         "       v2_engine_cli legacy-closeout-demo [--output <path>]\n";
            std::exit(0);
        }
    }
    return args;
}

std::string legacy_default_out_path() {
    return "closeout.json";
}

int legacy_print_result_and_return(const lift::GateResult& gr) {
    std::cout << "GateDecision: ";
    switch (gr.decision) {
        case lift::GateDecision::Go:        std::cout << "Go"; break;
        case lift::GateDecision::NoGo:      std::cout << "NoGo"; break;
        case lift::GateDecision::NeedsData: std::cout << "NeedsData"; break;
        default:                            std::cout << "NeedsData"; break;
    }
    std::cout << "\n";
    std::cout << "Failed gates: " << gr.failed_gates.size() << "\n";
    std::cout << "Missing data: " << gr.missing_data.size() << "\n";
    if (!gr.notes.empty()) std::cout << "Notes: " << gr.notes << "\n";

    if (gr.decision == lift::GateDecision::NoGo) return 2;
    if (gr.decision == lift::GateDecision::NeedsData) return 3;
    return 0;
}

int run_legacy_closeout_demo(int argc, char** argv) {
    std::string out_path = legacy_default_out_path();
    for (int i = 1; i < argc; ++i) {
        std::string_view token(argv[i]);
        if (token == "--output" && i + 1 < argc) {
            out_path = argv[++i];
        } else if (token == "--help") {
            std::cout << "Usage: v2_engine_cli legacy-closeout-demo [--output <path>]\n";
            return 0;
        }
    }

    lift::CloseoutReport r;

    r.variant_concept = lift::VariantConcept::Quad_With_SFCS;
    r.variant_name = "v2_legacy_closeout_demo";
    r.geom_hash = "demo_geom_hash_placeholder";
    r.eval_hash = "demo_eval_hash_placeholder";

    r.gates.max_delta_mass_kg = 1.50;
    r.gates.min_A_total_m2 = 1.60;
    r.gates.min_parasite_power_reduction_pct = 5.0;
    r.gates.min_yaw_margin_ratio = 1.10;
    r.gates.max_time_increase_pct = 2.0;
    r.gates.min_phase_tolerance_deg = lift::kUnset;
    r.gates.max_latency_ms = lift::kUnset;

    r.gates.notes =
        "Demo gates. Replace with rule-driven thresholds and design targets.";

    r.mass_delta.baseline_aircraft_mass_kg = 24.95;
    r.mass_delta.baseline_payload_ratio = 4.20;

    r.mass_delta.items.push_back({"motors",  +0.40, "demo motor swap mass delta"});
    r.mass_delta.items.push_back({"escs",    +0.10, "demo esc delta"});
    r.mass_delta.items.push_back({"wiring",  +0.08, "extra harnessing"});
    r.mass_delta.items.push_back({"structure",-0.20,"removed bracketry via SFCS routing"});
    r.mass_delta.items.push_back({"cooling", +0.15, "added ducting/heat spreader"});

    r.mass_delta.delta_cg_x_m = lift::kUnset;
    r.mass_delta.delta_cg_y_m = lift::kUnset;
    r.mass_delta.delta_cg_z_m = lift::kUnset;
    r.mass_delta.delta_Ixx_kgm2 = lift::kUnset;
    r.mass_delta.delta_Iyy_kgm2 = lift::kUnset;
    r.mass_delta.delta_Izz_kgm2 = lift::kUnset;

    r.disk.A_total_m2 = 1.75;
    r.disk.disk_loading_N_per_m2 = 0.0;
    r.disk.P_hover_induced_W = lift::kUnset;
    r.disk.P_hover_profile_W = lift::kUnset;
    r.disk.P_hover_total_W = lift::kUnset;
    r.disk.P_sized_W = lift::kUnset;
    r.disk.FM_used = 0.75;
    r.disk.rho_used = 1.225;

    r.parasite.V_cruise_mps = 22.0;
    r.parasite.P_parasite_W = 3200.0;
    r.parasite.delta_P_parasite_W = -250.0;
    r.parasite.CdS_m2 = lift::kUnset;
    r.parasite.delta_CdS_m2 = lift::kUnset;

    r.maneuver.authority.yaw_margin_ratio = 1.20;
    r.maneuver.authority.roll_margin_ratio = lift::kUnset;
    r.maneuver.authority.pitch_margin_ratio = lift::kUnset;
    r.maneuver.authority.yaw_moment_reserve_Nm = lift::kUnset;
    r.maneuver.authority.roll_moment_reserve_Nm = lift::kUnset;
    r.maneuver.authority.pitch_moment_reserve_Nm = lift::kUnset;
    r.maneuver.roll_bandwidth_hz = lift::kUnset;
    r.maneuver.pitch_bandwidth_hz = lift::kUnset;
    r.maneuver.yaw_bandwidth_hz = lift::kUnset;
    r.maneuver.min_turn_radius_m = lift::kUnset;

    r.sync_risk.phase_tolerance_deg = lift::kUnset;
    r.sync_risk.estimated_latency_ms = lift::kUnset;
    r.sync_risk.worst_case_disturbance_notes = "";
    r.sync_risk.fault_tree_notes = "";

    r.structure.mast_bending_margin_ratio = lift::kUnset;
    r.structure.gearbox_backlash_deg = lift::kUnset;
    r.structure.gearbox_mass_kg = lift::kUnset;
    r.structure.notes = "";

    r.mission.baseline_time_s = 720.0;
    r.mission.resulting_time_s = 730.0;
    r.mission.baseline_energy_Wh = lift::kUnset;
    r.mission.resulting_energy_Wh = lift::kUnset;
    r.mission.scoring_notes = "Demo times only.";

    r.rules.ruleset_name = "DARPA_LIFT";
    r.rules.ruleset_version = "UNSET";
    r.rules.clause_citations.clear();
    r.rules.notes = "Populate with clause IDs once rules PDF is parsed.";

    r.sfcs.corridor_routing_notes = "Demo: corridor routing TBD.";
    r.sfcs.emi_isolation_notes = "Demo: EMI/grounding TBD.";
    r.sfcs.serviceability_notes = "Demo: serviceability TBD.";

    lift::CloseoutEvalOptions opt;
    opt.strict_missing_data = true;
    opt.require_any_gate = true;
    opt.derive_payload_mass_from_baseline_ratio = true;

    lift::finalize_and_evaluate(r, opt);

    if (!lift::write_closeout_json_file(r, out_path, 2)) {
        std::cerr << "ERROR: failed to write JSON to: " << out_path << "\n";
        return 10;
    }

    std::cout << "Wrote: " << out_path << "\n";
    return legacy_print_result_and_return(r.gate_result);
}

}  // namespace

int main(int argc, char** argv) {
    if (argc > 1) {
        std::string_view mode(argv[1]);
        if (mode == "legacy-closeout-demo") {
            return run_legacy_closeout_demo(argc - 1, argv + 1);
        }
        if (mode == "--help" || mode == "-h") {
            std::cout << "Usage: v2_engine_cli --canonical-input \"{...}\" [--artifact-root <path>] [--no-write]\n"
                         "       v2_engine_cli legacy-closeout-demo [--output <path>]\n";
            return 0;
        }
    }

    const auto args = parse_args(argc, argv);
    if (args.canonical_input.empty()) {
        std::cerr << "missing --canonical-input\n";
        return 1;
    }

    const std::string run_id = v2::io::compute_run_id(args.canonical_input);
    const auto root = args.artifact_root.empty() ? v2::io::artifact_root(run_id) : std::filesystem::path(args.artifact_root);

    v2::io::RunOutputRecord record;
    record.run_id = run_id;
    record.inputs_json = args.canonical_input;
    record.artifact_root = root.generic_string();
    record.metrics = {{"duration_ms", 0.0}};
    record.ok = true;

    const auto json = v2::io::emit_run_output_json(record, 6);
    if (args.write) {
        if (!v2::io::write_run_output_file(record, 6)) {
            std::cerr << "failed to write run_output.json\n";
            return 2;
        }
    }

    std::cout << json;
    return 0;
}
