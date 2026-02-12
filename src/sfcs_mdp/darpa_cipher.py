from __future__ import annotations

import hashlib
import hmac
from typing import Any

# ---------------------------------------------------------------------------
# DARPA CyPhER Forge — digital-thread integrity component.
#
# CyPhER Forge is a DARPA programme that accelerates testing of complex
# systems via a continuous cipher loop between a physics-informed digital
# twin, an AI test agent, and the system under test.  See
# ``cypher_forge.py`` for the full orchestration layer.
#
# This module provides the HMAC-SHA-256 integrity mechanism used by the
# manufacturing digital thread to authenticate build artifacts.
# ---------------------------------------------------------------------------

DARPA_CIPHER_VERSION = "1"
DARPA_CIPHER_ALGORITHM = "HMAC-SHA-256"
DARPA_CIPHER_DOMAIN = "DARPA_LIFT_MFG_THREAD"


def _derive_key(build_id: str, rev_tag: str) -> bytes:
    """Derive a build-specific HMAC key from identity parameters.

    The key is deterministic so that any party with the same build_id and
    rev_tag can independently reproduce and verify the authentication tag.
    This is intentional: the DARPA LIFT digital thread requires reproducible
    integrity checks across manufacturing sites without shared secrets.
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
