# SHIM CMakeLists.txt for vendor legacy code
# This file enumerates vendor sources and builds ONLY the static library.
# DO NOT modify vendor source files.
# DO NOT alter global compiler flags.

cmake_minimum_required(VERSION 3.20)

# ---- Static Library: legacy_41drone ----
# Note: Excluding analysis files due to compilation issues in vendor code
# The adapter layer provides stubs for these functions
add_library(legacy_41drone STATIC
  # Core
  cpp/engine/core/logging.cpp
  cpp/engine/core/hashing.cpp
  cpp/engine/core/cache_key.cpp
  cpp/engine/core/design_hash.cpp
  # Physics
  cpp/engine/physics/disk_area.cpp
  cpp/engine/physics/hover_momentum.cpp
)

target_include_directories(legacy_41drone PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/cpp
)

# C++ standard for vendor code (requires C++20 for std::bit_cast)
set_target_properties(legacy_41drone PROPERTIES
  CXX_STANDARD 20
  CXX_STANDARD_REQUIRED ON
  CXX_EXTENSIONS OFF
)
