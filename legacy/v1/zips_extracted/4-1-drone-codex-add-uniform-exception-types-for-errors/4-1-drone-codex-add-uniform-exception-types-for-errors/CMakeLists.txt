cmake_minimum_required(VERSION 3.20)

project(lift_engine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Hardening flags (safe defaults; adjust per toolchain)
if (MSVC)
  add_compile_options(/W4 /permissive-)
else()
  add_compile_options(-Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion)
endif()

# ---- Library: lift_engine ----
add_library(lift_engine
  # Core
  cpp/engine/core/logging.cpp
  cpp/engine/core/hashing.cpp
  cpp/engine/core/cache_key.cpp
  cpp/engine/core/design_hash.cpp
  # Physics
  cpp/engine/physics/disk_area.cpp
  cpp/engine/physics/hover_momentum.cpp
  cpp/engine/physics/cfd_results.cpp
  cpp/engine/physics/stats_report_csv.cpp
  # Analysis
  cpp/engine/analysis/closeout_eval.cpp
  cpp/engine/analysis/closeout_json.cpp
  cpp/engine/analysis/closeout_report_csv.cpp
)

target_include_directories(lift_engine PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/cpp
)

# ---- CLI: closeout_cli (Fragment 1.4.28 tool) ----
add_executable(closeout_cli
  cpp/tools/closeout_cli.cpp
)

target_link_libraries(closeout_cli PRIVATE lift_engine)

# ---- CLI: closeout_demo (Fragment 2.5 harness) ----
add_executable(closeout_demo
  cpp/cli/closeout_demo.cpp
)

target_link_libraries(closeout_demo PRIVATE lift_engine)

# ---- CLI: closeout_cli (Closeout tool with CSV outputs) ----
add_executable(closeout_cli
  cpp/tools/closeout_cli.cpp
)

target_link_libraries(closeout_cli PRIVATE lift_engine)
