# CMake generated Testfile for 
# Source directory: /home/runner/work/DARK_leaf_drone_4-1_V2/DARK_leaf_drone_4-1_V2/v2/engine
# Build directory: /home/runner/work/DARK_leaf_drone_4-1_V2/DARK_leaf_drone_4-1_V2/build-test/v2/engine
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test([=[v2_engine_tests]=] "/home/runner/work/DARK_leaf_drone_4-1_V2/DARK_leaf_drone_4-1_V2/build-test/v2/engine/v2_engine_tests")
set_tests_properties([=[v2_engine_tests]=] PROPERTIES  LABELS "determinism" _BACKTRACE_TRIPLES "/home/runner/work/DARK_leaf_drone_4-1_V2/DARK_leaf_drone_4-1_V2/v2/engine/CMakeLists.txt;101;add_test;/home/runner/work/DARK_leaf_drone_4-1_V2/DARK_leaf_drone_4-1_V2/v2/engine/CMakeLists.txt;0;")
add_test([=[v2_engine_test_run_id]=] "/home/runner/work/DARK_leaf_drone_4-1_V2/DARK_leaf_drone_4-1_V2/build-test/v2/engine/v2_engine_test_run_id")
set_tests_properties([=[v2_engine_test_run_id]=] PROPERTIES  LABELS "determinism" _BACKTRACE_TRIPLES "/home/runner/work/DARK_leaf_drone_4-1_V2/DARK_leaf_drone_4-1_V2/v2/engine/CMakeLists.txt;108;add_test;/home/runner/work/DARK_leaf_drone_4-1_V2/DARK_leaf_drone_4-1_V2/v2/engine/CMakeLists.txt;0;")
add_test([=[v2_engine_test_json_emit]=] "/home/runner/work/DARK_leaf_drone_4-1_V2/DARK_leaf_drone_4-1_V2/build-test/v2/engine/v2_engine_test_json_emit")
set_tests_properties([=[v2_engine_test_json_emit]=] PROPERTIES  LABELS "determinism" _BACKTRACE_TRIPLES "/home/runner/work/DARK_leaf_drone_4-1_V2/DARK_leaf_drone_4-1_V2/v2/engine/CMakeLists.txt;115;add_test;/home/runner/work/DARK_leaf_drone_4-1_V2/DARK_leaf_drone_4-1_V2/v2/engine/CMakeLists.txt;0;")
subdirs("tests")
