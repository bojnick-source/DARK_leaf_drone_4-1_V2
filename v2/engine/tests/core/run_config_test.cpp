/*
================================================================================
v2 Core Tests — RunConfig and Determinism Verification
FILE: v2/engine/tests/core/run_config_test.cpp

Purpose:
  - Verify RunConfig validation and serialization
  - Test deterministic execution guarantees
  - Ensure run traceability and reproducibility
================================================================================
*/

#include "v2/core/run_config.hpp"
#include <iostream>
#include <cassert>
#include <stdexcept>

void test_run_config_creation() {
    std::cout << "Test: RunConfig creation and validation..." << std::endl;
    
    v2::core::RunConfig config;
    config.global_seed = 12345;
    config.run_id = "test_run_001";
    config.git_commit_hash = "abc123def456";
    config.build_type = "Debug";
    config.compiler_id = "g++";
    config.compiler_version = "13.0.0";
    config.compiler_flags = {"-std=c++20", "-O2", "-Wall"};
    config.metadata["user"] = "test_user";
    config.metadata["host"] = "test_host";
    
    // Should validate without throwing
    config.validate();
    
    std::cout << "  global_seed: " << config.global_seed << std::endl;
    std::cout << "  run_id: " << config.run_id << std::endl;
    std::cout << "  git_commit_hash: " << config.git_commit_hash << std::endl;
    std::cout << "  PASS" << std::endl;
}

void test_run_config_validation_failures() {
    std::cout << "Test: RunConfig validation failures..." << std::endl;
    
    // Empty run_id should fail
    {
        v2::core::RunConfig config;
        config.global_seed = 12345;
        config.run_id = "";  // Empty!
        config.git_commit_hash = "abc123";
        config.build_type = "Debug";
        config.compiler_id = "g++";
        config.compiler_version = "13.0.0";
        
        bool caught = false;
        try {
            config.validate();
        } catch (const std::invalid_argument& e) {
            caught = true;
            std::cout << "  Caught expected error: " << e.what() << std::endl;
        }
        assert(caught && "Expected validation error for empty run_id");
    }
    
    // Empty git hash should fail
    {
        v2::core::RunConfig config;
        config.global_seed = 12345;
        config.run_id = "test_run";
        config.git_commit_hash = "";  // Empty!
        config.build_type = "Debug";
        config.compiler_id = "g++";
        config.compiler_version = "13.0.0";
        
        bool caught = false;
        try {
            config.validate();
        } catch (const std::invalid_argument& e) {
            caught = true;
            std::cout << "  Caught expected error: " << e.what() << std::endl;
        }
        assert(caught && "Expected validation error for empty git_commit_hash");
    }
    
    std::cout << "  PASS" << std::endl;
}

void test_run_config_serialization() {
    std::cout << "Test: RunConfig JSON serialization..." << std::endl;
    
    v2::core::RunConfig config;
    config.global_seed = 42;
    config.run_id = "test_run_json";
    config.git_commit_hash = "1234567890abcdef";
    config.build_type = "Release";
    config.compiler_id = "clang++";
    config.compiler_version = "15.0.0";
    config.compiler_flags = {"-std=c++20", "-O3"};
    config.metadata["platform"] = "Linux";
    
    std::string json = config.to_json();
    
    // Verify JSON contains key fields
    assert(json.find("\"global_seed\": 42") != std::string::npos);
    assert(json.find("\"run_id\": \"test_run_json\"") != std::string::npos);
    assert(json.find("\"git_commit_hash\"") != std::string::npos);
    assert(json.find("\"compiler_flags\"") != std::string::npos);
    assert(json.find("\"metadata\"") != std::string::npos);
    assert(json.find("\"platform\": \"Linux\"") != std::string::npos);
    
    std::cout << "  JSON output (first 200 chars):" << std::endl;
    std::cout << "  " << json.substr(0, 200) << "..." << std::endl;
    std::cout << "  PASS" << std::endl;
}

void test_run_id_generation() {
    std::cout << "Test: RunConfig run_id generation..." << std::endl;
    
    v2::core::RunConfig config1;
    config1.global_seed = 12345;
    config1.git_commit_hash = "abcdef123456";
    
    std::string run_id1 = config1.generate_run_id();
    assert(!run_id1.empty());
    assert(run_id1.find("run_") == 0);  // Should start with "run_"
    
    // Same seed and hash should generate same run_id (deterministic)
    v2::core::RunConfig config2;
    config2.global_seed = 12345;
    config2.git_commit_hash = "abcdef123456";
    
    std::string run_id2 = config2.generate_run_id();
    assert(run_id1 == run_id2 && "Same inputs should generate same run_id");
    
    // Different seed should generate different run_id
    v2::core::RunConfig config3;
    config3.global_seed = 99999;
    config3.git_commit_hash = "abcdef123456";
    
    std::string run_id3 = config3.generate_run_id();
    assert(run_id1 != run_id3 && "Different seed should generate different run_id");
    
    std::cout << "  run_id1: " << run_id1 << std::endl;
    std::cout << "  run_id2: " << run_id2 << std::endl;
    std::cout << "  run_id3: " << run_id3 << std::endl;
    std::cout << "  PASS (deterministic generation)" << std::endl;
}

void test_build_info_creation() {
    std::cout << "Test: RunConfig creation with build info..." << std::endl;
    
    v2::core::RunConfig config = v2::core::RunConfig::create_with_build_info(54321);
    
    assert(config.global_seed == 54321);
    assert(!config.run_id.empty());
    assert(!config.git_commit_hash.empty());
    assert(!config.build_type.empty());
    assert(!config.compiler_id.empty());
    assert(!config.compiler_version.empty());
    
    std::cout << "  global_seed: " << config.global_seed << std::endl;
    std::cout << "  run_id: " << config.run_id << std::endl;
    std::cout << "  git_commit_hash: " << config.git_commit_hash << std::endl;
    std::cout << "  build_type: " << config.build_type << std::endl;
    std::cout << "  compiler_id: " << config.compiler_id << std::endl;
    std::cout << "  PASS" << std::endl;
}

void test_determinism_guarantee() {
    std::cout << "Test: Determinism guarantee (same seed ⇒ same run_id)..." << std::endl;
    
    const uint64_t seed = 42;
    
    // Create two configs with same seed
    v2::core::RunConfig config1 = v2::core::RunConfig::create_with_build_info(seed);
    v2::core::RunConfig config2 = v2::core::RunConfig::create_with_build_info(seed);
    
    // Run IDs should be identical (deterministic)
    assert(config1.run_id == config2.run_id);
    assert(config1.global_seed == config2.global_seed);
    assert(config1.git_commit_hash == config2.git_commit_hash);
    
    std::cout << "  Seed: " << seed << std::endl;
    std::cout << "  Run ID 1: " << config1.run_id << std::endl;
    std::cout << "  Run ID 2: " << config2.run_id << std::endl;
    std::cout << "  PASS (deterministic)" << std::endl;
}

int main() {
    std::cout << "=== RunConfig and Determinism Tests ===" << std::endl;
    
    test_run_config_creation();
    test_run_config_validation_failures();
    test_run_config_serialization();
    test_run_id_generation();
    test_build_info_creation();
    test_determinism_guarantee();
    
    std::cout << "\nAll RunConfig tests passed!" << std::endl;
    return 0;
}
