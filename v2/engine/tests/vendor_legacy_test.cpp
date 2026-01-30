#include "v2/vendor_legacy/legacy_41drone.hpp"
#include <iostream>
#include <cassert>

int main() {
    // Test 1: Verify legacy_build_info() returns non-empty string
    std::string build_info = v2::vendor_legacy::legacy_build_info();
    
    std::cout << "Legacy Build Info: " << build_info << std::endl;
    
    assert(!build_info.empty() && "legacy_build_info() must return non-empty string");
    
    // Test 2: Verify evaluate_candidate() returns NotImplemented error
    std::error_code error = v2::vendor_legacy::evaluate_candidate();
    
    assert(error && "evaluate_candidate() must return an error");
    assert(error.category().name() == std::string("NotImplemented") && 
           "evaluate_candidate() must return NotImplemented error");
    
    std::cout << "All tests passed!" << std::endl;
    
    return 0;
}
