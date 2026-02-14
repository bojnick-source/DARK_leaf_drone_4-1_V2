"""Tests for reidce.code_gen — AI code generation engine."""

import ast

from reidce.code_gen import (
    CodeGenEngine,
    CodeTemplate,
    GeneratedCode,
    generate_analysis_script,
    generate_drone_config,
    generate_simulation_script,
)

# ── CodeTemplate ─────────────────────────────────────────────────────────


def test_code_template_render() -> None:
    tmpl = CodeTemplate(
        name="test",
        category="test",
        description="test template",
        template="x = {value}",
        parameter_names=["value"],
    )
    rendered = tmpl.render({"value": 42})
    assert "x = 42" in rendered


# ── CodeGenEngine ────────────────────────────────────────────────────────


def test_engine_has_builtin_templates() -> None:
    engine = CodeGenEngine()
    names = [t["name"] for t in engine.list_templates()]
    assert "drone_config" in names
    assert "simulation_script" in names
    assert "analysis_script" in names
    assert "blueprint_script" in names


def test_engine_generate_drone_config() -> None:
    engine = CodeGenEngine()
    result = engine.generate("drone_config", {
        "config_name": "test_quad",
        "mass_kg": 2.5,
        "wing_area_m2": 0.12,
        "cd0": 0.04,
        "max_thrust_n": 50.0,
        "max_tilt_rad": 0.6,
        "max_speed_m_s": 30.0,
    })
    assert isinstance(result, GeneratedCode)
    assert result.is_valid
    assert result.validation_error == ""
    assert result.line_count > 5
    assert "VehicleParams" in result.source


def test_engine_generate_simulation_script() -> None:
    engine = CodeGenEngine()
    result = engine.generate("simulation_script", {
        "mass_kg": 2.5,
        "max_thrust_n": 50.0,
        "max_speed_m_s": 30.0,
        "initial_altitude_m": 0.0,
        "initial_speed_m_s": 5.0,
        "target_altitude_m": 50.0,
        "target_speed_m_s": 12.0,
        "duration_s": 20.0,
        "dt_s": 0.05,
    })
    assert result.is_valid
    assert "simulate_flight" in result.source


def test_engine_generate_analysis_script() -> None:
    engine = CodeGenEngine()
    result = engine.generate("analysis_script", {
        "mass_kg": 2.5,
        "wing_area_m2": 0.12,
        "cd0": 0.04,
        "max_thrust_n": 50.0,
        "max_tilt_rad": 0.6,
        "max_speed_m_s": 30.0,
        "max_iterations": 5,
        "convergence_score": 85.0,
    })
    assert result.is_valid
    assert "run_design_loop" in result.source


def test_engine_generate_blueprint_script() -> None:
    engine = CodeGenEngine()
    result = engine.generate("blueprint_script", {
        "title": "Test Blueprint",
        "sheet_width_mm": 841.0,
        "sheet_height_mm": 594.0,
        "arm_count": 4,
        "arm_length_m": 0.30,
        "hub_radius_m": 0.06,
        "prop_radius_m": 0.12,
        "scale": 2.0,
    })
    assert result.is_valid
    assert "generate_drone_blueprint" in result.source


def test_engine_register_custom_template() -> None:
    engine = CodeGenEngine()
    tmpl = CodeTemplate(
        name="custom",
        category="custom",
        description="Custom template",
        template="result = {value} + 1",
        parameter_names=["value"],
    )
    engine.register_template(tmpl)
    result = engine.generate("custom", {"value": 10})
    assert result.is_valid
    assert "result = 10 + 1" in result.source


def test_engine_unknown_template_raises() -> None:
    engine = CodeGenEngine()
    try:
        engine.generate("nonexistent", {})
        raise AssertionError("Should have raised KeyError")
    except KeyError:
        pass


def test_engine_to_dict() -> None:
    engine = CodeGenEngine()
    d = engine.to_dict()
    assert d["schema"] == "dark/code_gen_engine/1.0"
    assert d["template_count"] >= 4


# ── Convenience generators ───────────────────────────────────────────────


def test_generate_drone_config() -> None:
    result = generate_drone_config(config_name="competition", mass_kg=3.0)
    assert result.is_valid
    assert result.template_name == "drone_config"
    assert "3.0" in result.source
    # Validate it parses as Python
    ast.parse(result.source)


def test_generate_simulation_script() -> None:
    result = generate_simulation_script(duration_s=30.0)
    assert result.is_valid
    assert result.template_name == "simulation_script"
    ast.parse(result.source)


def test_generate_analysis_script() -> None:
    result = generate_analysis_script(max_iterations=10)
    assert result.is_valid
    assert result.template_name == "analysis_script"
    ast.parse(result.source)


def test_generated_code_category() -> None:
    result = generate_drone_config()
    assert result.category == "configuration"


def test_generated_code_parameters_recorded() -> None:
    result = generate_drone_config(mass_kg=5.0)
    assert result.parameters["mass_kg"] == 5.0
