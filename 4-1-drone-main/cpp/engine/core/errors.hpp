#pragma once
/*
================================================================================
Fragment 1.9 — Core: Error Types (Hardened, Engine-Wide)
FILE: cpp/engine/core/errors.hpp

Purpose:
  - Provide uniform exception types so validation and runtime failures are:
      * searchable
      * catchable by category
      * reportable to UI cleanly

Hardening:
  - Small, dependency-free exceptions.
  - No iostream required.
  - Safe what() storage via std::string.
================================================================================
*/

#include <stdexcept>
#include <string>
#include <utility>

namespace lift {

// Base error for the engine.
class LiftError : public std::runtime_error {
 public:
  explicit LiftError(std::string msg) : std::runtime_error(std::move(msg)) {}
};

// Thrown when user/config input fails validation.
class ValidationError : public LiftError {
 public:
  explicit ValidationError(std::string msg) : LiftError(std::move(msg)) {}
};

// Thrown when a computation fails to converge or becomes numerically invalid.
class NumericalError : public LiftError {
 public:
  explicit NumericalError(std::string msg) : LiftError(std::move(msg)) {}
};

// Thrown when a required feature/module is unavailable in a build.
class NotImplementedError : public LiftError {
 public:
  explicit NotImplementedError(std::string msg) : LiftError(std::move(msg)) {}
};

// Thrown for I/O or filesystem related issues.
class IOError : public LiftError {
 public:
  explicit IOError(std::string msg) : LiftError(std::move(msg)) {}
};

} // namespace lift
