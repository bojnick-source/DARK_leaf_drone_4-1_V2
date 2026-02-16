from __future__ import annotations

import pytest
pytest.importorskip("numpy")
pytest.importorskip("scipy")

from ceai_topopt.topopt.gradcheck import gradcheck_compliance


def test_gradcheck_compliance_passes():
    res = gradcheck_compliance(
        nelx=20, nely=8,
        volfrac=0.4, penal=3.0, rmin=2.0,
        eps=1e-6, samples=12, seed=0,
    )
    assert res["rel_error_max"] < 2e-2, res
