cmake_minimum_required(VERSION 3.20)

# ---- v2 Engine Library ----
add_library(v2_engine STATIC
  src/vendor_legacy/legacy_41drone.cpp
)

target_include_directories(v2_engine PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Link against the vendor static library
target_link_libraries(v2_engine PUBLIC legacy_41drone)

# C++ standard for v2 code
target_compile_features(v2_engine PUBLIC cxx_std_20)

# ---- Tests ----
enable_testing()
add_subdirectory(tests)
