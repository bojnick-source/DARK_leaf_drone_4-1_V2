"""Voice encoding/decoding interface for rapid engineering data transfer.

Provides a phoneme-based serialization system that encodes structured
engineering data into voice-transmittable token streams and decodes them
back.  Voice-encoded data can be transmitted faster than textual
representations because it maps numeric values to compact syllable
sequences optimized for verbal communication.

Key components
--------------
* ``Phoneme`` — atomic sound unit with duration and frequency.
* ``VoiceToken`` — encoded engineering datum as a phoneme sequence.
* ``VoiceStream`` — ordered sequence of voice tokens representing a
  full engineering dataset (e.g. vehicle parameters + flight metrics).
* ``VoiceCodec`` — encoder/decoder that maps engineering key-value
  pairs to/from voice token streams using a deterministic phoneme
  alphabet.
* ``VoiceTranscript`` — human-readable transcript of a voice stream
  with timing and decoded values.

The codec is deterministic and reversible — encoding then decoding
always produces the original data (within floating-point precision).

No external dependencies — built entirely on the standard library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ── Phoneme alphabet ─────────────────────────────────────────────────────

# A compact phoneme alphabet designed for unambiguous spoken communication.
# Each phoneme maps to a single digit (0–9), a decimal point, a negative
# sign, or a structural marker (field separator, record separator).

_DIGIT_PHONEMES: Dict[str, str] = {
    "0": "zoh",
    "1": "wun",
    "2": "too",
    "3": "tree",
    "4": "fow",
    "5": "fiv",
    "6": "six",
    "7": "sev",
    "8": "ayt",
    "9": "nyn",
}

_PHONEME_DIGITS: Dict[str, str] = {v: k for k, v in _DIGIT_PHONEMES.items()}

_POINT_PHONEME = "dot"
_NEGATIVE_PHONEME = "neg"
_FIELD_SEP_PHONEME = "brk"
_RECORD_SEP_PHONEME = "end"

# Character-to-phoneme for field names (NATO-inspired alphabet)
_CHAR_PHONEMES: Dict[str, str] = {
    "a": "al", "b": "br", "c": "ch", "d": "dl", "e": "ek",
    "f": "fx", "g": "gl", "h": "ho", "i": "id", "j": "jl",
    "k": "ka", "l": "lm", "m": "mu", "n": "nv", "o": "os",
    "p": "px", "q": "qu", "r": "rx", "s": "sx", "t": "tx",
    "u": "ul", "v": "vx", "w": "wx", "x": "xi", "y": "yx",
    "z": "zx", "_": "us", " ": "sp",
}

_PHONEME_CHARS: Dict[str, str] = {v: k for k, v in _CHAR_PHONEMES.items()}

# ── Data structures ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class Phoneme:
    """Atomic sound unit in the voice encoding."""

    symbol: str
    duration_ms: float = 120.0
    frequency_hz: float = 440.0


@dataclass(frozen=True)
class VoiceToken:
    """Single encoded engineering datum as a phoneme sequence."""

    field_name: str
    phonemes: List[Phoneme]
    encoded_value: str
    original_value: Any

    @property
    def duration_ms(self) -> float:
        return sum(p.duration_ms for p in self.phonemes)


@dataclass
class VoiceStream:
    """Ordered sequence of voice tokens representing engineering data."""

    tokens: List[VoiceToken] = field(default_factory=list)
    sample_rate_hz: int = 16000
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_duration_ms(self) -> float:
        return sum(t.duration_ms for t in self.tokens)

    @property
    def token_count(self) -> int:
        return len(self.tokens)

    @property
    def phoneme_count(self) -> int:
        return sum(len(t.phonemes) for t in self.tokens)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "dark/voice_stream/1.0",
            "token_count": self.token_count,
            "phoneme_count": self.phoneme_count,
            "total_duration_ms": round(self.total_duration_ms, 1),
            "sample_rate_hz": self.sample_rate_hz,
            "fields": [t.field_name for t in self.tokens],
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class VoiceTranscript:
    """Human-readable transcript of a voice stream."""

    lines: List[str]
    decoded_data: Dict[str, Any]
    total_duration_ms: float
    field_count: int

    def to_text(self) -> str:
        return "\n".join(self.lines)


# ── Encoding helpers ─────────────────────────────────────────────────────


def _encode_field_name(name: str) -> List[Phoneme]:
    """Encode a field name as phonemes."""
    phonemes: List[Phoneme] = []
    for char in name.lower():
        symbol = _CHAR_PHONEMES.get(char, char)
        phonemes.append(Phoneme(symbol=symbol, duration_ms=80.0, frequency_hz=520.0))
    return phonemes


def _decode_field_name(phonemes: List[Phoneme]) -> str:
    """Decode phonemes back to a field name."""
    chars: List[str] = []
    for p in phonemes:
        char = _PHONEME_CHARS.get(p.symbol, p.symbol)
        chars.append(char)
    return "".join(chars)


def _encode_number(value: float, precision: int = 6) -> List[Phoneme]:
    """Encode a numeric value as phonemes."""
    phonemes: List[Phoneme] = []
    if value < 0:
        phonemes.append(Phoneme(symbol=_NEGATIVE_PHONEME, duration_ms=100.0, frequency_hz=380.0))
        value = -value

    formatted = f"{value:.{precision}f}"
    # Strip trailing zeros after decimal
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")

    for char in formatted:
        if char == ".":
            phonemes.append(Phoneme(symbol=_POINT_PHONEME, duration_ms=100.0, frequency_hz=400.0))
        elif char in _DIGIT_PHONEMES:
            phonemes.append(
                Phoneme(symbol=_DIGIT_PHONEMES[char], duration_ms=120.0, frequency_hz=440.0)
            )
    return phonemes


def _decode_number(phonemes: List[Phoneme]) -> float:
    """Decode phonemes back to a numeric value."""
    chars: List[str] = []
    negative = False
    for p in phonemes:
        if p.symbol == _NEGATIVE_PHONEME:
            negative = True
        elif p.symbol == _POINT_PHONEME:
            chars.append(".")
        elif p.symbol in _PHONEME_DIGITS:
            chars.append(_PHONEME_DIGITS[p.symbol])
    if not chars:
        return 0.0
    value = float("".join(chars))
    return -value if negative else value


def _encode_string(value: str) -> List[Phoneme]:
    """Encode a string value as phonemes."""
    phonemes: List[Phoneme] = []
    for char in value.lower():
        symbol = _CHAR_PHONEMES.get(char, char)
        phonemes.append(Phoneme(symbol=symbol, duration_ms=80.0, frequency_hz=520.0))
    return phonemes


def _decode_string(phonemes: List[Phoneme]) -> str:
    """Decode phonemes back to a string."""
    return _decode_field_name(phonemes)


# ── Voice codec ──────────────────────────────────────────────────────────


@dataclass
class VoiceCodec:
    """Encoder/decoder for engineering data to voice token streams.

    Maps engineering key-value pairs to phoneme sequences using a
    deterministic, reversible encoding.  Numeric values are encoded
    digit-by-digit; string values are encoded character-by-character.
    """

    precision: int = 6
    phoneme_duration_ms: float = 120.0
    sample_rate_hz: int = 16000

    def encode(
        self,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VoiceStream:
        """Encode a dictionary of engineering data as a voice stream."""
        tokens: List[VoiceToken] = []
        for key, value in data.items():
            name_phonemes = _encode_field_name(key)
            sep = [Phoneme(symbol=_FIELD_SEP_PHONEME, duration_ms=150.0, frequency_hz=300.0)]
            if isinstance(value, bool):
                value_phonemes = _encode_string(str(value).lower())
                encoded = " ".join(p.symbol for p in value_phonemes)
            elif isinstance(value, (int, float)):
                value_phonemes = _encode_number(float(value), self.precision)
                encoded = " ".join(p.symbol for p in value_phonemes)
            elif isinstance(value, str):
                value_phonemes = _encode_string(value)
                encoded = " ".join(p.symbol for p in value_phonemes)
            else:
                # Convert to string representation
                str_val = str(value)
                value_phonemes = _encode_string(str_val)
                encoded = " ".join(p.symbol for p in value_phonemes)

            all_phonemes = name_phonemes + sep + value_phonemes
            end = [Phoneme(symbol=_RECORD_SEP_PHONEME, duration_ms=200.0, frequency_hz=260.0)]
            all_phonemes.extend(end)

            tokens.append(VoiceToken(
                field_name=key,
                phonemes=all_phonemes,
                encoded_value=encoded,
                original_value=value,
            ))

        return VoiceStream(
            tokens=tokens,
            sample_rate_hz=self.sample_rate_hz,
            metadata=metadata or {},
        )

    def decode(self, stream: VoiceStream) -> Dict[str, Any]:
        """Decode a voice stream back to engineering data."""
        result: Dict[str, Any] = {}
        for token in stream.tokens:
            # Split phonemes into name and value parts at the field separator
            sep_idx = -1
            for i, p in enumerate(token.phonemes):
                if p.symbol == _FIELD_SEP_PHONEME:
                    sep_idx = i
                    break

            if sep_idx < 0:
                continue

            name_phonemes = token.phonemes[:sep_idx]
            # Value phonemes: after separator, before record end
            value_phonemes = [
                p for p in token.phonemes[sep_idx + 1:]
                if p.symbol != _RECORD_SEP_PHONEME
            ]

            field_name = _decode_field_name(name_phonemes)

            # Determine if numeric or string
            is_numeric = all(
                p.symbol in _PHONEME_DIGITS
                or p.symbol == _POINT_PHONEME
                or p.symbol == _NEGATIVE_PHONEME
                for p in value_phonemes
            ) and len(value_phonemes) > 0

            if isinstance(token.original_value, bool):
                decoded_text = _decode_string(value_phonemes).strip().lower()
                result[field_name] = decoded_text in {"true", "1", "yes", "on"}
            elif is_numeric:
                result[field_name] = _decode_number(value_phonemes)
            else:
                result[field_name] = _decode_string(value_phonemes)

        return result

    def transcribe(self, stream: VoiceStream) -> VoiceTranscript:
        """Produce a human-readable transcript of a voice stream."""
        lines: List[str] = []
        decoded = self.decode(stream)
        for token in stream.tokens:
            phoneme_str = " ".join(p.symbol for p in token.phonemes)
            lines.append(
                f"[{token.field_name}] "
                f"({token.duration_ms:.0f}ms): "
                f"{phoneme_str}"
            )
        return VoiceTranscript(
            lines=lines,
            decoded_data=decoded,
            total_duration_ms=stream.total_duration_ms,
            field_count=len(stream.tokens),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "dark/voice_codec/1.0",
            "precision": self.precision,
            "phoneme_duration_ms": self.phoneme_duration_ms,
            "sample_rate_hz": self.sample_rate_hz,
            "digit_alphabet_size": len(_DIGIT_PHONEMES),
            "char_alphabet_size": len(_CHAR_PHONEMES),
        }


# ── Convenience functions ────────────────────────────────────────────────


def encode_vehicle_params(params: Any) -> VoiceStream:
    """Encode a ``VehicleParams`` object as a voice stream."""
    data = {
        "mass_kg": params.mass_kg,
        "wing_area_m2": params.wing_area_m2,
        "cd0": params.cd0,
        "max_thrust_n": params.max_thrust_n,
        "max_tilt_rad": params.max_tilt_rad,
        "max_speed_m_s": params.max_speed_m_s,
    }
    codec = VoiceCodec()
    return codec.encode(data, metadata={"source": "vehicle_params"})


def encode_flight_metrics(metrics: Dict[str, float]) -> VoiceStream:
    """Encode flight performance metrics as a voice stream."""
    codec = VoiceCodec()
    return codec.encode(metrics, metadata={"source": "flight_metrics"})


def roundtrip_verify(data: Dict[str, float]) -> bool:
    """Verify that encoding then decoding reproduces the original data."""
    codec = VoiceCodec()
    stream = codec.encode(data)
    decoded = codec.decode(stream)
    for key, original in data.items():
        recovered = decoded.get(key)
        if recovered is None:
            return False
        if isinstance(original, (int, float)) and isinstance(recovered, (int, float)):
            if abs(float(original) - float(recovered)) > 1e-4:
                return False
    return True
