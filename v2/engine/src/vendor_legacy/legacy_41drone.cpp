#include "v2/vendor_legacy/legacy_41drone.hpp"

namespace v2::vendor_legacy {

std::string legacy_build_info() {
    return "legacy_4_1 snapshot from bojnick-source/4-1-drone main (2026-02-04)";
}

std::error_code evaluate_candidate() {
    return make_not_implemented_error();
}

} // namespace v2::vendor_legacy