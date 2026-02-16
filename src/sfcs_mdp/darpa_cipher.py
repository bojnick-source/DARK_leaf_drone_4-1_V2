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
    """Return a JSON-serializable dict describing the active cipher config."""
    _validate_identity(build_id, rev_tag)
    return {
        "cipher_version": DARPA_CIPHER_VERSION,
        "cipher_algorithm": DARPA_CIPHER_ALGORITHM,
        "cipher_domain": DARPA_CIPHER_DOMAIN,
        "build_id": build_id,
        "rev_tag": rev_tag,
    }


# ---------------------------------------------------------------------------
# Input validation — hardened against all malformed inputs
# ---------------------------------------------------------------------------

def _validate_identity(build_id: str, rev_tag: str) -> None:
    """Validate build_id and rev_tag are non-empty ASCII strings."""
    if not isinstance(build_id, str) or not build_id.strip():
        raise ValueError("build_id must be a non-empty string")
    if not isinstance(rev_tag, str) or not rev_tag.strip():
        raise ValueError("rev_tag must be a non-empty string")
    try:
        build_id.encode("ascii")
        rev_tag.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError("build_id and rev_tag must be ASCII-safe")


def _validate_data(data: bytes) -> None:
    """Validate data payload."""
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("data must be bytes or bytearray")
    if len(data) == 0:
        raise ValueError("data must not be empty")


# ---------------------------------------------------------------------------
# Hardened versions with full validation
# ---------------------------------------------------------------------------

def compute_hmac_strict(data: bytes, build_id: str, rev_tag: str) -> str:
    """Validated HMAC computation — rejects all malformed inputs."""
    _validate_identity(build_id, rev_tag)
    _validate_data(data)
    return compute_hmac(data, build_id, rev_tag)


def verify_hmac_strict(
    data: bytes, expected_hex: str, build_id: str, rev_tag: str,
) -> bool:
    """Validated HMAC verification with strict input checks."""
    _validate_identity(build_id, rev_tag)
    _validate_data(data)
    if not isinstance(expected_hex, str) or len(expected_hex) != 64:
        raise ValueError("expected_hex must be a 64-character hex string")
    try:
        bytes.fromhex(expected_hex)
    except ValueError:
        raise ValueError("expected_hex contains invalid hex characters")
    return verify_hmac(data, expected_hex, build_id, rev_tag)


# ---------------------------------------------------------------------------
# Batch operations — manufacturing digital-thread pipeline
# ---------------------------------------------------------------------------

def batch_compute_hmac(
    artifacts: list[tuple[str, bytes]],
    build_id: str,
    rev_tag: str,
) -> dict[str, str]:
    """Compute HMACs for a batch of named artifacts.

    Parameters
    ----------
    artifacts : list of (artifact_name, data) tuples
    build_id, rev_tag : identity parameters for key derivation

    Returns a dict mapping artifact_name -> hex HMAC tag.
    The key is derived once and reused across all artifacts.
    """
    _validate_identity(build_id, rev_tag)
    key = _derive_key(build_id, rev_tag)
    results: dict[str, str] = {}
    for name, data in artifacts:
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"artifact name must be a non-empty string, got {name!r}")
        _validate_data(data)
        results[name] = hmac.new(key, data, hashlib.sha256).hexdigest()
    return results


def batch_verify_hmac(
    artifacts: list[tuple[str, bytes, str]],
    build_id: str,
    rev_tag: str,
) -> dict[str, bool]:
    """Verify HMACs for a batch of named artifacts.

    Parameters
    ----------
    artifacts : list of (artifact_name, data, expected_hex) tuples

    Returns a dict mapping artifact_name -> bool (verified or not).
    All comparisons are constant-time.
    """
    _validate_identity(build_id, rev_tag)
    key = _derive_key(build_id, rev_tag)
    results: dict[str, bool] = {}
    for name, data, expected_hex in artifacts:
        if not isinstance(data, (bytes, bytearray)) or len(data) == 0:
            results[name] = False
            continue
        computed = hmac.new(key, data, hashlib.sha256).hexdigest()
        results[name] = hmac.compare_digest(computed, expected_hex)
    return results


# ---------------------------------------------------------------------------
# Chain-of-custody — ordered verification of manufacturing stages
# ---------------------------------------------------------------------------

def chain_of_custody_verify(
    stages: list[dict[str, Any]],
    build_id: str,
) -> dict[str, Any]:
    """Verify an ordered chain of manufacturing stages.

    Each stage dict must contain:
      - "rev_tag": str
      - "data": bytes
      - "hmac": str (hex)

    Returns a summary with per-stage results and overall chain integrity.
    """
    _validate_identity(build_id, "chain_check")
    if not stages:
        raise ValueError("stages list must not be empty")

    stage_results: list[dict[str, Any]] = []
    chain_valid = True

    for idx, stage in enumerate(stages):
        rev_tag = stage.get("rev_tag", "")
        data = stage.get("data", b"")
        expected = stage.get("hmac", "")
        stage_name = stage.get("name", f"stage_{idx}")

        try:
            _validate_identity(build_id, rev_tag)
            _validate_data(data)
            verified = verify_hmac(data, expected, build_id, rev_tag)
        except (ValueError, TypeError):
            verified = False

        if not verified:
            chain_valid = False

        stage_results.append({
            "stage": stage_name,
            "rev_tag": rev_tag,
            "verified": verified,
            "order": idx,
        })

    return {
        "build_id": build_id,
        "chain_length": len(stages),
        "all_verified": chain_valid,
        "stages": stage_results,
    }
