"""Tests for reidce.voice_interface — voice encoding/decoding interface."""

from reidce.voice_interface import (
    Phoneme,
    VoiceCodec,
    VoiceStream,
    VoiceToken,
    VoiceTranscript,
    encode_flight_metrics,
    encode_vehicle_params,
    roundtrip_verify,
)

# ── Phoneme ──────────────────────────────────────────────────────────────


def test_phoneme_creation() -> None:
    p = Phoneme(symbol="wun", duration_ms=120.0, frequency_hz=440.0)
    assert p.symbol == "wun"
    assert p.duration_ms == 120.0


# ── VoiceCodec encode/decode ─────────────────────────────────────────────


def test_codec_encode_single_numeric() -> None:
    codec = VoiceCodec()
    stream = codec.encode({"mass_kg": 2.5})
    assert isinstance(stream, VoiceStream)
    assert stream.token_count == 1
    assert stream.phoneme_count > 0


def test_codec_encode_multiple_fields() -> None:
    codec = VoiceCodec()
    data = {"mass_kg": 2.5, "speed_m_s": 30.0, "altitude_m": 100.0}
    stream = codec.encode(data)
    assert stream.token_count == 3


def test_codec_decode_numeric() -> None:
    codec = VoiceCodec()
    data = {"mass_kg": 2.5, "speed_m_s": 30.0}
    stream = codec.encode(data)
    decoded = codec.decode(stream)
    assert abs(decoded["mass_kg"] - 2.5) < 0.01
    assert abs(decoded["speed_m_s"] - 30.0) < 0.01


def test_codec_roundtrip_integer() -> None:
    codec = VoiceCodec()
    data = {"count": 42.0}
    stream = codec.encode(data)
    decoded = codec.decode(stream)
    assert abs(decoded["count"] - 42.0) < 0.01


def test_codec_roundtrip_negative() -> None:
    codec = VoiceCodec()
    data = {"offset": -3.14}
    stream = codec.encode(data)
    decoded = codec.decode(stream)
    assert abs(decoded["offset"] - (-3.14)) < 0.01


def test_codec_roundtrip_zero() -> None:
    codec = VoiceCodec()
    data = {"zero_val": 0.0}
    stream = codec.encode(data)
    decoded = codec.decode(stream)
    assert abs(decoded["zero_val"]) < 0.01


def test_codec_encode_string_value() -> None:
    codec = VoiceCodec()
    data = {"mode": "auto"}
    stream = codec.encode(data)
    assert stream.token_count == 1


def test_codec_transcribe() -> None:
    codec = VoiceCodec()
    data = {"mass_kg": 2.5}
    stream = codec.encode(data)
    transcript = codec.transcribe(stream)
    assert isinstance(transcript, VoiceTranscript)
    assert transcript.field_count == 1
    assert len(transcript.lines) == 1
    assert transcript.total_duration_ms > 0


def test_codec_to_dict() -> None:
    codec = VoiceCodec()
    d = codec.to_dict()
    assert d["schema"] == "dark/voice_codec/1.0"
    assert d["digit_alphabet_size"] == 10


# ── VoiceStream ──────────────────────────────────────────────────────────


def test_voice_stream_properties() -> None:
    codec = VoiceCodec()
    stream = codec.encode({"a": 1.0, "b": 2.0})
    assert stream.total_duration_ms > 0
    assert stream.token_count == 2


def test_voice_stream_to_dict() -> None:
    codec = VoiceCodec()
    stream = codec.encode({"x": 5.0})
    d = stream.to_dict()
    assert d["schema"] == "dark/voice_stream/1.0"
    assert d["token_count"] == 1


def test_voice_stream_metadata() -> None:
    codec = VoiceCodec()
    stream = codec.encode({"x": 1.0}, metadata={"source": "test"})
    assert stream.metadata["source"] == "test"


# ── VoiceToken ───────────────────────────────────────────────────────────


def test_voice_token_duration() -> None:
    codec = VoiceCodec()
    stream = codec.encode({"val": 123.456})
    token = stream.tokens[0]
    assert isinstance(token, VoiceToken)
    assert token.duration_ms > 0
    assert token.field_name == "val"


# ── Convenience functions ────────────────────────────────────────────────


def test_encode_vehicle_params() -> None:
    from reidce.flight_sim import VehicleParams
    params = VehicleParams()
    stream = encode_vehicle_params(params)
    assert stream.token_count == 6
    assert stream.metadata["source"] == "vehicle_params"


def test_encode_flight_metrics() -> None:
    metrics = {"max_speed": 25.0, "max_alt": 100.0, "score": 85.0}
    stream = encode_flight_metrics(metrics)
    assert stream.token_count == 3


def test_roundtrip_verify_success() -> None:
    data = {"mass_kg": 2.5, "speed": 30.0, "cd0": 0.04}
    assert roundtrip_verify(data) is True


def test_roundtrip_verify_multi_field() -> None:
    data = {
        "mass_kg": 2.5,
        "wing_area_m2": 0.12,
        "cd0": 0.04,
        "max_thrust_n": 50.0,
    }
    assert roundtrip_verify(data) is True


def test_voice_transcript_to_text() -> None:
    codec = VoiceCodec()
    stream = codec.encode({"x": 1.0, "y": 2.0})
    transcript = codec.transcribe(stream)
    text = transcript.to_text()
    assert "[x]" in text
    assert "[y]" in text
