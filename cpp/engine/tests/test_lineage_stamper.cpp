#include <cassert>
#include <filesystem>
#include <string>
#include <vector>

#include "analysis/lineage_stamper.hpp"
#include "v2/io/artifacts.hpp"
#include "v2/io/run_id.hpp"

using engine::analysis::LineageInput;
using engine::analysis::LineageResult;
using engine::analysis::RunContext;
using engine::analysis::stamp_lineage;

std::string canonical_inputs() {
    return v2::io::canonicalize_kv({{"alpha", 1.0}, {"beta", 2.0}});
}

int main() {
    const std::string run_id = v2::io::compute_run_id(canonical_inputs());
    const auto root = v2::io::artifact_root(run_id);
    std::filesystem::remove_all(root);

    RunContext ctx{run_id};

    LineageInput base{
        run_id,
        {"p2", "p1"},
        {"b.bin", "a.bin"},
        {"out_z", "out_a"},
        canonical_inputs(),
    };

    LineageResult first = stamp_lineage(ctx, base);
    assert(first.ok);
    assert(std::filesystem::exists(root / "lineage.json"));

    // Replay should be idempotent and produce identical JSON even with permuted inputs.
    LineageInput permuted = base;
    permuted.parent_run_ids = {"p1", "p2"};
    permuted.input_artifacts = {"a.bin", "b.bin"};
    permuted.output_artifacts = {"out_a", "out_z"};
    LineageResult second = stamp_lineage(ctx, permuted);
    assert(second.ok);
    assert(second.lineage_json == first.lineage_json);

    // Multiple parents should be sorted deterministically.
    const std::string multi_id = v2::io::compute_run_id(v2::io::canonicalize_kv({{"multi", 2.0}}));
    const auto multi_root = v2::io::artifact_root(multi_id);
    std::filesystem::remove_all(multi_root);
    LineageInput multi_parent = {
        multi_id,
        {"parent_b", "parent_a", "parent_c"},
        {"i2", "i1"},
        {"out_c", "out_b", "out_a"},
        v2::io::canonicalize_kv({{"multi", 2.0}}),
    };
    RunContext ctx_multi{multi_id};
    LineageResult multi = stamp_lineage(ctx_multi, multi_parent);
    assert(multi.ok);
    const std::string json = multi.lineage_json;
    assert(json.find("\"parents\":[\"parent_a\",\"parent_b\",\"parent_c\"]") != std::string::npos);
    assert(json.find("\"outputs\":[\"out_a\",\"out_b\",\"out_c\"]") != std::string::npos);

    // Mismatch on replay should fail.
    LineageInput changed = base;
    changed.canonical_inputs = "different";
    LineageResult first_again = stamp_lineage(ctx, base);
    assert(first_again.ok);
    LineageResult mismatch = stamp_lineage(ctx, changed);
    assert(!mismatch.ok);

    std::filesystem::remove_all(root);
    std::filesystem::remove_all(multi_root);
    return 0;
}
