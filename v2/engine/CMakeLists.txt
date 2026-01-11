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
  src/vendor_legacy/legacy_41drone.cpp
  src/physics/physics_factory.cpp
  src/physics/adapters/legacy_4_1/disk_area_adapter.cpp
  src/physics/adapters/legacy_4_1/hover_power_adapter.cpp
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
)

target_include_directories(v2_engine PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Private include for adapter implementation files
target_include_directories(v2_engine PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src
)

# Inject build metadata as compile definitions
target_compile_definitions(v2_engine PRIVATE
  V2_GIT_COMMIT_HASH="${GIT_COMMIT_HASH}"
  V2_BUILD_TYPE="${CMAKE_BUILD_TYPE}"
  V2_COMPILER_ID="${CMAKE_CXX_COMPILER_ID}"
  V2_COMPILER_VERSION="${CMAKE_CXX_COMPILER_VERSION}"
)

# Link against the vendor static library
target_link_libraries(v2_engine PUBLIC legacy_41drone)

# C++ standard for v2 code
target_compile_features(v2_engine PUBLIC cxx_std_20)

# ---- Tests ----
enable_testing()
add_subdirectory(tests)
