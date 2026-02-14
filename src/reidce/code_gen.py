"""AI code generation engine for drone engineering workflows.

Generates syntactically valid, runnable Python code for drone
configurations, simulation setups, analysis scripts, and engineering
calculations.  The engine uses template composition with parametric
substitution — no external API calls.

Key components
--------------
* ``CodeTemplate`` — named template with parameter placeholders.
* ``GeneratedCode`` — validated output with source, AST check, and metadata.
* ``CodeGenEngine`` — registry of templates + parametric code generation
  with automatic ``ast.parse`` validation.
* ``generate_drone_config`` — produce a ``VehicleParams`` configuration script.
* ``generate_simulation_script`` — produce a flight-sim invocation script.
* ``generate_analysis_script`` — produce an engineering analysis pipeline.
* ``generate_blueprint_script`` — produce a blueprint generation script.

All generated code is validated via ``ast.parse`` before being returned.
No external dependencies — built entirely on the standard library.
"""

from __future__ import annotations

import ast
import textwrap
from dataclasses import dataclass, field
from typing import Any, Dict, List

# ── Code template ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CodeTemplate:
    """Named code template with parameter placeholders."""

    name: str
    category: str
    description: str
    template: str
    parameter_names: List[str]
    imports: List[str] = field(default_factory=list)

    def render(self, params: Dict[str, Any]) -> str:
        """Render the template by substituting parameters."""
        code = self.template
        for name in self.parameter_names:
            placeholder = "{" + name + "}"
            value = params.get(name, f"<{name}>")
            code = code.replace(placeholder, str(value))
        return code


# ── Generated code ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class GeneratedCode:
    """Validated generated code output."""

    source: str
    template_name: str
    is_valid: bool
    validation_error: str
    parameters: Dict[str, Any]
    line_count: int
    category: str


def _validate_python(source: str) -> tuple[bool, str]:
    """Validate Python source via ast.parse."""
    try:
        ast.parse(source)
        return True, ""
    except SyntaxError as exc:
        return False, f"SyntaxError at line {exc.lineno}: {exc.msg}"


# ── Built-in templates ───────────────────────────────────────────────────

_DRONE_CONFIG_TEMPLATE = textwrap.dedent("""\
    \"\"\"Auto-generated drone configuration — {config_name}.\"\"\"

    from reidce.flight_sim import VehicleParams

    config = VehicleParams(
        mass_kg={mass_kg},
        wing_area_m2={wing_area_m2},
        cd0={cd0},
        max_thrust_n={max_thrust_n},
        max_tilt_rad={max_tilt_rad},
        max_speed_m_s={max_speed_m_s},
    )

    if __name__ == "__main__":
        print(f"Configuration: {config_name}")
        print(f"  mass        = {{config.mass_kg}} kg")
        print(f"  wing area   = {{config.wing_area_m2}} m²")
        print(f"  cd0         = {{config.cd0}}")
        print(f"  max thrust  = {{config.max_thrust_n}} N")
        print(f"  max tilt    = {{config.max_tilt_rad}} rad")
        print(f"  max speed   = {{config.max_speed_m_s}} m/s")
""")

_SIMULATION_SCRIPT_TEMPLATE = textwrap.dedent("""\
    \"\"\"Auto-generated flight simulation script.\"\"\"

    from reidce.flight_sim import (
        GuidanceTarget,
        VehicleParams,
        VehicleState,
        simulate_flight,
    )

    params = VehicleParams(
        mass_kg={mass_kg},
        max_thrust_n={max_thrust_n},
        max_speed_m_s={max_speed_m_s},
    )

    initial = VehicleState(z_m={initial_altitude_m}, vx_m_s={initial_speed_m_s})
    target = GuidanceTarget(
        altitude_m={target_altitude_m},
        speed_m_s={target_speed_m_s},
        heading_rad=0.0,
    )

    result = simulate_flight(
        initial, target,
        duration_s={duration_s},
        dt_s={dt_s},
        params=params,
    )

    if __name__ == "__main__":
        print(f"Simulation complete: {{len(result.state)}} steps")
        max_alt = max(s.z_m for s in result.state)
        print(f"  max altitude = {{max_alt:.1f}} m")
        print(f"  min battery  = {{min(result.battery_pct):.1f}} %")
""")

_ANALYSIS_SCRIPT_TEMPLATE = textwrap.dedent("""\
    \"\"\"Auto-generated engineering analysis pipeline.\"\"\"

    import json
    from reidce.design_loop import run_design_loop, iteration_log_to_dict
    from reidce.flight_sim import VehicleParams

    params = VehicleParams(
        mass_kg={mass_kg},
        wing_area_m2={wing_area_m2},
        cd0={cd0},
        max_thrust_n={max_thrust_n},
        max_tilt_rad={max_tilt_rad},
        max_speed_m_s={max_speed_m_s},
    )

    log = run_design_loop(
        initial_params=params,
        max_iterations={max_iterations},
        convergence_score={convergence_score},
    )

    if __name__ == "__main__":
        summary = iteration_log_to_dict(log)
        print(json.dumps(summary, indent=2))
        print(f"Converged: {{log.converged}}")
        print(f"Best score: {{log.best_score}}")
""")

_BLUEPRINT_SCRIPT_TEMPLATE = textwrap.dedent("""\
    \"\"\"Auto-generated blueprint generation script.\"\"\"

    from reidce.blueprint_engine import (
        BlueprintSpec,
        generate_drone_blueprint,
    )

    spec = BlueprintSpec(
        title="{title}",
        sheet_width_mm={sheet_width_mm},
        sheet_height_mm={sheet_height_mm},
        arm_count={arm_count},
        arm_length_m={arm_length_m},
        hub_radius_m={hub_radius_m},
        prop_radius_m={prop_radius_m},
        scale={scale},
    )

    result = generate_drone_blueprint(spec)

    if __name__ == "__main__":
        print(f"Blueprint: {{result.title}}")
        print(f"  views: {{result.view_count}}")
        print(f"  dimensions: {{result.dimension_count}}")
        print(f"  SVG length: {{len(result.svg_content)}} chars")
        with open("blueprint.svg", "w") as f:
            f.write(result.svg_content)
        print("  Saved to blueprint.svg")
""")


# ── Code generation engine ───────────────────────────────────────────────


@dataclass
class CodeGenEngine:
    """Registry of code templates with parametric generation.

    All generated code is automatically validated via ``ast.parse``
    to ensure syntactic correctness before being returned.
    """

    templates: Dict[str, CodeTemplate] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register built-in engineering code templates."""
        builtins = [
            CodeTemplate(
                name="drone_config",
                category="configuration",
                description="Generate a VehicleParams drone configuration module",
                template=_DRONE_CONFIG_TEMPLATE,
                parameter_names=[
                    "config_name", "mass_kg", "wing_area_m2", "cd0",
                    "max_thrust_n", "max_tilt_rad", "max_speed_m_s",
                ],
                imports=["reidce.flight_sim"],
            ),
            CodeTemplate(
                name="simulation_script",
                category="simulation",
                description="Generate a flight simulation invocation script",
                template=_SIMULATION_SCRIPT_TEMPLATE,
                parameter_names=[
                    "mass_kg", "max_thrust_n", "max_speed_m_s",
                    "initial_altitude_m", "initial_speed_m_s",
                    "target_altitude_m", "target_speed_m_s",
                    "duration_s", "dt_s",
                ],
                imports=["reidce.flight_sim"],
            ),
            CodeTemplate(
                name="analysis_script",
                category="analysis",
                description="Generate an engineering analysis pipeline script",
                template=_ANALYSIS_SCRIPT_TEMPLATE,
                parameter_names=[
                    "mass_kg", "wing_area_m2", "cd0",
                    "max_thrust_n", "max_tilt_rad", "max_speed_m_s",
                    "max_iterations", "convergence_score",
                ],
                imports=["reidce.design_loop", "reidce.flight_sim"],
            ),
            CodeTemplate(
                name="blueprint_script",
                category="blueprint",
                description="Generate a blueprint generation script",
                template=_BLUEPRINT_SCRIPT_TEMPLATE,
                parameter_names=[
                    "title", "sheet_width_mm", "sheet_height_mm",
                    "arm_count", "arm_length_m", "hub_radius_m",
                    "prop_radius_m", "scale",
                ],
                imports=["reidce.blueprint_engine"],
            ),
        ]
        for tmpl in builtins:
            self.templates[tmpl.name] = tmpl

    def register_template(self, template: CodeTemplate) -> None:
        """Register a custom code template."""
        self.templates[template.name] = template

    def list_templates(self) -> List[Dict[str, str]]:
        """List all available templates."""
        return [
            {
                "name": t.name,
                "category": t.category,
                "description": t.description,
                "parameters": ", ".join(t.parameter_names),
            }
            for t in self.templates.values()
        ]

    def generate(
        self,
        template_name: str,
        params: Dict[str, Any],
    ) -> GeneratedCode:
        """Generate code from a named template with given parameters.

        The generated source is validated via ``ast.parse`` before
        being returned.
        """
        if template_name not in self.templates:
            raise KeyError(f"Unknown template: {template_name!r}")
        tmpl = self.templates[template_name]
        source = tmpl.render(params)
        is_valid, error = _validate_python(source)
        return GeneratedCode(
            source=source,
            template_name=template_name,
            is_valid=is_valid,
            validation_error=error,
            parameters=dict(params),
            line_count=source.count("\n") + 1,
            category=tmpl.category,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "dark/code_gen_engine/1.0",
            "template_count": len(self.templates),
            "templates": list(self.templates.keys()),
        }


# ── Convenience generators ───────────────────────────────────────────────


def generate_drone_config(
    config_name: str = "competition_quad",
    mass_kg: float = 2.5,
    wing_area_m2: float = 0.12,
    cd0: float = 0.04,
    max_thrust_n: float = 50.0,
    max_tilt_rad: float = 0.6,
    max_speed_m_s: float = 30.0,
) -> GeneratedCode:
    """Generate a drone configuration Python module."""
    engine = CodeGenEngine()
    return engine.generate("drone_config", {
        "config_name": config_name,
        "mass_kg": mass_kg,
        "wing_area_m2": wing_area_m2,
        "cd0": cd0,
        "max_thrust_n": max_thrust_n,
        "max_tilt_rad": max_tilt_rad,
        "max_speed_m_s": max_speed_m_s,
    })


def generate_simulation_script(
    mass_kg: float = 2.5,
    max_thrust_n: float = 50.0,
    max_speed_m_s: float = 30.0,
    initial_altitude_m: float = 0.0,
    initial_speed_m_s: float = 5.0,
    target_altitude_m: float = 50.0,
    target_speed_m_s: float = 12.0,
    duration_s: float = 20.0,
    dt_s: float = 0.05,
) -> GeneratedCode:
    """Generate a flight simulation script."""
    engine = CodeGenEngine()
    return engine.generate("simulation_script", {
        "mass_kg": mass_kg,
        "max_thrust_n": max_thrust_n,
        "max_speed_m_s": max_speed_m_s,
        "initial_altitude_m": initial_altitude_m,
        "initial_speed_m_s": initial_speed_m_s,
        "target_altitude_m": target_altitude_m,
        "target_speed_m_s": target_speed_m_s,
        "duration_s": duration_s,
        "dt_s": dt_s,
    })


def generate_analysis_script(
    mass_kg: float = 2.5,
    wing_area_m2: float = 0.12,
    cd0: float = 0.04,
    max_thrust_n: float = 50.0,
    max_tilt_rad: float = 0.6,
    max_speed_m_s: float = 30.0,
    max_iterations: int = 5,
    convergence_score: float = 85.0,
) -> GeneratedCode:
    """Generate an engineering analysis pipeline script."""
    engine = CodeGenEngine()
    return engine.generate("analysis_script", {
        "mass_kg": mass_kg,
        "wing_area_m2": wing_area_m2,
        "cd0": cd0,
        "max_thrust_n": max_thrust_n,
        "max_tilt_rad": max_tilt_rad,
        "max_speed_m_s": max_speed_m_s,
        "max_iterations": max_iterations,
        "convergence_score": convergence_score,
    })
