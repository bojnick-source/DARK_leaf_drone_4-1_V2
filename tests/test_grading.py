import pytest
from sfcs_mdp.grading import GradingBreakdown, format_grading_footer


def test_default_grading_footer() -> None:
    footer = format_grading_footer()
    assert "Total: 100.00/100.00" in footer
    assert "Breakdown:" in footer
    assert "Deductions:" in footer
    assert "  - None." in footer


def test_footer_requires_corrected_version_for_deductions() -> None:
    breakdown = GradingBreakdown(determinism=24.0)
    footer = format_grading_footer(
        breakdown=breakdown,
        deductions=["Determinism missing detail."],
        corrected_version="Corrected output.",
    )
    assert "Total: 99.00/100.00" in footer
    assert "Corrected version:" in footer
    assert "Corrected output." in footer


def test_footer_raises_without_corrected_version() -> None:
    breakdown = GradingBreakdown(determinism=24.0)
    with pytest.raises(ValueError):
        format_grading_footer(breakdown=breakdown)
