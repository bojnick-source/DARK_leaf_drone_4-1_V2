#pragma once
/*
================================================================================
Fragment 1.5 — Core: Deterministic Hashing Utilities (Hardened)
FILE: cpp/engine/core/hashing.hpp

Purpose:
  - Provide stable, deterministic 64-bit hashing for:
      * cache keys (settings/mission/geometry fingerprints)
      * artifact IDs (result file names)
      * reproducible eval signatures across platforms/builds

Design constraints:
  - Determinism > speed.
  - No dependence on std::hash (not stable across processes/platforms).
  - Avoid UB: use std::bit_cast for floating types, normalize NaNs.

Hardening:
  - Canonicalize -0.0 -> +0.0
  - Canonicalize NaN -> fixed quiet-NaN payload
  - Hash doubles via bit pattern AFTER canonicalization.
  - Provide explicit byte-order stable updates (we hash raw bytes in a defined way).

Notes:
  - This is NOT cryptographic. It is for cache identity and reproducibility.
================================================================================
*/

#include <array>
#include <bit>
#include <cstdint>
#include <cstring>
#include <string>
#include <string_view>
#include <type_traits>
#include <vector>

namespace lift {

// ----------------------------- Hash64 ----------------------------------------
struct Hash64 {
  uint64_t value = 0;

  constexpr bool operator==(const Hash64& o) const noexcept { return value == o.value; }
  constexpr bool operator!=(const Hash64& o) const noexcept { return value != o.value; }
};

// ----------------------------- FNV-1a 64 -------------------------------------
// Stable baseline hash. Not crypto. Excellent for deterministic cache keys.
class Fnv1a64 {
 public:
  static constexpr uint64_t kOffsetBasis = 14695981039346656037ull;
  static constexpr uint64_t kPrime       = 1099511628211ull;

  Fnv1a64() : h_(kOffsetBasis) {}
  explicit Fnv1a64(uint64_t seed) : h_(seed ? seed : kOffsetBasis) {}

  uint64_t value() const { return h_; }

  void reset(uint64_t seed = kOffsetBasis) { h_ = seed ? seed : kOffsetBasis; }

  void update_bytes(const void* data, size_t n);

  // Update with a single byte.
  void update_u8(uint8_t v) { update_bytes(&v, 1); }

  // Update with fixed-width integers in a stable way (little-endian encoding).
  void update_u32(uint32_t v) { update_le(v); }
  void update_u64(uint64_t v) { update_le(v); }
  void update_i32(int32_t v)  { update_le(static_cast<uint32_t>(v)); }
  void update_i64(int64_t v)  { update_le(static_cast<uint64_t>(v)); }

  // Update booleans explicitly.
  void update_bool(bool b) { update_u8(static_cast<uint8_t>(b ? 1 : 0)); }

  // Update strings with length delimiter to avoid ambiguity.
  void update_string(std::string_view s);

  // Update vectors of bytes with length delimiter.
  void update_bytes_vec(const std::vector<uint8_t>& v);

  // Update enums by underlying type.
  template <class E, std::enable_if_t<std::is_enum_v<E>, int> = 0>
  void update_enum(E e) {
    using U = std::underlying_type_t<E>;
    if constexpr (sizeof(U) <= 4) update_u32(static_cast<uint32_t>(static_cast<U>(e)));
    else update_u64(static_cast<uint64_t>(static_cast<U>(e)));
  }

  // Canonical float hashing.
  void update_f32(float x);
  void update_f64(double x);

 private:
  template <class T>
  void update_le(T v) {
    static_assert(std::is_integral_v<T> && (sizeof(T) == 4 || sizeof(T) == 8),
                  "update_le supports 32/64-bit integral types only");
    std::array<uint8_t, sizeof(T)> b{};
    // Encode in little-endian explicitly for platform stability.
    for (size_t i = 0; i < sizeof(T); ++i) {
      b[i] = static_cast<uint8_t>((static_cast<uint64_t>(v) >> (8 * i)) & 0xFFu);
    }
    update_bytes(b.data(), b.size());
  }

  uint64_t h_;
};

// Convenience: combine two hashes deterministically.
Hash64 hash_combine(Hash64 a, Hash64 b);

// Convenience: hex encoding for filenames/keys.
std::string hash_to_hex(Hash64 h);

}  // namespace lift

