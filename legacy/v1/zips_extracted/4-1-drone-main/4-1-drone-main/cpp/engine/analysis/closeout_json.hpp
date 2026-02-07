#pragma once
/*
================================================================================
Fragment 2.3 — Analysis: Closeout JSON Serializer (Header)
FILE: cpp/engine/analysis/closeout_json.hpp

Purpose:
  - Deterministic JSON export of CloseoutReport for UI, auditing, and handoff.
  - No ambiguous fields: every sub-structure is explicitly serialized.
  - NaN ("unset") fields serialize as JSON null.

Hardening:
  - No third-party JSON dependency (simple, controlled emitter).
  - Stable key ordering so diffs between runs are readable.
================================================================================
*/

#include "engine/analysis/closeout_types.hpp"

#include <string>

namespace lift {

// Serialize CloseoutReport to JSON string.
std::string closeout_to_json(const CloseoutReport& r, int indent_spaces = 2);

// Write JSON to a file path. Returns true on success, false on failure.
bool write_closeout_json_file(const CloseoutReport& r,
                              const std::string& file_path,
                              int indent_spaces = 2);

} // namespace lift
