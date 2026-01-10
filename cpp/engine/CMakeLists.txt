add_library(cpp_accuracy_gate STATIC
    analysis/accuracy_gate.cpp
)

target_include_directories(cpp_accuracy_gate
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}
        ${CMAKE_CURRENT_SOURCE_DIR}/analysis
)

target_link_libraries(cpp_accuracy_gate
    PUBLIC
        v2_engine
)

add_executable(cpp_accuracy_gate_tests
    tests/test_accuracy_gate.cpp
)

target_link_libraries(cpp_accuracy_gate_tests PRIVATE cpp_accuracy_gate)
add_test(NAME cpp_accuracy_gate_tests COMMAND cpp_accuracy_gate_tests)
