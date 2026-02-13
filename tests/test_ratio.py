"""Tests for ratio parsing, validation, and normalisation."""

import pytest
from reidce.ratio import RatioResult, parse_ratio


# ---------------------------------------------------------------------------
# Accepted formats — all must resolve to 4:1
# ---------------------------------------------------------------------------
class TestAcceptedFormats:
    """Every common human-written form of '4:1' must parse correctly."""

    @pytest.mark.parametrize(
        "raw",
        [
            "4:1",
            "4-1",
            "4/1",
            "4 / 1",
            "4 to 1",
            "4-to-1",
            "4\u20131",       # en-dash
            "4\u20141",       # em-dash
        ],
    )
    def test_canonical_four_to_one(self, raw: str) -> None:
        r = parse_ratio(raw)
        assert r.numerator == 4
        assert r.denominator == 1
        assert r.ratio_value == 4.0
        assert r.ratio_string == "4:1"

    def test_spaces_around_colon(self) -> None:
        r = parse_ratio("  4 : 1  ")
        assert r == RatioResult(4, 1, 4.0, "4:1")

    def test_spaces_around_slash(self) -> None:
        r = parse_ratio(" 4 / 1 ")
        assert r == RatioResult(4, 1, 4.0, "4:1")

    def test_to_case_insensitive(self) -> None:
        r = parse_ratio("4 TO 1")
        assert r.ratio_string == "4:1"


# ---------------------------------------------------------------------------
# GCD reduction
# ---------------------------------------------------------------------------
class TestGCDReduction:
    """Fractions must be reduced to lowest terms."""

    def test_8_to_2_reduces(self) -> None:
        r = parse_ratio("8:2")
        assert r.numerator == 4
        assert r.denominator == 1
        assert r.ratio_value == 4.0
        assert r.ratio_string == "4:1"

    def test_12_to_3_reduces(self) -> None:
        r = parse_ratio("12:3")
        assert r.ratio_string == "4:1"

    def test_6_to_3_reduces(self) -> None:
        r = parse_ratio("6:3")
        assert r.ratio_string == "2:1"

    def test_3_to_9_reduces(self) -> None:
        r = parse_ratio("3:9")
        assert r.ratio_string == "1:3"
        assert r.ratio_value == pytest.approx(1 / 3)


# ---------------------------------------------------------------------------
# Non-4:1 ratios
# ---------------------------------------------------------------------------
class TestOtherRatios:
    """Arbitrary valid ratios must be handled."""

    def test_1_to_1(self) -> None:
        r = parse_ratio("1:1")
        assert r.ratio_value == 1.0

    def test_10_to_3(self) -> None:
        r = parse_ratio("10:3")
        assert r.ratio_value == pytest.approx(10 / 3)

    def test_large_ratio(self) -> None:
        r = parse_ratio("100:1")
        assert r.numerator == 100


# ---------------------------------------------------------------------------
# Rejection tests
# ---------------------------------------------------------------------------
class TestRejections:
    """Invalid inputs must raise ValueError."""

    @pytest.mark.parametrize(
        "raw",
        [
            "4::1",       # double colon
            "4-",         # trailing dash, no denominator
            "to 1",       # missing numerator
            "4:0",        # zero denominator
            "4:1:2",      # triple
            "4.0:1",      # decimal numerator
            "4:1.0",      # decimal denominator
            "",           # empty string
            "   ",        # whitespace only
            "abc",        # non-numeric
            "4",          # single number, no delimiter
            ":1",         # missing numerator with colon
        ],
    )
    def test_invalid_input_raises(self, raw: str) -> None:
        with pytest.raises(ValueError):
            parse_ratio(raw)

    def test_none_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_ratio(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# RatioResult is frozen / immutable
# ---------------------------------------------------------------------------
class TestRatioResultImmutable:
    def test_frozen(self) -> None:
        r = parse_ratio("4:1")
        with pytest.raises(AttributeError):
            r.numerator = 99  # type: ignore[misc]
