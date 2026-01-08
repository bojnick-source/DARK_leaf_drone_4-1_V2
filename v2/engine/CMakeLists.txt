add_library(v2_engine STATIC
    src/engine.cpp
)

target_include_directories(v2_engine
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_features(v2_engine PUBLIC cxx_std_20)

add_executable(v2_engine_cli
    src/cli/main.cpp
)

target_link_libraries(v2_engine_cli PRIVATE v2_engine)
