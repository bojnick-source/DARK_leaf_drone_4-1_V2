"""Robust parsing and validation of ratio strings such as ``4:1``.

Accepts many common human-written forms and normalises them to a canonical
``numerator:denominator`` representation with GCD-reduced integers.

Accepted delimiters / forms (after Unicode-dash normalisation)::

    4:1   4-1   4/1   4 / 1   4 to 1   4-to-1   4–1   4—1   8:2 (→ 4:1)

Rejected inputs::

    4::1   4-   to 1   4:0   4:1:2   4.0:1 (decimal parts)
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

# Unicode dashes that should be treated as a plain hyphen-minus:
# \u2013 en-dash, \u2014 em-dash, \u2015 horizontal bar,
# \u2012 figure dash, \u2010 hyphen
_UNICODE_DASHES = "\u2013\u2014\u2015\u2012\u2010"
_DASH_RE = re.compile(f"[{_UNICODE_DASHES}]")

# After normalisation the separator must be one of these tokens:
#   :   colon       (4:1)
#   /   slash       (4/1)
#   -to-            (4-to-1)
#   -   hyphen      (4-1) — accepted because it appears in repo naming (e.g. "4-1 drone")
_SEPARATOR_RE = re.compile(r"^(\d+)\s*(?::|/|-to-|-)\s*(\d+)$")

# "to" written as a word: "4 to 1"
_TO_WORD_RE = re.compile(r"^(\d+)\s+to\s+(\d+)$", re.IGNORECASE)


@dataclass(frozen=True)
class RatioResult:
    """Canonical ratio representation."""

    numerator: int
    denominator: int
    ratio_value: float
    ratio_string: str


def parse_ratio(raw: str) -> RatioResult:
    """Parse a human-written ratio string into a validated :class:`RatioResult`.

    Parameters
    ----------
    raw:
        The raw ratio string (e.g. ``"4:1"``, ``"8/2"``, ``"4 to 1"``).

    Returns
    -------
    RatioResult
        A normalised, GCD-reduced ratio.

    Raises
    ------
    ValueError
        If *raw* cannot be parsed or fails validation.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"ratio input must be a non-empty string, got {raw!r}")

    text = raw.strip()

    # 1. Normalise Unicode dashes → ASCII hyphen-minus
    text = _DASH_RE.sub("-", text)

    # 2. Try the general separator pattern first (:, /, -to-, -)
    m = _SEPARATOR_RE.match(text)
    if m is None:
        # 3. Try "N to M" with word separator
        m = _TO_WORD_RE.match(text)
    if m is None:
        raise ValueError(f"cannot parse ratio from {raw!r}")

    num_str, den_str = m.group(1), m.group(2)

    # Integer-only check (the regex already enforces \d+, so this is a safety net)
    numerator = int(num_str)
    denominator = int(den_str)

    # Validation
    if denominator == 0:
        raise ValueError(f"denominator must not be zero in ratio {raw!r}")
    if numerator <= 0:
        raise ValueError(f"numerator must be a positive integer in ratio {raw!r}")

    # GCD reduction
    g = math.gcd(numerator, denominator)
    numerator //= g
    denominator //= g

    return RatioResult(
        numerator=numerator,
        denominator=denominator,
        ratio_value=numerator / denominator,
        ratio_string=f"{numerator}:{denominator}",
    )
