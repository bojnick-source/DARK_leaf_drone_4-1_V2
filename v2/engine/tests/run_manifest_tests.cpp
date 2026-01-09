#include <cassert>
#include <map>
#include <string>
#include <vector>

#include "v2/io/run_manifest.hpp"

int main() {
    using v2::io::run_id_from_inputs;

    std::map<std::string, double> scalars_a{{"mass", 1.0}, {"area", 0.5}};
    std::map<std::string, double> scalars_b{{"area", 0.5}, {"mass", 1.0000000001}};
    std::map<std::string, std::vector<double>> arrays_a{{"vec", {1.0, 2.0}}};
    std::map<std::string, std::vector<double>> arrays_b{{"vec", {1.00000000001, 2.0}}};
    std::map<std::string, std::pair<double, std::string>> units_a{{"length", {1.0, "m"}}};
    std::map<std::string, std::pair<double, std::string>> units_b{{"length", {1.00000000001, "m"}}};

    const auto id1 = run_id_from_inputs(scalars_a, {}, arrays_a, units_a);
    const auto id2 = run_id_from_inputs(scalars_b, {}, arrays_b, units_b);

    // Close numeric values should canonicalize to same formatted string
    assert(id1 == id2);

    scalars_b["mass"] = 2.0;
    const auto id3 = run_id_from_inputs(scalars_b, {}, arrays_b, units_b);
    assert(id1 != id3);

    return 0;
}
