#pragma once
/*
================================================================================
Legacy 4.1 — Analysis: Closeout JSON Serializer (Header)
FILE: engine/analysis/closeout_json.hpp
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