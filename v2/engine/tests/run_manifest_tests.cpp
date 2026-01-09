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

    return 0;
}
