#include "engine/core/hashing.hpp"

#include <bit>
#include <cmath>
#include <sstream>

namespace lift {

namespace {

constexpr uint64_t kCanonicalQuietNaNBits = 0x7ff8000000000000ull; // IEEE quiet NaN payload canonical
constexpr uint32_t kCanonicalQuietNaNBitsF = 0x7fc00000u;

template <class T>
T canonicalize_floating(T v) {
  if constexpr (std::is_same_v<T, float> || std::is_same_v<T, double>) {
    if (std::isnan(v)) {
      if constexpr (std::is_same_v<T, float>) {
        return std::bit_cast<T>(kCanonicalQuietNaNBitsF);
      } else {
        return std::bit_cast<T>(kCanonicalQuietNaNBits);
      }
    }
    if (v == static_cast<T>(-0.0)) return static_cast<T>(0.0);
  }
  return v;
}

} // namespace

void Fnv1a64::update_bytes(const void* data, size_t n) {
  const auto* p = static_cast<const uint8_t*>(data);
  if (p == nullptr || n == 0) return;

  for (size_t i = 0; i < n; ++i) {
    h_ ^= static_cast<uint64_t>(p[i]);
    h_ *= kPrime;
  }
}

void Fnv1a64::update_string(std::string_view s) {
  // Length delimiter (u64 LE), then bytes.
  update_u64(static_cast<uint64_t>(s.size()));
  if (!s.empty()) update_bytes(s.data(), s.size());
}

void Fnv1a64::update_bytes_vec(const std::vector<uint8_t>& v) {
  update_u64(static_cast<uint64_t>(v.size()));
  if (!v.empty()) update_bytes(v.data(), v.size());
}

void Fnv1a64::update_f32(float x) {
  const float c = canonicalize_floating(x);
  const uint32_t bits = std::bit_cast<uint32_t>(c);
  update_u32(bits);
}

void Fnv1a64::update_f64(double x) {
  const double c = canonicalize_floating(x);
  const uint64_t bits = std::bit_cast<uint64_t>(c);
  update_u64(bits);
}

Hash64 hash_combine(Hash64 a, Hash64 b) {
  // Deterministic combine (not crypto). Uses a common avalanche-ish mix.
  uint64_t x = a.value;
  uint64_t y = b.value;

  // Mix y into x.
  x ^= y + 0x9e3779b97f4a7c15ull + (x << 6) + (x >> 2);

  // Additional diffusion
  x ^= (x >> 33);
  x *= 0xff51afd7ed558ccdull;
  x ^= (x >> 33);
  x *= 0xc4ceb9fe1a85ec53ull;
  x ^= (x >> 33);

  return Hash64{x};
}

std::string hash_to_hex(Hash64 h) {
  static const char* kHex = "0123456789abcdef";
  std::string out;
  out.resize(16);
  uint64_t v = h.value;

  // Big-endian human string (most significant nibble first).
  for (int i = 15; i >= 0; --i) {
    out[15 - i] = kHex[(v >> (4ull * i)) & 0xFull];
  }
  return out;
}

}  // namespace lift
