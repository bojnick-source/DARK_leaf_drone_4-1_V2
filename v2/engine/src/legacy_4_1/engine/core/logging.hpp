#pragma once
/*
================================================================================
Legacy 4.1 — Core: Logging (Hardened)
FILE: engine/core/logging.hpp
================================================================================
*/

#include <string>

namespace lift {

enum class LogLevel : int { DEBUG = 0, INFO = 1, WARN = 2, ERROR = 3 };

// Set global logging verbosity (default INFO).
void set_log_level(LogLevel lvl) noexcept;

// Get global logging verbosity.
LogLevel get_log_level() noexcept;

// Core logging call. Never throws.
void log(LogLevel lvl, const std::string& msg) noexcept;

} // namespace lift