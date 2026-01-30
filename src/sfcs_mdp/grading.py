from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class GradingBreakdown:
    determinism: float = 25.0
    scope: float = 20.0
    ci_faithfulness: float = 20.0
    behavior: float = 15.0
    verification: float = 15.0
    deliverables: float = 5.0

    @property
    def total(self) -> float:
        return (
            self.determinism
            + self.scope
            + self.ci_faithfulness
            + self.behavior
            + self.verification
            + self.deliverables
        )


def format_grading_footer(
    breakdown: GradingBreakdown | None = None,
    deductions: Sequence[str] | None = None,
    corrected_version: str | None = None,
) -> str:
    scores = breakdown or GradingBreakdown()
    total = scores.total
    if total < 0.0 or total > 100.0:
        raise ValueError("Total score must be between 0.00 and 100.00.")
    if total < 100.0 and corrected_version is None:
        raise ValueError("Corrected version required when total is below 100.00.")

    lines = [
        f"Total: {total:.2f}/100.00",
        "Breakdown:",
        f"  Determinism: {scores.determinism:.2f}/25.00",
        f"  Scope: {scores.scope:.2f}/20.00",
        f"  CI-faithfulness: {scores.ci_faithfulness:.2f}/20.00",
        f"  Behavior: {scores.behavior:.2f}/15.00",
        f"  Verification: {scores.verification:.2f}/15.00",
        f"  Deliverables: {scores.deliverables:.2f}/5.00",
        "Deductions:",
    ]

    deductions_list = list(deductions or [])
    if deductions_list:
        lines.extend([f"  - {deduction}" for deduction in deductions_list])
    else:
        lines.append("  - None.")

    if total < 100.0:
        lines.append("Corrected version:")
        assert corrected_version is not None
        lines.append(corrected_version)

    return "\n".join(lines)
