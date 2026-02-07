#pragma once

#include <cstdint>
#include <cmath>
#include <limits>
#include <string>
#include <vector>

namespace lift {

// ------------------------------
// Unset / NaN-as-unset convention
// ------------------------------
inline constexpr double kUnset = std::numeric_limits<double>::quiet_NaN();

inline bool is_set(double v) {
  return !std::isnan(v);
}

// ------------------------------
// Gate / Issue typing
// ------------------------------
enum class GateStatus : uint8_t {
  Go = 0,
  NoGo = 1,
  NeedsData = 2,
};

enum class IssueKind : uint8_t {
  MissingData = 0,        // required input not provided
  ConstraintViolation = 1,// violates a requirement/limit
  Infeasible = 2,         // model says cannot satisfy constraints
  ComputationError = 3,   // NaN/inf, divide-by-zero, overflow, etc.
  Warning = 4,            // non-blocking concern
};

enum class ErrorCode : uint16_t {
  None = 0,

  // Missing data
  MissingRequiredField = 100,
  MissingMassBreakdown = 101,
  MissingGeometry = 102,
  MissingPropulsion = 103,

  // Constraints / feasibility
  ExceedsMassCap = 200,
  ExceedsPowerCap = 201,
  ExceedsDiskLoading = 202,
  ExceedsThermal = 203,
  FailsLiftRatio = 204,
  NegativeMargin = 205,

  // Computation
  NaNDetected = 300,
  InfDetected = 301,
  DivideByZero = 302,
  Overflow = 303,
};

inline const char* to_string(GateStatus s) {
  switch (s) {
    case GateStatus::Go: return "GO";
    case GateStatus::NoGo: return "NO_GO";
    case GateStatus::NeedsData: return "NEEDS_DATA";
  }
  return "UNKNOWN";
}

inline const char* to_string(IssueKind k) {
  switch (k) {
    case IssueKind::MissingData: return "MISSING_DATA";
    case IssueKind::ConstraintViolation: return "CONSTRAINT_VIOLATION";
    case IssueKind::Infeasible: return "INFEASIBLE";
    case IssueKind::ComputationError: return "COMPUTATION_ERROR";
    case IssueKind::Warning: return "WARNING";
  }
  return "UNKNOWN";
}

inline const char* to_string(ErrorCode c) {
  switch (c) {
    case ErrorCode::None: return "NONE";

    case ErrorCode::MissingRequiredField: return "MISSING_REQUIRED_FIELD";
    case ErrorCode::MissingMassBreakdown: return "MISSING_MASS_BREAKDOWN";
    case ErrorCode::MissingGeometry: return "MISSING_GEOMETRY";
    case ErrorCode::MissingPropulsion: return "MISSING_PROPULSION";

    case ErrorCode::ExceedsMassCap: return "EXCEEDS_MASS_CAP";
    case ErrorCode::ExceedsPowerCap: return "EXCEEDS_POWER_CAP";
    case ErrorCode::ExceedsDiskLoading: return "EXCEEDS_DISK_LOADING";
    case ErrorCode::ExceedsThermal: return "EXCEEDS_THERMAL";
    case ErrorCode::FailsLiftRatio: return "FAILS_LIFT_RATIO";
    case ErrorCode::NegativeMargin: return "NEGATIVE_MARGIN";

    case ErrorCode::NaNDetected: return "NAN_DETECTED";
    case ErrorCode::InfDetected: return "INF_DETECTED";
    case ErrorCode::DivideByZero: return "DIVIDE_BY_ZERO";
    case ErrorCode::Overflow: return "OVERFLOW";
  }
  return "UNKNOWN";
}

// A single typed finding produced by evaluation.
struct Issue {
  IssueKind kind = IssueKind::Warning;
  GateStatus gate = GateStatus::Go;     // which way this pushes the gate
  ErrorCode code = ErrorCode::None;

  std::string where;   // e.g. "mass_gate", "disk_area", "power_budget"
  std::string field;   // optional: input/field name, e.g. "delta_mass_total_kg"
  std::string message; // human-readable
};

inline Issue make_missing(std::string where, std::string field, std::string message) {
  Issue i;
  i.kind = IssueKind::MissingData;
  i.gate = GateStatus::NeedsData;
  i.code = ErrorCode::MissingRequiredField;
  i.where = std::move(where);
  i.field = std::move(field);
  i.message = std::move(message);
  return i;
}

inline Issue make_violation(std::string where, ErrorCode code, std::string message) {
  Issue i;
  i.kind = IssueKind::ConstraintViolation;
  i.gate = GateStatus::NoGo;
  i.code = code;
  i.where = std::move(where);
  i.message = std::move(message);
  return i;
}

inline Issue make_compute_error(std::string where, ErrorCode code, std::string message) {
  Issue i;
  i.kind = IssueKind::ComputationError;
  i.gate = GateStatus::NoGo;
  i.code = code;
  i.where = std::move(where);
  i.message = std::move(message);
  return i;
}

// Gate aggregation result.
struct GateResult {
  GateStatus status = GateStatus::Go;
  std::vector<Issue> issues;
};

inline void add_issue(GateResult& gr, Issue issue) {
  // Escalation: NO_GO dominates NEEDS_DATA dominates GO.
  if (issue.gate == GateStatus::NoGo) gr.status = GateStatus::NoGo;
  else if (issue.gate == GateStatus::NeedsData && gr.status != GateStatus::NoGo)
    gr.status = GateStatus::NeedsData;

  gr.issues.push_back(std::move(issue));
}

} // namespace lift
