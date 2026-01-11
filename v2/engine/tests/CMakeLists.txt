cmake_minimum_required(VERSION 3.20)

# ---- Test: vendor_legacy_test ----
add_executable(vendor_legacy_test
  vendor_legacy_test.cpp
)

target_link_libraries(vendor_legacy_test PRIVATE v2_engine)

# Register the test with CTest
add_test(NAME vendor_legacy_test COMMAND vendor_legacy_test)
