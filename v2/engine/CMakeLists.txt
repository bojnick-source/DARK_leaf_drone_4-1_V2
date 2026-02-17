cmake_minimum_required(VERSION 3.20)

# Capture build metadata for RunConfig
execute_process(
  COMMAND git rev-parse HEAD
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
  OUTPUT_VARIABLE GIT_COMMIT_HASH
  OUTPUT_STRIP_TRAILING_WHITESPACE
  ERROR_QUIET
)
if(NOT GIT_COMMIT_HASH)
  set(GIT_COMMIT_HASH "unknown")
endif()

# Set default build type if not specified
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE "Debug")
endif()

# ---- v2 Engine Library ----
add_library(v2_engine STATIC
  src/physics/physics_factory.cpp
  src/physics/baseline/disk_area_calculator.cpp
  src/physics/baseline/hover_power_model.cpp
  src/physics/adapters/legacy_4_1/disk_area_adapter.cpp
  src/physics/adapters/legacy_4_1/hover_power_adapter.cpp
  src/vendor_legacy/legacy_41drone.cpp
  src/core/run_config.cpp
  src/uncertainty/types.cpp
  src/uncertainty/monte_carlo_evaluator.cpp
  src/sampling/types.cpp
  src/sampling/uncertainty_driven_policy.cpp
  src/safety/types.cpp
  src/safety/probabilistic_gate.cpp
  src/calibration/types.cpp
  src/calibration/calibration_fitter.cpp
  src/calibration/calibrated_evaluator.cpp
  src/validity/types.cpp
  src/validity/conservative_ood_detector.cpp
  src/analysis/accuracy_gate.cpp
  src/analysis/commit_gate.cpp
  src/analysis/lineage_stamper.cpp
  src/engine.cpp
  src/core/error.cpp
  src/io/run_id.cpp
  src/io/artifacts.cpp
  src/io/json_emit.cpp
  # Legacy 4.1 sources
  src/legacy_4_1/engine/analysis/closeout_eval.cpp
  src/legacy_4_1/engine/analysis/closeout_json.cpp
  src/legacy_4_1/engine/core/cache_key.cpp
  src/legacy_4_1/engine/core/design_hash.cpp
  src/legacy_4_1/engine/core/hashing.cpp
  src/legacy_4_1/engine/core/logging.cpp
  src/legacy_4_1/engine/physics/disk_area.cpp
  src/legacy_4_1/engine/physics/hover_momentum.cpp
)

target_include_directories(v2_engine PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Private include for implementation files
target_include_directories(v2_engine PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/src/legacy_4_1
)

# Inject build metadata as compile definitions
target_compile_definitions(v2_engine PRIVATE
  V2_GIT_COMMIT_HASH="${GIT_COMMIT_HASH}"
  V2_BUILD_TYPE="${CMAKE_BUILD_TYPE}"
  V2_COMPILER_ID="${CMAKE_CXX_COMPILER_ID}"
  V2_COMPILER_VERSION="${CMAKE_CXX_COMPILER_VERSION}"
)

# C++ standard for v2 code
target_compile_features(v2_engine PUBLIC cxx_std_20)

# ---- Tests ----
enable_testing()
add_subdirectory(tests)

target_include_directories(v2_engine
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_features(v2_engine PUBLIC cxx_std_20)

add_executable(v2_engine_cli
    src/cli/v2_cli.cpp
)

target_link_libraries(v2_engine_cli PRIVATE v2_engine)

add_executable(v2_engine_tests
    tests/run_manifest_tests.cpp
)

target_link_libraries(v2_engine_tests PRIVATE v2_engine)
add_test(NAME v2_engine_tests COMMAND v2_engine_tests)
set_tests_properties(v2_engine_tests PROPERTIES LABELS "determinism")

add_executable(v2_engine_test_run_id
    tests/test_run_id_determinism.cpp
)
target_link_libraries(v2_engine_test_run_id PRIVATE v2_engine)
add_test(NAME v2_engine_test_run_id COMMAND v2_engine_test_run_id)
set_tests_properties(v2_engine_test_run_id PROPERTIES LABELS "determinism")

add_executable(v2_engine_test_json_emit
    tests/test_json_emit_smoke.cpp
)
target_link_libraries(v2_engine_test_json_emit PRIVATE v2_engine)
add_test(NAME v2_engine_test_json_emit COMMAND v2_engine_test_json_emit)
set_tests_properties(v2_engine_test_json_emit PROPERTIES LABELS "determinism")
