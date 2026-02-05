#pragma once
/*
================================================================================
Legacy 4.1 — Core: Design Fingerprint Hash (Deterministic)
FILE: engine/core/design_hash.hpp
================================================================================
*/

#include <string>

#include "engine/core/design.hpp"
#include "engine/core/hashing.hpp"

namespace lift {

// Returns a deterministic hash of the design schema values.
Hash64 hash_design_schema(const Design& d);

// Convenience hex string (16 chars) for filenames/IDs.
std::string hash_design_schema_hex(const Design& d);

}  // namespace lift