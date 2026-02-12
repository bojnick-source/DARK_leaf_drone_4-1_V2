from __future__ import annotations

import hashlib
import hmac
from typing import Any

# ---------------------------------------------------------------------------
# DARPA LIFT programme cipher configuration
# Derived from DARPA LIFT digital-thread integrity requirements.
# Algorithm: HMAC-SHA-256 with a programme-scoped domain separator.
# ---------------------------------------------------------------------------

DARPA_CIPHER_VERSION = "1"
DARPA_CIPHER_ALGORITHM = "HMAC-SHA-256"
DARPA_CIPHER_DOMAIN = "DARPA_LIFT_MFG_THREAD"


def _derive_key(build_id: str, rev_tag: str) -> bytes:
    """Derive a build-specific HMAC key from identity parameters.

    The key is deterministic so that any party with the same build_id and
    rev_tag can independently reproduce the authentication tag.
    """
    seed = f"{DARPA_CIPHER_DOMAIN}:{DARPA_CIPHER_VERSION}:{build_id}:{rev_tag}"
    return hashlib.sha256(seed.encode("utf-8")).digest()


def compute_hmac(data: bytes, build_id: str, rev_tag: str) -> str:
    """Return a hex-encoded HMAC-SHA-256 tag for *data*."""
    key = _derive_key(build_id, rev_tag)
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def verify_hmac(data: bytes, expected_hex: str, build_id: str, rev_tag: str) -> bool:
    """Verify *data* against an expected hex HMAC tag (constant-time)."""
    key = _derive_key(build_id, rev_tag)
    computed = hmac.new(key, data, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, expected_hex)


def cipher_metadata(build_id: str, rev_tag: str) -> dict[str, Any]:
    """Return a JSON-serialisable dict describing the active cipher config."""
    return {
        "cipher_version": DARPA_CIPHER_VERSION,
        "cipher_algorithm": DARPA_CIPHER_ALGORITHM,
        "cipher_domain": DARPA_CIPHER_DOMAIN,
        "build_id": build_id,
        "rev_tag": rev_tag,
    }
