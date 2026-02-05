#pragma once

#include <string>
#include <system_error>

namespace v2::vendor_legacy {

/**
 * Returns vendor identifier for the legacy 4.1 drone codebase.
 * Format: "repo + branch + import date"
 */
std::string legacy_build_info();

/**
 * Error category for NotImplemented errors.
 */
class NotImplementedCategory : public std::error_category {
public:
    const char* name() const noexcept override {
        return "NotImplemented";
    }

    std::string message(int) const override {
        return "Feature not yet implemented";
    }
};

inline const std::error_category& not_implemented_category() {
    static NotImplementedCategory instance;
    return instance;
}

inline std::error_code make_not_implemented_error() {
    return {1, not_implemented_category()};
}

/**
 * Stub function for evaluating candidates.
 */
std::error_code evaluate_candidate();

} // namespace v2::vendor_legacy