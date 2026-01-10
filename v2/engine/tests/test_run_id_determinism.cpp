#include <cassert>
#include <map>
#include <string>

#include "v2/io/run_id.hpp"

int main() {
    std::map<std::string, double> scalars_a{{"mass", 1.0}, {"area", 0.5}};
    std::map<std::string, double> scalars_b{{"area", 0.5}, {"mass", 1.0}};

    const auto canon_a = v2::io::canonicalize_kv(scalars_a, 6);
    const auto canon_b = v2::io::canonicalize_kv(scalars_b, 6);
    assert(canon_a == "{\"area\":\"0.500000\",\"mass\":\"1.000000\"}");
    assert(canon_b == canon_a);

    const auto id1 = v2::io::compute_run_id(canon_a);
    const auto id2 = v2::io::compute_run_id(canon_b);
    assert(id1 == id2);

    scalars_b["mass"] = 2.0;
    const auto canon_c = v2::io::canonicalize_kv(scalars_b, 6);
    const auto id3 = v2::io::compute_run_id(canon_c);
    assert(id1 != id3);

    // String canonicalization stability
    std::map<std::string, std::string> kv{{"b", "two"}, {"a", "one"}};
    const auto canon_str = v2::io::canonicalize_kv(kv);
    assert(canon_str == "{\"a\":\"one\",\"b\":\"two\"}");
    const auto id_str = v2::io::compute_run_id(canon_str);
    assert(id_str.size() == 16);
    return 0;
}
