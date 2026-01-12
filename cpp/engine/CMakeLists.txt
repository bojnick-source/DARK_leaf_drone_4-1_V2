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

add_library(cpp_commit_gate STATIC
    analysis/commit_gate.cpp
)

target_include_directories(cpp_commit_gate
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}
        ${CMAKE_CURRENT_SOURCE_DIR}/analysis
)

target_link_libraries(cpp_commit_gate
    PUBLIC
        v2_engine
)

add_executable(cpp_accuracy_gate_tests
    tests/test_accuracy_gate.cpp
)

target_link_libraries(cpp_accuracy_gate_tests PRIVATE cpp_accuracy_gate)
add_test(NAME cpp_accuracy_gate_tests COMMAND cpp_accuracy_gate_tests)
set_tests_properties(cpp_accuracy_gate_tests PROPERTIES LABELS "determinism")

add_executable(cpp_commit_gate_tests
    tests/test_commit_gate.cpp
)

target_link_libraries(cpp_commit_gate_tests PRIVATE cpp_commit_gate)
add_test(NAME cpp_commit_gate_tests COMMAND cpp_commit_gate_tests)
set_tests_properties(cpp_commit_gate_tests PROPERTIES LABELS "determinism")

add_library(cpp_lineage_stamper STATIC
    analysis/lineage_stamper.cpp
)

target_include_directories(cpp_lineage_stamper
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}
        ${CMAKE_CURRENT_SOURCE_DIR}/analysis
)

target_link_libraries(cpp_lineage_stamper
    PUBLIC
        v2_engine
)

add_executable(cpp_lineage_stamper_tests
    tests/test_lineage_stamper.cpp
)

target_link_libraries(cpp_lineage_stamper_tests PRIVATE cpp_lineage_stamper)
add_test(NAME cpp_lineage_stamper_tests COMMAND cpp_lineage_stamper_tests)
set_tests_properties(cpp_lineage_stamper_tests PROPERTIES LABELS "determinism")
