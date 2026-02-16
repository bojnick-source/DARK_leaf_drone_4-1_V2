#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <map>
#include <string>
#include <vector>

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
            std::cout << "Usage: v2_engine_cli --canonical-input \"{...}\" [--artifact-root <path>] [--no-write]\n";
            std::exit(0);
        }
    }
    return args;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc > 1) {
        std::string_view mode(argv[1]);
        if (mode == "--help" || mode == "-h") {
            std::cout << "Usage: v2_engine_cli --canonical-input \"{...}\" [--artifact-root <path>] [--no-write]\n";
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
