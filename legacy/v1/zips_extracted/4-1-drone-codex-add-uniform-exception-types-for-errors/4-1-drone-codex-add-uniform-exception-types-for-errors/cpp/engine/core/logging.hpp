#pragma once
/*
===========================================================
Fragment 1.1 — Core: Logging (Hardened)
FILE: cpp/engine/core/logging.hpp
===========================================================
Purpose:
  - Minimal, dependency-free logging used by ALL engine modules.
  - Centralizes stdout/stderr policy.

Hardening:
  - Logging MUST NOT throw (noexcept API).
  - Thread-safe (coarse mutex in implementation).
  - Caller controls severity; implementation routes WARN/ERROR to stderr.

Notes:
  - Keep this tiny. No fmt, no spdlog. This is the base layer.
===========================================================
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
