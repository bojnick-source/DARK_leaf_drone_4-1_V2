"""Tests for future-proofing additions: enums, configs, protocols, deprecation."""

from __future__ import annotations

import warnings
from typing import Any

from sfcs_mdp.color_qa import ColorQaConfig, GroupThreshold
from sfcs_mdp.deprecation import deprecated
from sfcs_mdp.model import AcceptanceCriterionType, StepDisposition

# ---------------------------------------------------------------------------
# AcceptanceCriterionType enum
# ---------------------------------------------------------------------------


def test_acceptance_criterion_type_values() -> None:
    assert AcceptanceCriterionType.FILE_EXISTS.value == "file_exists"
    assert AcceptanceCriterionType.MANUAL_SIGNOFF.value == "manual_signoff"


def test_acceptance_criterion_type_is_str_enum() -> None:
    assert isinstance(AcceptanceCriterionType.FILE_EXISTS, str)
    assert AcceptanceCriterionType("file_exists") is AcceptanceCriterionType.FILE_EXISTS


# ---------------------------------------------------------------------------
# StepDisposition enum
# ---------------------------------------------------------------------------


def test_step_disposition_values() -> None:
    assert StepDisposition.PASS.value == "PASS"
    assert StepDisposition.FAIL.value == "FAIL"
    assert StepDisposition.SKIPPED.value == "SKIPPED"
    assert StepDisposition.OPTIONAL.value == "OPTIONAL"


def test_step_disposition_is_str_enum() -> None:
    assert isinstance(StepDisposition.PASS, str)
    assert StepDisposition("PASS") is StepDisposition.PASS


# ---------------------------------------------------------------------------
# AutopilotConfig
# ---------------------------------------------------------------------------


def test_autopilot_config_defaults() -> None:
    from reidce.flight_sim import AutopilotConfig

    config = AutopilotConfig()
    assert config.altitude_kp == 0.6
    assert config.throttle_trim == 0.5


def test_autopilot_config_custom_gains() -> None:
    from reidce.flight_sim import AutopilotConfig

    config = AutopilotConfig(altitude_kp=1.0, throttle_trim=0.6)
    assert config.altitude_kp == 1.0
    assert config.throttle_trim == 0.6


def test_autopilot_channel_uses_config() -> None:
    from reidce.flight_sim import AutopilotChannel, AutopilotConfig

    config = AutopilotConfig(altitude_kp=2.0, speed_kp=1.5)
    channel = AutopilotChannel(config=config)
    assert channel.altitude_pid.kp == 2.0
    assert channel.speed_pid.kp == 1.5


def test_autopilot_channel_default_config() -> None:
    from reidce.flight_sim import AutopilotChannel

    channel = AutopilotChannel()
    assert channel.altitude_pid.kp == 0.6
    assert channel.config.throttle_trim == 0.5


# ---------------------------------------------------------------------------
# ColorQaConfig
# ---------------------------------------------------------------------------


def test_color_qa_config_defaults() -> None:
    config = ColorQaConfig()
    assert config.grayscale.max == 1.0
    assert config.neutrals.mean == 0.8
    assert config.saturated.max == 3.0


def test_color_qa_config_custom_thresholds() -> None:
    config = ColorQaConfig(
        grayscale=GroupThreshold(max=2.0, mean=1.0),
    )
    assert config.grayscale.max == 2.0
    assert config.grayscale.mean == 1.0
    # Defaults preserved for others
    assert config.neutrals.max == 2.0


def test_color_qa_config_thresholds_for() -> None:
    from sfcs_mdp.color_qa import PatchGroup

    config = ColorQaConfig()
    assert config.thresholds_for(PatchGroup.GRAYSCALE).max == 1.0
    assert config.thresholds_for(PatchGroup.SATURATED).mean == 1.2


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


def test_simulator_protocol_structural_check() -> None:
    from reidce.protocols import Simulator

    class MockSim:
        def step(self, dt: float) -> None:
            pass

        def get_state(self) -> Any:
            return {}

    assert isinstance(MockSim(), Simulator)


def test_design_validator_protocol_structural_check() -> None:
    from reidce.protocols import DesignValidator

    class MockValidator:
        def validate(self, design: Any) -> bool:
            return True

        def describe(self) -> str:
            return "mock"

    assert isinstance(MockValidator(), DesignValidator)


def test_acceptance_evaluator_protocol_structural_check() -> None:
    from reidce.protocols import AcceptanceEvaluator

    class MockEvaluator:
        def evaluate(self, context: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
            return True, {}

    assert isinstance(MockEvaluator(), AcceptanceEvaluator)


def test_protocol_non_conformant_rejected() -> None:
    from reidce.protocols import Simulator

    class NotASim:
        def run(self) -> None:
            pass

    assert not isinstance(NotASim(), Simulator)


# ---------------------------------------------------------------------------
# Deprecation decorator
# ---------------------------------------------------------------------------


def test_deprecated_decorator_emits_warning() -> None:
    @deprecated("Use new_func instead", removal_version="1.0")
    def old_func() -> str:
        return "result"

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = old_func()
        assert result == "result"
        assert len(caught) == 1
        assert issubclass(caught[0].category, DeprecationWarning)
        assert "old_func" in str(caught[0].message)
        assert "Use new_func instead" in str(caught[0].message)
        assert "1.0" in str(caught[0].message)


def test_deprecated_decorator_without_version() -> None:
    @deprecated("Use something else")
    def legacy() -> int:
        return 42

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = legacy()
        assert result == 42
        assert len(caught) == 1
        assert "Scheduled for removal" not in str(caught[0].message)
