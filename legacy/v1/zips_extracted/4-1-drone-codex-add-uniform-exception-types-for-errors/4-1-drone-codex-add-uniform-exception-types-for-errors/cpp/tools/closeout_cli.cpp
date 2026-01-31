// ============================================================================
// Fragment 1.4.28 — Closeout CLI Tool Skeleton (Hardened Args + CSV Outputs) (C++)
// File: cpp/tools/closeout_cli.cpp
// ============================================================================
//
// Purpose:
// - Tool boundary for running closeout + emitting CSV artifacts.
// - Hardened argument parsing, fail-closed behavior, explicit exit codes.
// - Minimal working skeleton that compiles even before full closeout wiring.
//   (When you wire actual CloseoutPipeline invocation, do it where indicated.)
//
// Outputs:
// - evidence CSV (optional path)
// - gates CSV (optional path)
//
// NOTE:
// - This file intentionally avoids depending on repo-specific JSON/config parsing.
//   Keep parsing in tools layer; keep engine APIs pure.
//
// ============================================================================

#include "engine/analysis/closeout_report_csv.hpp"
#include "engine/analysis/closeout_thresholds.hpp"
#include "engine/closeout/closeout_pipeline.hpp"
#include "engine/physics/bemt_require.hpp"

#include <fstream>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

namespace {

struct Args final {
    std::string out_evidence_csv;
    std::string out_gates_csv;
    bool strict = false;
    bool dry_run = false;
    bool help = false;
};

// Simple, deterministic CLI parser (no dependencies).
static Args parse_args_or_throw(int argc, char** argv) {
    Args a{};
    auto require_value = [&](int& i, const char* flag) -> std::string {
        if (i + 1 >= argc) {
            throw lift::bemt::BemtException(lift::bemt::ErrorCode::InvalidInput,
            throw lift::bemt::BemtException(lift::bemt::ErrorCode::MissingRequiredField,
                                            std::string("Missing value for ") + flag);
        }
        ++i;
        return std::string(argv[i]);
    };

    for (int i = 1; i < argc; ++i) {
        const std::string s = argv[i];

        if (s == "-h" || s == "--help") {
            a.help = true;
            continue;
        }
        if (s == "--strict") {
            a.strict = true;
            continue;
        }
        if (s == "--dry-run") {
            a.dry_run = true;
            continue;
        }
        if (s == "--out-evidence") {
            a.out_evidence_csv = require_value(i, "--out-evidence");
            continue;
        }
        if (s == "--out-gates") {
            a.out_gates_csv = require_value(i, "--out-gates");
            continue;
        }

        throw lift::bemt::BemtException(lift::bemt::ErrorCode::InvalidInput,
        throw lift::bemt::BemtException(lift::bemt::ErrorCode::MissingRequiredField,
                                        std::string("Unknown arg: ") + s);
    }

    return a;
}

static void print_usage(std::ostream& os) {
    os <<
R"(closeout_cli

Usage:
  closeout_cli [--strict] [--dry-run] [--out-evidence <path>] [--out-gates <path>]

Options:
  --strict            Use stricter default thresholds (still overrideable later).
  --dry-run           Validate configuration and write empty headers only.
  --out-evidence PATH Write evidence CSV to PATH.
  --out-gates PATH    Write gates CSV to PATH.
  -h, --help          Show this help.

Notes:
  - This tool is a boundary wrapper. It will be extended to load candidate/design
    inputs and invoke CloseoutPipeline deterministically.
)";
}

static std::ofstream open_out_or_throw(const std::string& path) {
    std::ofstream f(path, std::ios::out | std::ios::trunc);
    if (!f.is_open()) {
        throw lift::bemt::BemtException(lift::bemt::ErrorCode::IoError,
        throw lift::bemt::BemtException(lift::bemt::ErrorCode::MissingRequiredField,
                                        std::string("Failed to open output: ") + path);
    }
    return f;
}

} // namespace

int main(int argc, char** argv) {
    try {
        const Args args = parse_args_or_throw(argc, argv);
        if (args.help) {
            print_usage(std::cout);
            return 0;
        }

        // Threshold selection + validation (fail closed)
        const auto thr = args.strict
            ? lift::analysis::strict_closeout_thresholds()
            : lift::analysis::default_closeout_thresholds();

        lift::analysis::validate_closeout_thresholds_or_throw(
            thr, args.strict ? "strict_thresholds" : "default_thresholds");

        // Dry-run mode: emit CSV headers only (no engine invocation).
        if (args.dry_run) {
            if (!args.out_evidence_csv.empty()) {
                auto f = open_out_or_throw(args.out_evidence_csv);
                f << "key,value,units,source,notes\n";
            }
            if (!args.out_gates_csv.empty()) {
                auto f = open_out_or_throw(args.out_gates_csv);
                f << "id,pass,value,threshold,note\n";
            }
            return 0;
        }

        // --------------------------------------------------------------------
        // TODO (next milestone):
        // 1) Load candidate/design inputs (JSON, protobuf, etc.) in tools layer.
        // 2) Construct lift::closeout::CloseoutInput and pass thresholds.
        // 3) Invoke CloseoutPipeline to produce CloseoutOutput deterministically.
        // 4) Write CSV outputs via engine/analysis writers.
        // --------------------------------------------------------------------

        // Placeholder CloseoutOutput for now (keeps tool usable as a sanity check).
        lift::closeout::CloseoutOutput out{};
        out.gate.checks.clear();
        out.evidence.clear();
        out.validate();

        if (!args.out_evidence_csv.empty()) {
            auto f = open_out_or_throw(args.out_evidence_csv);
            lift::analysis::write_closeout_evidence_csv(f, out);
        }
        if (!args.out_gates_csv.empty()) {
            auto f = open_out_or_throw(args.out_gates_csv);
            lift::analysis::write_closeout_gates_csv(f, out);
        }

        return 0;
    } catch (const lift::bemt::BemtException& e) {
        std::cerr << "closeout_cli error: " << e.what() << "\n";
        return 2;
    } catch (const std::exception& e) {
        std::cerr << "closeout_cli fatal: " << e.what() << "\n";
        return 3;
    } catch (...) {
        std::cerr << "closeout_cli fatal: unknown exception\n";
        return 3;
    }
}
