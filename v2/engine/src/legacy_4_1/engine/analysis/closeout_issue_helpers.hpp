#pragma once
/*
================================================================================
Legacy 4.1 — Analysis: Closeout Issue Helpers (Uniform Issue Schema)
FILE: engine/analysis/closeout_issue_helpers.hpp
================================================================================
*/

#include <cmath>
#include <cstdint>
#include <limits>
#include <string>
#include <vector>

namespace lift::closeout {

// -------------------------------
// Unset (NaN) semantics
// -------------------------------
inline constexpr double kUnset = std::numeric_limits<double>::quiet_NaN();

inline bool is_unset(double x) {
  return std::isnan(x);
}

// -------------------------------
// Uniform issue kinds
// -------------------------------
enum class IssueKind : std::uint8_t {
  MissingData = 0,
  InvalidInput = 1,
  ConstraintViolation = 2,
  InternalError = 3
};

inline const char* to_string(IssueKind k) {
  switch (k) {
    case IssueKind::MissingData: return "missing_data";
    case IssueKind::InvalidInput: return "invalid_input";
    case IssueKind::ConstraintViolation: return "constraint_violation";
    case IssueKind::InternalError: return "internal_error";
    default: return "unknown";
  }
}

// -------------------------------
// Gate decision
// -------------------------------
enum class GateStatus : std::uint8_t {
  GO = 0,
  NO_GO = 1,
  NEEDS_DATA = 2
};

inline const char* to_string(GateStatus s) {
  switch (s) {
    case GateStatus::GO: return "go";
    case GateStatus::NO_GO: return "no_go";
    case GateStatus::NEEDS_DATA: return "needs_data";
    default: return "unknown";
  }
}

// -------------------------------
// Issue record (machine readable)
// -------------------------------
struct Issue {
  IssueKind kind = IssueKind::InternalError;

  std::string code;
  std::string message;
  std::string field;

  bool has_value = false;
  double value = kUnset;

  bool has_limit = false;
  double limit = kUnset;

  std::string units;
};

// Convenience creators (keep callsites consistent)
inline Issue make_missing(std::string code,
                          std::string message,
                          std::string field = {}) {
  Issue i;
  i.kind = IssueKind::MissingData;
  i.code = std::move(code);
  i.message = std::move(message);
  i.field = std::move(field);
  return i;
}

inline Issue make_invalid(std::string code,
                          std::string message,
                          std::string field = {}) {
  Issue i;
  i.kind = IssueKind::InvalidInput;
  i.code = std::move(code);
  i.message = std::move(message);
  i.field = std::move(field);
  return i;
}

inline Issue make_violation(std::string code,
                            std::string message,
                            std::string field = {}) {
  Issue i;
  i.kind = IssueKind::ConstraintViolation;
  i.code = std::move(code);
  i.message = std::move(message);
  i.field = std::move(field);
  return i;
}

inline Issue make_internal(std::string code,
                           std::string message,
                           std::string field = {}) {
  Issue i;
  i.kind = IssueKind::InternalError;
  i.code = std::move(code);
  i.message = std::move(message);
  i.field = std::move(field);
  return i;
}

// -------------------------------
// Gate result (one gate evaluation)
// -------------------------------
struct GateResult {
  std::string gate_name;
  GateStatus status = GateStatus::NEEDS_DATA;
  std::vector<Issue> issues;
};

}  // namespace lift::closeout