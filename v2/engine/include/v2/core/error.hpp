#pragma once

#include <string>

namespace v2::core {

enum class ErrorCode {
    None = 0,
    InvalidInput,
    IoFailure,
};

struct Error {
    ErrorCode code{ErrorCode::None};
    std::string message{};

    static Error ok() { return {}; }
    static Error invalid(std::string msg) { return {ErrorCode::InvalidInput, std::move(msg)}; }
    static Error io(std::string msg) { return {ErrorCode::IoFailure, std::move(msg)}; }

    [[nodiscard]] bool success() const { return code == ErrorCode::None; }
};

}  // namespace v2::core
