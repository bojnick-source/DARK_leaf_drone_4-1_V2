#include <cassert>
#include <map>
#include <string>

#include "v2/io/run_manifest.hpp"

int main() {
    using v2::io::run_id_from_inputs;

    std::map<std::string, double> scalars_a{{"mass", 1.0}, {"area", 0.5}};
    std::map<std::string, double> scalars_b{{"area", 0.5}, {"mass", 1.0000000001}};

    const auto id1 = run_id_from_inputs(scalars_a);
    const auto id2 = run_id_from_inputs(scalars_b);

    // Close numeric values should canonicalize to same formatted string
    assert(id1 == id2);

    scalars_b["mass"] = 2.0;
    const auto id3 = run_id_from_inputs(scalars_b);
    assert(id1 != id3);

    return 0;
}
