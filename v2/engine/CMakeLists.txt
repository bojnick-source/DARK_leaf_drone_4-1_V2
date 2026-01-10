add_library(v2_engine STATIC
    src/engine.cpp
    src/core/error.cpp
    src/io/run_id.cpp
    src/io/artifacts.cpp
    src/io/json_emit.cpp
)

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

add_executable(v2_engine_test_run_id
    tests/test_run_id_determinism.cpp
)
target_link_libraries(v2_engine_test_run_id PRIVATE v2_engine)
add_test(NAME v2_engine_test_run_id COMMAND v2_engine_test_run_id)

add_executable(v2_engine_test_json_emit
    tests/test_json_emit_smoke.cpp
)
target_link_libraries(v2_engine_test_json_emit PRIVATE v2_engine)
add_test(NAME v2_engine_test_json_emit COMMAND v2_engine_test_json_emit)
