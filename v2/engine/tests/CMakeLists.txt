cmake_minimum_required(VERSION 3.20)

# ---- Test: vendor_legacy_test ----
add_executable(vendor_legacy_test
  vendor_legacy_test.cpp
)

target_link_libraries(vendor_legacy_test PRIVATE v2_engine)

# Register the test with CTest
add_test(NAME vendor_legacy_test COMMAND vendor_legacy_test)

# ---- Test: disk_area_test ----
add_executable(disk_area_test
  physics/disk_area_test.cpp
)

target_link_libraries(disk_area_test PRIVATE v2_engine)

# Register the test with CTest
add_test(NAME disk_area_test COMMAND disk_area_test)

# ---- Test: hover_power_test ----
add_executable(hover_power_test
  physics/hover_power_test.cpp
)

target_link_libraries(hover_power_test PRIVATE v2_engine)

# Register the test with CTest
add_test(NAME hover_power_test COMMAND hover_power_test)
