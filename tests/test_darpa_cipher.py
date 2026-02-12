from sfcs_mdp.darpa_cipher import (
    DARPA_CIPHER_ALGORITHM,
    DARPA_CIPHER_DOMAIN,
    DARPA_CIPHER_VERSION,
    cipher_metadata,
    compute_hmac,
    verify_hmac,
)


def test_constants() -> None:
    assert DARPA_CIPHER_VERSION == "1"
    assert DARPA_CIPHER_ALGORITHM == "HMAC-SHA-256"
    assert DARPA_CIPHER_DOMAIN == "DARPA_LIFT_MFG_THREAD"


def test_compute_hmac_deterministic() -> None:
    data = b"hello world"
    tag_a = compute_hmac(data, "BUILD_0001", "REV_A")
    tag_b = compute_hmac(data, "BUILD_0001", "REV_A")
    assert tag_a == tag_b
    assert len(tag_a) == 64  # SHA-256 hex digest


def test_compute_hmac_varies_with_build() -> None:
    data = b"payload"
    tag_a = compute_hmac(data, "BUILD_0001", "REV_A")
    tag_b = compute_hmac(data, "BUILD_0002", "REV_A")
    assert tag_a != tag_b


def test_compute_hmac_varies_with_rev() -> None:
    data = b"payload"
    tag_a = compute_hmac(data, "BUILD_0001", "REV_A")
    tag_b = compute_hmac(data, "BUILD_0001", "REV_B")
    assert tag_a != tag_b


def test_verify_hmac_success() -> None:
    data = b"important artifact"
    tag = compute_hmac(data, "BUILD_X", "REV_1")
    assert verify_hmac(data, tag, "BUILD_X", "REV_1") is True


def test_verify_hmac_wrong_data() -> None:
    tag = compute_hmac(b"original", "B", "R")
    assert verify_hmac(b"tampered", tag, "B", "R") is False


def test_verify_hmac_wrong_tag() -> None:
    data = b"data"
    assert verify_hmac(data, "0" * 64, "B", "R") is False


def test_cipher_metadata() -> None:
    meta = cipher_metadata("BUILD_0001", "REV_A")
    assert meta["cipher_version"] == DARPA_CIPHER_VERSION
    assert meta["cipher_algorithm"] == DARPA_CIPHER_ALGORITHM
    assert meta["cipher_domain"] == DARPA_CIPHER_DOMAIN
    assert meta["build_id"] == "BUILD_0001"
    assert meta["rev_tag"] == "REV_A"
