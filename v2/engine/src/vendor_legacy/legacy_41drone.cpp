#include "v2/vendor_legacy/legacy_41drone.hpp"

namespace v2::vendor_legacy {

std::string legacy_build_info() {
    // Vendor identifier: repository + branch + import date
    // This represents the frozen snapshot of the legacy codebase
    return "bojnick-source/4-1-drone main 2026-01-11";
}

std::error_code evaluate_candidate() {
    // Stub ONLY - returns NotImplemented error
    // No physics, no solver calls, no data translation
    return make_not_implemented_error();
}

} // namespace v2::vendor_legacy
