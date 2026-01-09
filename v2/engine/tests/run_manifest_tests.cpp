#include <cassert>
#include <filesystem>
#include <fstream>
#include <map>
#include <string>
#include <vector>

#include "v2/io/run_manifest.hpp"

int main() {
    using v2::io::run_id_from_inputs;
    using v2::io::write_run_output;
    using v2::io::load_run_output;
    using v2::io::LoadError;

    std::map<std::string, double> scalars_a{{"mass", 1.0}, {"area", 0.5}};
    std::map<std::string, double> scalars_b{{"area", 0.5}, {"mass", 1.0}};
    std::map<std::string, std::vector<double>> arrays_a{{"vec", {1.0, 2.0}}};
    std::map<std::string, std::vector<double>> arrays_b{{"vec", {1.0, 2.0}}};
    std::map<std::string, std::pair<double, std::string>> units_a{{"length", {1.0, "m"}}};
    std::map<std::string, std::pair<double, std::string>> units_b{{"length", {1.0, "m"}}};

    const auto id1 = run_id_from_inputs(scalars_a, {}, arrays_a, units_a);
    const auto id2 = run_id_from_inputs(scalars_b, {}, arrays_b, units_b);

    // Close numeric values should canonicalize to same formatted string
    assert(id1 == id2);

    scalars_b["mass"] = 2.0;
    const auto id3 = run_id_from_inputs(scalars_b, {}, arrays_b, units_b);
    assert(id1 != id3);

    // IO.0.3: write run_output.json deterministically
    const auto inputs_json = v2::io::canonicalize_inputs(scalars_a, {}, arrays_a, units_a);
    std::map<std::string, double> metrics{{"energy", 42.5}};
    std::vector<std::string> paths{"extra.dat"};
    const auto run_dir = std::filesystem::path("artifacts") / "runs" / id1;
    const auto output_path = run_dir / "run_output.json";

    std::filesystem::remove_all("artifacts");
    const bool wrote = v2::io::write_run_output(id1, inputs_json, metrics, true, std::nullopt, paths);
    assert(wrote);

    std::ifstream in(output_path, std::ios::binary);
    assert(in.is_open());
    std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());

    const std::string expected = std::string("{\"run_id\":\"") + id1 +
        "\",\"ok\":true,\"label\":null,\"inputs\":" + inputs_json +
        ",\"metrics\":{\"energy\":" + v2::io::format_scalar(42.5) +
        "},\"artifacts\":{\"root\":\"artifacts/runs/" + id1 +
        "\",\"paths\":[\"extra.dat\"]}}\n";
    assert(content == expected);

    std::filesystem::remove_all("artifacts");

    // IO.0.4: happy load
    {
        std::filesystem::remove_all("artifacts");
        const auto inputs_json = v2::io::canonicalize_inputs(scalars_a, {}, arrays_a, units_a);
        std::map<std::string, double> metrics{{"energy", 10.0}};
        std::vector<std::string> paths{"file.dat"};
        const bool ok = write_run_output(id1, inputs_json, metrics, true, std::nullopt, paths);
        assert(ok);
        auto res = load_run_output(id1);
        assert(res.success);
        assert(res.code == LoadError::NONE);
        assert(res.output.run_id == id1);
        assert(res.output.ok);
        assert(res.output.metrics.at("energy") == 10.0);
        assert(res.output.artifact_paths.size() == 1 && res.output.artifact_paths[0] == "file.dat");
    }

    // IO.0.4: run_id mismatch between dir and JSON
    {
        std::filesystem::remove_all("artifacts");
        const std::string dir_id = "aaaaaaaaaaaaaaaa";
        const std::string json_id = "bbbbbbbbbbbbbbbb";
        std::filesystem::create_directories(std::filesystem::path("artifacts") / "runs" / dir_id);
        std::ofstream out(std::filesystem::path("artifacts") / "runs" / dir_id / "run_output.json");
        out << "{\"run_id\":\"" << json_id
            << "\",\"ok\":true,\"label\":null,\"inputs\":{},\"metrics\":{},\"artifacts\":{\"root\":\"artifacts/runs/"
            << dir_id << "\",\"paths\":[]}}\n";
        out.close();
        auto res = load_run_output(dir_id);
        assert(!res.success);
        assert(res.code == LoadError::RUN_ID_MISMATCH);
    }

    // IO.0.4: invalid label when ok==false
    {
        std::filesystem::remove_all("artifacts");
        const std::string rid = "cccccccccccccccc";
        std::filesystem::create_directories(std::filesystem::path("artifacts") / "runs" / rid);
        std::ofstream out(std::filesystem::path("artifacts") / "runs" / rid / "run_output.json");
        out << "{\"run_id\":\"" << rid
            << "\",\"ok\":false,\"label\":\"BAD_LABEL\",\"inputs\":{},\"metrics\":{},\"artifacts\":{\"root\":\"artifacts/runs/"
            << rid << "\",\"paths\":[]}}\n";
        out.close();
        auto res = load_run_output(rid);
        assert(!res.success);
        assert(res.code == LoadError::SCHEMA_VIOLATION);
    }

    // IO.0.4: reject non-finite metric
    {
        std::filesystem::remove_all("artifacts");
        const std::string rid = "dddddddddddddddd";
        std::filesystem::create_directories(std::filesystem::path("artifacts") / "runs" / rid);
        std::ofstream out(std::filesystem::path("artifacts") / "runs" / rid / "run_output.json");
        out << "{\"run_id\":\"" << rid
            << "\",\"ok\":true,\"label\":null,\"inputs\":{},\"metrics\":{\"energy\":1e309},\"artifacts\":{\"root\":\"artifacts/runs/"
            << rid << "\",\"paths\":[]}}\n";
        out.close();
        auto res = load_run_output(rid);
        assert(!res.success);
        assert(res.code == LoadError::INVALID_METRIC);
    }

    // IO.0.4: reject bad artifact path
    {
        std::filesystem::remove_all("artifacts");
        const std::string rid = "eeeeeeeeeeeeeeee";
        std::filesystem::create_directories(std::filesystem::path("artifacts") / "runs" / rid);
        std::ofstream out(std::filesystem::path("artifacts") / "runs" / rid / "run_output.json");
        out << "{\"run_id\":\"" << rid
            << "\",\"ok\":true,\"label\":null,\"inputs\":{},\"metrics\":{},\"artifacts\":{\"root\":\"artifacts/runs/"
            << rid << "\",\"paths\":[\"../bad\"]}}\n";
        out.close();
        auto res = load_run_output(rid);
        assert(!res.success);
        assert(res.code == LoadError::INVALID_ARTIFACT_PATH);
    }

    // IO.1.0: ingest multiple runs with ordering and mixed validity
    {
        using v2::io::ingest_runs;
        using v2::io::IngestOptions;
        using v2::io::LoadError;
        std::filesystem::remove_all("artifacts");

        // valid runs
        const std::string r1 = "1111111111111111";
        const std::string r2 = "2222222222222222";
        const auto inputs_json = "{}";
        write_run_output(r1, inputs_json, {{"energy", 1.0}}, true);
        write_run_output(r2, inputs_json, {{"energy", 2.0}}, true);

        // invalid directory name
        std::filesystem::create_directories(std::filesystem::path("artifacts") / "runs" / "bad_dir");

        // missing manifest
        const std::string r3 = "3333333333333333";
        std::filesystem::create_directories(std::filesystem::path("artifacts") / "runs" / r3);

        // invalid metric
        const std::string r4 = "4444444444444444";
        std::filesystem::create_directories(std::filesystem::path("artifacts") / "runs" / r4);
        {
            std::ofstream out(std::filesystem::path("artifacts") / "runs" / r4 / "run_output.json");
            out << "{\"run_id\":\"" << r4
                << "\",\"ok\":true,\"label\":null,\"inputs\":{},\"metrics\":{\"energy\":1e309},"
                   "\"artifacts\":{\"root\":\"artifacts/runs/"
                << r4 << "\",\"paths\":[]}}\n";
        }

        auto ingest = ingest_runs();
        assert(ingest.runs.size() == 2);
        assert(ingest.runs[0].output.run_id == r1);
        assert(ingest.runs[1].output.run_id == r2);
        assert(!ingest.errors.empty());
        bool saw_invalid_dir = false;
        bool saw_missing = false;
        bool saw_validation = false;
        for (const auto& err : ingest.errors) {
            if (err.code == "INVALID_RUN_ID_DIR") saw_invalid_dir = true;
            if (err.code == "MISSING_MANIFEST") saw_missing = true;
            if (err.code == "VALIDATION_FAILED") saw_validation = true;
        }
        assert(saw_invalid_dir && saw_missing && saw_validation);

        // Filters: run_ids allowlist and max_runs
        IngestOptions opts;
        opts.run_ids = {r2};
        opts.max_runs = 1;
        auto ingest_filtered = ingest_runs(opts);
        assert(ingest_filtered.runs.size() == 1);
        assert(ingest_filtered.runs[0].output.run_id == r2);
    }

    // IO.1.1: aggregation summary with partial failures
    {
        using v2::io::aggregate_runs;
        using v2::io::SummaryOptions;
        std::filesystem::remove_all("artifacts");

        const std::string r1 = "aaaaaaaaaaaaaaaa";
        const std::string r2 = "bbbbbbbbbbbbbbbb";
        const std::string r3 = "cccccccccccccccc";
        const std::string r4 = "dddddddddddddddd";

        const std::string inputs_json = "{}";
        write_run_output(r1, inputs_json, {{"energy", 5.0}}, true);
        write_run_output(r2, inputs_json, {}, false, v2::core::FailLabel::SYS_NAN_FAIL);

        // missing manifest r3
        std::filesystem::create_directories(std::filesystem::path("artifacts") / "runs" / r3);

        // invalid metric r4
        std::filesystem::create_directories(std::filesystem::path("artifacts") / "runs" / r4);
        {
            std::ofstream out(std::filesystem::path("artifacts") / "runs" / r4 / "run_output.json");
            out << "{\"run_id\":\"" << r4
                << "\",\"ok\":true,\"label\":null,\"inputs\":{},\"metrics\":{\"energy\":1e309},"
                   "\"artifacts\":{\"root\":\"artifacts/runs/"
                << r4 << "\",\"paths\":[]}}\n";
        }

        SummaryOptions sopts;
        sopts.generated_at = "2024-01-01T00:00:00Z";
        auto summary = aggregate_runs(sopts);

        assert(summary.counts.total == 4);
        assert(summary.counts.passed == 1);
        assert(summary.counts.failed == 1);
        assert(summary.counts.invalid == 2);
        assert(summary.runs.size() == 2);
        assert(summary.runs[0].run_id == r1);
        assert(summary.runs[0].ok);
        assert(summary.runs[1].run_id == r2);
        assert(!summary.runs[1].ok && summary.runs[1].error.has_value());
        assert(summary.errors.size() == 2);

        // Deterministic JSON contains schema and generated_at
        assert(summary.json.find("\"schema\":\"dark/v2/io/run_summary/1.1\"") != std::string::npos);
        assert(summary.json.find("\"generated_at\":\"2024-01-01T00:00:00Z\"") != std::string::npos);
    }

    return 0;
}
