#pragma once
// ============================================================================
// BEMT Requirements and Error Handling
// File: cpp/engine/physics/bemt_require.hpp
// ============================================================================
//
// Purpose:
// - Provide error codes and exception types for BEMT uncertainty analysis.
// - Consistent with existing lift::LiftError hierarchy.
//
// ============================================================================

#include "engine/core/errors.hpp"

#include <string>
#include <stdexcept>

namespace lift::bemt {

// ErrorCode enum for BEMT exceptions
enum class ErrorCode : uint16_t {
    None = 0,
    InvalidInput = 100,
    MissingRequiredField = 101,
    IoError = 200,
    ComputationError = 300,
};

// BEMT-specific exception that wraps lift::LiftError
class BemtException : public lift::LiftError {
public:
    BemtException(ErrorCode code, std::string msg)
        : lift::LiftError(std::move(msg)), error_code_(code) {}
    
    ErrorCode error_code() const { return error_code_; }
    
private:
    ErrorCode error_code_;
};

} // namespace lift::bemt
