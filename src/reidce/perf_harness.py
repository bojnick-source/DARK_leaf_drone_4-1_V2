"""Unified performance harness — ties all seven engines together.

Orchestrates the full design-to-CAD pipeline:

1. Energy manipulation (energy_maneuverability) — Ps surfaces, E-M envelopes
2. DARPA cipher (darpa_cipher) — artifact signing, chain-of-custody
3. Physics engine (aerospace) — ISA atmosphere, drag polars, flight conditions
4. Math engine (sampling, topology, bemt) — DOE, rotor BEMT, topology opt
5. Engineering AI (engineering_ai) — retrieval-augmented knowledge queries
6. CAD output (cad_rendering) — cached mesh generation, quality scoring
7. This orchestrator — pipeline coordination, timing, accuracy metrics

The harness provides:
* ``PerformanceHarness`` — single entry point for the full pipeline
* ``PipelineBenchmark`` — timing and accuracy metrics for every stage
* ``run_full_pipeline`` — one-call design evaluation from parameters to CAD
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from reidce.aerospace import (
    AeroCoefficients,
    FlightCondition,
    ISAAtmosphere,
    analyze_flight_condition,
    compute_drag_polar,
    isa_atmosphere,
    isa_density_at,
)
from reidce.bemt import (
    BEMTCondition,
    BEMTResult,
    RotorGeometry,
    rpm_sweep,
    solve_bemt_fast,
)
from reidce.cad_rendering import (
    CadMesh,
    batch_generate_meshes,
    clear_mesh_cache,
    generate_mesh_cached,
    mesh_quality_score_fast,
    mesh_to_stl_text,
)
from reidce.energy_maneuverability import (
    EMState,
    StructuralLimits,
    compute_em_envelope_fast,
    compute_em_state,
    compute_ps_surface,
)
from reidce.engineering_ai import (
    ConversationContext,
    EngineeringQueryEngine,
    PipelineResult,
    clear_query_cache,
    run_ai_pipeline,
)
from reidce.flight_sim import Atmosphere, VehicleParams, VehicleState
from reidce.lift_challenge import (
    ALADDIN_3B,
    DesignConfig,
    DesignEvaluation,
    HoverPowerResult,
    evaluate_design,
    hover_power,
)
from reidce.sampling import (
    SamplingBounds,
    adaptive_sample,
    compute_discrepancy_fast,
    latin_hypercube_sample,
    multi_objective_adaptive_sample,
    sobol_like_sample,
)
from reidce.schemas import DesignSpec, GeometrySpec


# ---------------------------------------------------------------------------
# Timing instrumentation
# ---------------------------------------------------------------------------

@dataclass
class StageTimer:
    """Measures wall-clock time for a pipeline stage."""

    name: str
    start_ns: int = 0
    end_ns: int = 0

    def start(self) -> None:
        self.start_ns = time.perf_counter_ns()

    def stop(self) -> None:
        self.end_ns = time.perf_counter_ns()

    @property
    def elapsed_ms(self) -> float:
        return (self.end_ns - self.start_ns) / 1_000_000.0


# ---------------------------------------------------------------------------
# Pipeline benchmark result
# ---------------------------------------------------------------------------

@dataclass
class PipelineBenchmark:
    """Timing and accuracy metrics for a full pipeline run."""

    stage_times: Dict[str, float] = field(default_factory=dict)
    total_ms: float = 0.0
    accuracy_metrics: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "dark/perf_harness/benchmark/1.0",
            "stage_times_ms": dict(self.stage_times),
            "total_ms": round(self.total_ms, 2),
            "accuracy_metrics": dict(self.accuracy_metrics),
            "warnings": list(self.warnings),
        }


# ---------------------------------------------------------------------------
# Pipeline result
# ---------------------------------------------------------------------------

@dataclass
class FullPipelineResult:
    """Complete result from the unified performance pipeline."""

    # Energy manipulation
    em_state: Optional[EMState] = None
    ps_surface: Optional[List[Tuple[float, float, float]]] = None

    # Physics engine
    isa: Optional[ISAAtmosphere] = None
    flight_analysis: Optional[Dict[str, float]] = None
    drag_polar: Optional[List[Tuple[float, float]]] = None

    # Math engine — BEMT
    bemt_result: Optional[BEMTResult] = None
    rpm_sweep_data: Optional[List[Dict[str, float]]] = None

    # Design evaluation
    design_eval: Optional[DesignEvaluation] = None
    hover: Optional[HoverPowerResult] = None

    # CAD output
    mesh: Optional[CadMesh] = None
    mesh_quality: float = 0.0
    stl_text: Optional[str] = None

    # AI pipeline
    ai_result: Optional[PipelineResult] = None

    # Benchmark
    benchmark: PipelineBenchmark = field(default_factory=PipelineBenchmark)

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable summary of the full pipeline run."""
        result: Dict[str, Any] = {
            "schema": "dark/perf_harness/pipeline/1.0",
        }
        if self.em_state is not None:
            result["em_state"] = {
                "ps_m_s": self.em_state.ps_m_s,
                "load_factor_g": self.em_state.load_factor_g,
                "specific_energy_j_per_kg": self.em_state.specific_energy_j_per_kg,
                "sustained_turn_rate_deg_s": self.em_state.sustained_turn_rate_deg_s,
            }
        if self.flight_analysis is not None:
            result["flight_analysis"] = self.flight_analysis
        if self.bemt_result is not None:
            result["bemt"] = {
                "thrust_n": self.bemt_result.thrust_n,
                "power_w": self.bemt_result.power_w,
                "fm": self.bemt_result.fm,
            }
        if self.design_eval is not None:
            result["design_eval"] = {
                "name": self.design_eval.name,
                "payload_ratio": self.design_eval.payload_ratio,
                "mass_under_limit": self.design_eval.mass_under_limit,
                "ratio_meets_minimum": self.design_eval.ratio_meets_minimum,
                "errors": self.design_eval.errors,
            }
        if self.mesh is not None:
            result["mesh"] = {
                "vertex_count": self.mesh.statistics.vertex_count,
                "triangle_count": self.mesh.statistics.triangle_count,
                "surface_area": self.mesh.statistics.surface_area,
                "quality_score": self.mesh_quality,
                "watertight": self.mesh.statistics.watertight,
                "geometry_hash": self.mesh.geometry_hash,
            }
        result["benchmark"] = self.benchmark.to_dict()
        return result


# ---------------------------------------------------------------------------
# Performance harness
# ---------------------------------------------------------------------------

@dataclass
class PerformanceHarness:
    """Unified performance harness tying all seven engines together.

    Provides the single entry point for the full design-to-CAD pipeline
    with integrated timing, accuracy tracking, and caching across all
    sub-engines.
    """

    atmosphere: Atmosphere = field(default_factory=Atmosphere)
    limits: StructuralLimits = field(default_factory=StructuralLimits)
    vehicle_params: VehicleParams = field(default_factory=VehicleParams)
    rotor_geometry: RotorGeometry = field(default_factory=RotorGeometry)
    bemt_condition: BEMTCondition = field(default_factory=BEMTCondition)

    def run_energy_analysis(
        self,
        speed_m_s: float = 10.0,
        altitude_m: float = 30.0,
        throttle: float = 0.8,
    ) -> Tuple[EMState, PipelineBenchmark]:
        """Stage 1: Energy manipulation analysis."""
        bench = PipelineBenchmark()
        timer = StageTimer("energy_manipulation")
        timer.start()

        state = VehicleState(z_m=altitude_m, vx_m_s=speed_m_s)
        em = compute_em_state(
            state, throttle, bank_angle_rad=0.0,
            params=self.vehicle_params,
            atmosphere=self.atmosphere,
            limits=self.limits,
        )

        timer.stop()
        bench.stage_times["energy_manipulation"] = timer.elapsed_ms
        bench.total_ms = timer.elapsed_ms

        # Accuracy: check Ps is physically consistent
        if em.ps_m_s > 100.0:
            bench.warnings.append("Ps > 100 m/s — check thrust/drag balance")
        bench.accuracy_metrics["ps_m_s"] = em.ps_m_s
        bench.accuracy_metrics["specific_energy_j_per_kg"] = em.specific_energy_j_per_kg

        return em, bench

    def run_physics_analysis(
        self,
        altitude_m: float = 30.0,
        speed_m_s: float = 15.0,
    ) -> Tuple[Dict[str, float], PipelineBenchmark]:
        """Stage 3: Physics engine analysis."""
        bench = PipelineBenchmark()
        timer = StageTimer("physics_engine")
        timer.start()

        coeffs = AeroCoefficients(
            cl=self.vehicle_params.cl_alpha_per_rad * 0.1,
            cd=self.vehicle_params.cd0,
            cm=0.0,
        )
        condition = FlightCondition(
            altitude_m=altitude_m,
            speed_m_s=speed_m_s,
            wing_area_m2=self.vehicle_params.wing_area_m2,
            coeffs=coeffs,
            mass_kg=self.vehicle_params.mass_kg,
        )
        analysis = analyze_flight_condition(condition)

        timer.stop()
        bench.stage_times["physics_engine"] = timer.elapsed_ms
        bench.total_ms = timer.elapsed_ms

        # Accuracy: lift should approximately balance weight in level flight
        weight = analysis["weight_n"]
        lift = analysis["lift_n"]
        lift_error_pct = abs(lift - weight) / max(weight, 1e-6) * 100.0
        bench.accuracy_metrics["lift_weight_error_pct"] = round(lift_error_pct, 2)
        bench.accuracy_metrics["l_over_d"] = analysis["l_over_d"]

        return analysis, bench

    def run_bemt_analysis(self) -> Tuple[BEMTResult, PipelineBenchmark]:
        """Stage 4: Math engine — BEMT rotor analysis."""
        bench = PipelineBenchmark()
        timer = StageTimer("bemt_analysis")
        timer.start()

        result = solve_bemt_fast(self.rotor_geometry, self.bemt_condition)

        timer.stop()
        bench.stage_times["bemt_analysis"] = timer.elapsed_ms
        bench.total_ms = timer.elapsed_ms

        bench.accuracy_metrics["fm"] = result.fm
        bench.accuracy_metrics["thrust_n"] = result.thrust_n
        if result.fm < 0.3:
            bench.warnings.append(f"Figure of merit {result.fm:.3f} is very low")
        if result.fm > 1.0:
            bench.warnings.append(f"Figure of merit {result.fm:.3f} > 1.0 — check inputs")

        return result, bench

    def run_cad_output(
        self,
        geometry: GeometrySpec,
        quality: str = "standard",
        export_stl: bool = False,
    ) -> Tuple[CadMesh, float, Optional[str], PipelineBenchmark]:
        """Stage 6: CAD output with cached mesh generation."""
        bench = PipelineBenchmark()
        timer = StageTimer("cad_output")
        timer.start()

        mesh = generate_mesh_cached(geometry, quality)  # type: ignore[arg-type]
        quality_score = mesh_quality_score_fast(mesh)
        stl = mesh_to_stl_text(mesh) if export_stl else None

        timer.stop()
        bench.stage_times["cad_output"] = timer.elapsed_ms
        bench.total_ms = timer.elapsed_ms

        bench.accuracy_metrics["mesh_quality"] = quality_score
        bench.accuracy_metrics["vertex_count"] = mesh.statistics.vertex_count
        bench.accuracy_metrics["triangle_count"] = mesh.statistics.triangle_count
        if quality_score < 0.3:
            bench.warnings.append(f"Mesh quality {quality_score:.3f} below threshold")

        return mesh, quality_score, stl, bench


def run_full_pipeline(
    design_config: Optional[DesignConfig] = None,
    geometry: Optional[GeometrySpec] = None,
    vehicle_params: Optional[VehicleParams] = None,
    rotor_geometry: Optional[RotorGeometry] = None,
    bemt_condition: Optional[BEMTCondition] = None,
    ai_engine: Optional[EngineeringQueryEngine] = None,
    ai_question: Optional[str] = None,
    altitude_m: float = 30.0,
    speed_m_s: float = 10.0,
    throttle: float = 0.8,
    export_stl: bool = False,
) -> FullPipelineResult:
    """Run the complete seven-stage performance pipeline.

    Stages:
        1. Energy manipulation — Ps and E-M state
        2. DARPA cipher — (signing deferred to caller with artifacts)
        3. Physics engine — ISA, lift/drag, flight condition
        4. Math engine — BEMT rotor performance
        5. Engineering AI — knowledge query (if engine + question provided)
        6. CAD output — mesh generation and quality scoring
        7. Orchestration — timing aggregation and accuracy metrics

    Returns a ``FullPipelineResult`` with all sub-results and benchmark.
    """
    pipeline = FullPipelineResult()
    overall_start = time.perf_counter_ns()
    all_warnings: List[str] = []
    stage_times: Dict[str, float] = {}
    accuracy: Dict[str, float] = {}

    harness = PerformanceHarness(
        vehicle_params=vehicle_params or VehicleParams(),
        rotor_geometry=rotor_geometry or RotorGeometry(),
        bemt_condition=bemt_condition or BEMTCondition(),
    )

    # Stage 1: Energy manipulation
    em, em_bench = harness.run_energy_analysis(speed_m_s, altitude_m, throttle)
    pipeline.em_state = em
    stage_times.update(em_bench.stage_times)
    accuracy.update(em_bench.accuracy_metrics)
    all_warnings.extend(em_bench.warnings)

    # Stage 2: DARPA cipher (artifact signing happens at caller level;
    # we record stage as zero-cost here since no artifacts provided)
    stage_times["darpa_cipher"] = 0.0

    # Stage 3: Physics engine
    physics, phys_bench = harness.run_physics_analysis(altitude_m, speed_m_s)
    pipeline.flight_analysis = physics
    pipeline.isa = isa_atmosphere(altitude_m)
    stage_times.update(phys_bench.stage_times)
    accuracy.update(phys_bench.accuracy_metrics)
    all_warnings.extend(phys_bench.warnings)

    # Stage 4: Math engine — BEMT
    bemt_res, bemt_bench = harness.run_bemt_analysis()
    pipeline.bemt_result = bemt_res
    stage_times.update(bemt_bench.stage_times)
    accuracy.update(bemt_bench.accuracy_metrics)
    all_warnings.extend(bemt_bench.warnings)

    # Stage 5: Engineering AI
    if ai_engine is not None and ai_question:
        ai_timer = StageTimer("engineering_ai")
        ai_timer.start()
        context = ConversationContext()
        pipeline.ai_result = run_ai_pipeline(ai_engine, context, ai_question)
        ai_timer.stop()
        stage_times["engineering_ai"] = ai_timer.elapsed_ms
        accuracy["ai_confidence"] = pipeline.ai_result.confidence

    # Stage 6: CAD output
    if geometry is not None:
        mesh, qual, stl, cad_bench = harness.run_cad_output(
            geometry, quality="standard", export_stl=export_stl,
        )
        pipeline.mesh = mesh
        pipeline.mesh_quality = qual
        pipeline.stl_text = stl
        stage_times.update(cad_bench.stage_times)
        accuracy.update(cad_bench.accuracy_metrics)
        all_warnings.extend(cad_bench.warnings)

    # Design evaluation (if config provided)
    if design_config is not None:
        eval_timer = StageTimer("design_evaluation")
        eval_timer.start()
        pipeline.design_eval = evaluate_design(design_config)
        pipeline.hover = pipeline.design_eval.hover_power
        eval_timer.stop()
        stage_times["design_evaluation"] = eval_timer.elapsed_ms
        accuracy["payload_ratio"] = pipeline.design_eval.payload_ratio

    # Stage 7: Orchestration — aggregate benchmark
    overall_end = time.perf_counter_ns()
    pipeline.benchmark = PipelineBenchmark(
        stage_times=stage_times,
        total_ms=(overall_end - overall_start) / 1_000_000.0,
        accuracy_metrics=accuracy,
        warnings=all_warnings,
    )

    return pipeline


def clear_all_caches() -> None:
    """Clear all performance caches across every engine."""
    clear_mesh_cache()
    clear_query_cache()
