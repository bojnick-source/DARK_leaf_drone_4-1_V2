#pragma once
/*
================================================================================
Fragment 1.12 — Core: Design Fingerprint Hash (Deterministic)
FILE: cpp/engine/core/design_hash.hpp

Purpose:
  - Produce a deterministic geometry/config fingerprint for a Design that can be:
      * stored in CloseoutReport.geom_hash
      * used in CacheKey (geom_h)
      * used for artifact naming and result reproducibility

Key constraint:
  - This hash is schema-based (Design struct fields), NOT CAD-based.
    It stays valid even before PicoGK/OpenCascade are integrated.

Hardening:
  - Stable field order + tagged sections so additions are backwards detectable.
  - Floats hashed via canonical bit patterns (Fnv1a64::update_f64).
  - Vectors include length + per-element updates.

Output:
  - Hash64 + hex string helper.
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

