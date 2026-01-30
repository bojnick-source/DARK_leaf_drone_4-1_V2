cmake_minimum_required(VERSION 3.20)

project(DARK_leaf_drone_v2 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Enable testing
enable_testing()

# Add vendor code as isolated static library
add_subdirectory(external/4-1-drone)

# Add v2 engine
add_subdirectory(v2/engine)
