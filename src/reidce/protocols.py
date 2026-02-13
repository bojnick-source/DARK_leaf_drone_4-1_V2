"""Protocol definitions for simulator and validator contracts.

These protocols define the expected interfaces for pluggable components,
enabling future extensibility without modifying existing implementations.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Simulator(Protocol):
    """Protocol for physics simulators (flight, drivetrain, gimbal, etc.)."""

    def step(self, dt: float) -> None:
        """Advance the simulation by one time step."""
        ...

    def get_state(self) -> Any:
        """Return the current simulation state."""
        ...


@runtime_checkable
class DesignValidator(Protocol):
    """Protocol for design validation checks."""

    def validate(self, design: Any) -> bool:
        """Return True if the design passes validation."""
        ...

    def describe(self) -> str:
        """Return a human-readable description of this validator."""
        ...


@runtime_checkable
class AcceptanceEvaluator(Protocol):
    """Protocol for acceptance criterion evaluators in the manufacturing pipeline."""

    def evaluate(self, context: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        """Evaluate a single acceptance criterion.

        Returns a tuple of (passed, result_details).
        """
        ...
