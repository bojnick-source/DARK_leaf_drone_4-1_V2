cmake_minimum_required(VERSION 3.20)

project(DARK_leaf_drone_4-1_V2 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

enable_testing()

add_subdirectory(v2/engine)
add_subdirectory(v2/studio)
add_subdirectory(cpp/engine)
