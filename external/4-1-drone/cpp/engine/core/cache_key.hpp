#pragma once
/*
================================================================================
Fragment 1.7 — Core: Deterministic Cache Keys (Mission + Settings Fingerprints)
FILE: cpp/engine/core/cache_key.hpp

Purpose:
  - Build reproducible, platform-stable cache/evaluation keys by hashing:
      * MissionSpec
      * EvalSettings (physics + numerical + optimizer knobs)
      * Optional geometry/model fingerprint (supplied by geometry layer)
  - Provide stable string IDs for artifacts, JSON, and UI.

Hardening:
  - No std::hash.
  - Floats hashed via canonical bit patterns (handled by Fnv1a64::update_f64/f32).
  - Strings length-delimited.
  - Stable ordering, stable delimiters.

Notes:
  - Geometry hash is not computed here (depends on PicoGK/OpenCascade). This
    layer just consumes a provided geometry hash string or Hash64.
================================================================================
*/

#include <string>
#include <string_view>

#include "engine/core/hashing.hpp"
#include "engine/core/mission_spec.hpp"
#include "engine/core/settings.hpp"

namespace lift {

struct CacheKey {
  Hash64 mission_h{};
  Hash64 settings_h{};
  Hash64 geom_h{};     // optional (0 allowed)
  Hash64 combined_h{}; // combined fingerprint

  // Hex helpers (16 chars each)
  std::string mission_hex() const { return hash_to_hex(mission_h); }
  std::string settings_hex() const { return hash_to_hex(settings_h); }
  std::string geom_hex() const { return hash_to_hex(geom_h); }
  std::string combined_hex() const { return hash_to_hex(combined_h); }

  // One stable "eval id" string for filenames/paths.
  // Format: m_<16>__s_<16>__g_<16>__e_<16>
  std::string eval_id() const;
};

// Hash mission/settings deterministically
Hash64 hash_mission(const MissionSpec& m);
Hash64 hash_settings(const EvalSettings& s);

// Create a CacheKey from mission/settings and optional geometry.
// geom may be omitted: geom_h will be 0 and still combined deterministically.
CacheKey make_cache_key(const MissionSpec& m,
                        const EvalSettings& s,
                        Hash64 geom_h = Hash64{0});

}  // namespace lift

