/*
================================================================================
v2 Core — Run Configuration Implementation
FILE: v2/engine/src/core/run_config.cpp
================================================================================
*/

#include "v2/core/run_config.hpp"
#include <stdexcept>
#include <sstream>
#include <iomanip>
#include <random>

// Build-time metadata injected by CMake
#ifndef V2_GIT_COMMIT_HASH
#define V2_GIT_COMMIT_HASH "unknown"
#endif

#ifndef V2_BUILD_TYPE
#define V2_BUILD_TYPE "unknown"
#endif

#ifndef V2_COMPILER_ID
#define V2_COMPILER_ID "unknown"
#endif

#ifndef V2_COMPILER_VERSION
#define V2_COMPILER_VERSION "unknown"
#endif

namespace v2::core {

void RunConfig::validate() const {
    if (run_id.empty()) {
        throw std::invalid_argument("RunConfig: run_id cannot be empty");
    }
    if (git_commit_hash.empty()) {
        throw std::invalid_argument("RunConfig: git_commit_hash cannot be empty");
    }
    if (build_type.empty()) {
        throw std::invalid_argument("RunConfig: build_type cannot be empty");
    }
    if (compiler_id.empty()) {
        throw std::invalid_argument("RunConfig: compiler_id cannot be empty");
    }
    if (compiler_version.empty()) {
        throw std::invalid_argument("RunConfig: compiler_version cannot be empty");
    }
}

std::string RunConfig::generate_run_id() const {
    // Create deterministic hash from config contents
    std::ostringstream oss;
    oss << "run_" 
        << std::hex << std::setfill('0') << std::setw(16) << global_seed
        << "_" << git_commit_hash.substr(0, 8);
    return oss.str();
}

std::string RunConfig::to_json() const {
    std::ostringstream json;
    json << "{\n";
    json << "  \"global_seed\": " << global_seed << ",\n";
    json << "  \"run_id\": \"" << run_id << "\",\n";
    json << "  \"git_commit_hash\": \"" << git_commit_hash << "\",\n";
    json << "  \"build_type\": \"" << build_type << "\",\n";
    json << "  \"compiler_id\": \"" << compiler_id << "\",\n";
    json << "  \"compiler_version\": \"" << compiler_version << "\",\n";
    
    // Compiler flags array
    json << "  \"compiler_flags\": [";
    for (size_t i = 0; i < compiler_flags.size(); ++i) {
        if (i > 0) json << ", ";
        json << "\"" << compiler_flags[i] << "\"";
    }
    json << "],\n";
    
    // Metadata object
    json << "  \"metadata\": {\n";
    size_t count = 0;
    for (const auto& [key, value] : metadata) {
        if (count > 0) json << ",\n";
        json << "    \"" << key << "\": \"" << value << "\"";
        ++count;
    }
    json << "\n  }\n";
    json << "}";
    
    return json.str();
}

RunConfig RunConfig::create_with_build_info(uint64_t seed) {
    RunConfig config;
    config.global_seed = seed;
    config.git_commit_hash = V2_GIT_COMMIT_HASH;
    config.build_type = V2_BUILD_TYPE;
    config.compiler_id = V2_COMPILER_ID;
    config.compiler_version = V2_COMPILER_VERSION;
    
    // Generate run_id if not set
    config.run_id = config.generate_run_id();
    
    // Add standard metadata
    config.metadata["timestamp"] = __DATE__ " " __TIME__;
    
    return config;
}

} // namespace v2::core
