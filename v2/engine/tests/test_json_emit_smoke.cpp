#include <cassert>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <map>
#include <string>
#include <vector>

#include "v2/io/artifacts.hpp"
#include "v2/io/json_emit.hpp"
#include "v2/io/run_id.hpp"

int main() {
    std::filesystem::remove_all("artifacts");

    std::map<std::string, double> scalars{{"alpha", 1.25}, {"beta", 2.5}};
    const auto canonical_inputs = v2::io::canonicalize_kv(scalars, 6);
    const auto run_id = v2::io::compute_run_id(canonical_inputs);
    const auto root = v2::io::artifact_root(run_id);

    v2::io::RunOutputRecord record;
    record.run_id = run_id;
    record.inputs_json = canonical_inputs;
    record.artifact_root = root.generic_string();
    record.metrics = {{"energy", 42.0}};
    record.ok = true;
    record.artifact_paths = {"out.dat"};

    const auto json = v2::io::emit_run_output_json(record, 6);
    const auto fixture = std::filesystem::path(__FILE__).parent_path() / "fixtures" / "run_output_golden.json";
    std::ifstream fixture_in(fixture, std::ios::binary);
    std::string expected((std::istreambuf_iterator<char>(fixture_in)), std::istreambuf_iterator<char>());
    if (json != expected) {
        std::cerr << "Expected fixture mismatch\n";
        std::cerr << "Fixture path: " << fixture << "\n";
        std::cerr << "Expected:\n" << expected << "\nActual:\n" << json << "\n";
        return 1;
    }

    const bool wrote = v2::io::write_run_output_file(record, 6);
    assert(wrote);
    const auto path = v2::io::run_output_path(root);
    std::ifstream in(path, std::ios::binary);
    std::string disk((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    assert(disk == json);

    std::filesystem::remove_all("artifacts");
    return 0;
}
