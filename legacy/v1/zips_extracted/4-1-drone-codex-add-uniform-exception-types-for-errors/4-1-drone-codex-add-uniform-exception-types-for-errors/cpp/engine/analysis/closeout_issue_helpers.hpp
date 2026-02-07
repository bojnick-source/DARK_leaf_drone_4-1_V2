// FRAGMENT 1.20 — FILE: cpp/engine/analysis/closeout_types.hpp
#pragma once
/*
================================================================================
Fragment 1.20 — Analysis: Closeout Types (Uniform Issue Schema + Unset Semantics)
FILE: cpp/engine/analysis/closeout_types.hpp

Purpose:
  - Lock a single, typed schema for all Closeout findings:
      * Missing data (NEEDS_DATA)
      * Constraint violations (NO_GO)
      * Invalid inputs
      * Internal computation errors
  - Standardize "unset" numeric values across the engine using kUnset (NaN).

Design rules (hard lock):
  - NaN/kUnset means "unset / unknown / not computed"
  - Gates must never treat kUnset as 0.0
  - Missing inputs must surface as IssueKind::MissingData (NEEDS_DATA)

This header is dependency-light and safe to include everywhere.
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
  MissingData = 0,         // required input not provided -> NEEDS_DATA
  InvalidInput = 1,        // input violates validation constraints -> NO_GO
  ConstraintViolation = 2, // computed violation of a design/mission constraint -> NO_GO
  InternalError = 3        // unexpected engine error -> NO_GO (or NEEDS_DATA if recoverable)
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

  // Stable machine code, e.g.:
  //  - "mass.delta_total.unset"
  //  - "disk_area.invalid"
  //  - "hover.power.exceeds_limit"
  std::string code;

  // Human-readable explanation for UI/logs.
  std::string message;

  // Optional field path, e.g.:
  //  - "closeout.mass.delta_mass_total_kg"
  //  - "design.rotor_radius_m"
  std::string field;

  // Optional numeric value/context.
  // If has_value=false, ignore value.
  bool has_value = false;
  double value = kUnset;

  // Optional numeric limit/context.
  bool has_limit = false;
  double limit = kUnset;

  // Optional units tag for UI display (do not rely on this for computation).
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
  std::string gate_name;     // e.g. "mass_budget_gate"
  GateStatus status = GateStatus::NEEDS_DATA;

  // Issues produced by this gate (can be 0+).
  std::vector<Issue> issues;
};

}  // namespace lift::closeout
