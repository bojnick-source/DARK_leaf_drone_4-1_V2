cmake_minimum_required(VERSION 3.20)

# ---- v2 Engine Library ----
add_library(v2_engine STATIC
  src/vendor_legacy/legacy_41drone.cpp
  src/physics/physics_factory.cpp
  src/physics/adapters/legacy_4_1/disk_area_adapter.cpp
  src/physics/adapters/legacy_4_1/hover_power_adapter.cpp
)

target_include_directories(v2_engine PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Private include for adapter implementation files
target_include_directories(v2_engine PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src
)

# Link against the vendor static library
target_link_libraries(v2_engine PUBLIC legacy_41drone)

# C++ standard for v2 code
target_compile_features(v2_engine PUBLIC cxx_std_20)

# ---- Tests ----
enable_testing()
add_subdirectory(tests)
