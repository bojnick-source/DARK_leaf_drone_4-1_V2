/*
===========================================================
Fragment 1.1 — Core: Logging (Implementation)
FILE: cpp/engine/core/logging.cpp
===========================================================
Purpose:
  - Implements the noexcept logging API.
  - Adds timestamp + level tag.

Hardening:
  - All operations wrapped so exceptions are swallowed.
  - Coarse mutex makes multi-thread output readable.
===========================================================
*/

#include "engine/core/logging.hpp"

#include <atomic>
#include <chrono>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <sstream>

namespace lift {

static std::atomic<int> g_level{static_cast<int>(LogLevel::INFO)};
static std::mutex g_log_mu;

static const char* level_tag(LogLevel lvl) noexcept {
  switch (lvl) {
    case LogLevel::DEBUG: return "DEBUG";
    case LogLevel::INFO:  return "INFO";
    case LogLevel::WARN:  return "WARN";
    case LogLevel::ERROR: return "ERROR";
    default:              return "INFO";
  }
}

void set_log_level(LogLevel lvl) noexcept {
  g_level.store(static_cast<int>(lvl), std::memory_order_relaxed);
}

LogLevel get_log_level() noexcept {
  return static_cast<LogLevel>(g_level.load(std::memory_order_relaxed));
}

static std::string utc_timestamp() {
  using clock = std::chrono::system_clock;
  auto now = clock::now();
  std::time_t tt = clock::to_time_t(now);
  std::tm tm{};
#if defined(_WIN32)
  gmtime_s(&tm, &tt);
#else
  gmtime_r(&tt, &tm);
#endif
  std::ostringstream oss;
  oss << std::put_time(&tm, "%Y-%m-%dT%H:%M:%SZ");
  return oss.str();
}

void log(LogLevel lvl, const std::string& msg) noexcept {
  try {
    const int cur = g_level.load(std::memory_order_relaxed);
    if (static_cast<int>(lvl) < cur) return;

    std::lock_guard<std::mutex> lk(g_log_mu);

    std::ostream& out = (lvl >= LogLevel::WARN) ? std::cerr : std::cout;
    out << "[" << utc_timestamp() << "]"
        << "[" << level_tag(lvl) << "] "
        << msg << "\n";
    out.flush();
  } catch (...) {
    // Must never throw. Swallow everything.
  }
}

} // namespace lift
