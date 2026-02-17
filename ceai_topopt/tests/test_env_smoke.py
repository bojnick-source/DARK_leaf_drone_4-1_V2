def test_environment_smoke() -> None:
    # Ensures pytest exits cleanly even when scientific deps are unavailable and
    # dependent tests are skipped via importorskip.
    assert True
