#pragma once
/*
================================================================================
v2 Core — Run Configuration (Determinism & Traceability)
FILE: v2/engine/include/v2/core/run_config.hpp

Purpose:
  - Guarantee deterministic execution: same inputs + same seed ⇒ same outputs
  - Provide full run traceability for every evaluation
  - Capture build and environment metadata
  - Zero behavioral change to existing solver logic

This is the single source of truth for execution determinism.
================================================================================
*/

#include <string>
#include <vector>
#include <map>
#include <cstdint>

namespace v2::core {

/**
 * RunConfig: Authoritative configuration for deterministic execution.
 * 
 * This struct captures all information needed to reproduce a run exactly:
 * - Random seed for determinism
 * - Build metadata (commit, compiler, flags)
 * - Run identification and traceability
 */
struct RunConfig {
    // REQUIRED: Single source of randomness for entire run
    uint64_t global_seed = 0;
    
    // UUID or content hash for run identification
    std::string run_id;
    
    // Exact git commit hash at build time
    std::string git_commit_hash;
    
    // Build configuration: Debug / Release / RelWithDebInfo
    std::string build_type;
    
    // Compiler identifier (e.g., "clang++", "g++", "MSVC")
    std::string compiler_id;
    
    // Exact compiler version string
    std::string compiler_version;
    
    // Complete list of compiler flags used
    std::vector<std::string> compiler_flags;
    
    // Additional metadata (environment variables, system info, etc.)
    std::map<std::string, std::string> metadata;
    
    /**
     * Validate that RunConfig is complete and consistent.
     * @throws std::invalid_argument if configuration is invalid
     */
    void validate() const;
    
    /**
     * Generate a deterministic run_id from config contents.
     * Useful when run_id is not explicitly set.
     */
    std::string generate_run_id() const;
    
    /**
     * Serialize RunConfig to JSON string for artifact emission.
     */
    std::string to_json() const;
    
    /**
     * Create RunConfig with build-time metadata.
     * This captures git hash, compiler info, etc. from CMake.
     */
    static RunConfig create_with_build_info(uint64_t seed);
};

} // namespace v2::core
