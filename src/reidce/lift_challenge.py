"""DARPA LIFT Challenge analysis: constraints, governing equations, and design evaluation.

Implements the core physics for heavy-lift multirotor design:

* **Momentum theory** — ideal induced hover power: ``P = T^(3/2) / sqrt(2 ρ A_eff)``
* **Effective disk area** — with coaxial interference correction
* **Installed shaft power** — figure-of-merit and profile-drag penalties
* **Mission closure** — energy budget across flight phases
* **Design evaluation** — mass-budget and performance ratio checks

The reference design is **ALADDIN-3B**: an open quad with SFCS integration,
4 × 2.45 m folding carbon-fibre rotors, and a single 180 cc 2-stroke
mechanical hybrid drive.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

from reidce.ratio import RatioResult, parse_ratio

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
G_M_S2: float = 9.80665
"""Standard gravitational acceleration (m/s²)."""

RHO_SEA_LEVEL: float = 1.225
"""ISA sea-level air density (kg/m³)."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RotorConfig:
    """Rotor geometry for a multirotor configuration."""

    rotor_radius_m: float
    rotor_count: int
    is_coaxial: bool = False


@dataclass(frozen=True)
class DiskAreaResult:
    """Effective actuator disk area computation result."""

    a_single_m2: float
    effective_disk_count: float
    a_eff_m2: float


@dataclass(frozen=True)
class HoverPowerResult:
    """Hover power breakdown from momentum theory."""

    thrust_n: float
    a_eff_m2: float
    disk_loading_pa: float
    p_ideal_w: float
    p_shaft_w: float
    fm_net: float


@dataclass(frozen=True)
class MissionPhase:
    """A single phase of the flight mission."""

    name: str
    duration_s: float
    power_w: float

    @property
    def energy_wh(self) -> float:
        """Energy consumed in this phase (Wh)."""
        return self.power_w * self.duration_s / 3600.0


@dataclass(frozen=True)
class MissionClosureResult:
    """Full mission energy closure analysis."""

    phases: List[MissionPhase]
    total_time_s: float
    total_energy_wh: float
    fuel_required_kg: float
    fuel_available_kg: float
    margin_fraction: float
    closes: bool


@dataclass(frozen=True)
class DesignConfig:
    """A candidate design configuration for the DARPA LIFT challenge."""

    design_id: str
    name: str
    rotor_config: RotorConfig
    dry_mass_kg: float
    fuel_mass_kg: float
    payload_mass_kg: float
    installed_power_w: float
    fm_net: float = 0.75
    k_profile: float = 0.25
    rho_kg_m3: float = RHO_SEA_LEVEL


@dataclass(frozen=True)
class DesignEvaluation:
    """Evaluation of a design against DARPA LIFT constraints."""

    design_id: str
    name: str
    aircraft_mass_kg: float
    payload_mass_kg: float
    gross_mass_kg: float
    payload_ratio: float
    hover_power: HoverPowerResult
    mass_under_limit: bool
    ratio_meets_minimum: bool
    errors: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core physics
# ---------------------------------------------------------------------------
def effective_disk_area(config: RotorConfig) -> DiskAreaResult:
    """Compute effective actuator disk area for a rotor configuration.

    For coaxial rotors sharing the same footprint, the lower rotor operates
    in the upper rotor's downwash.  The effective disk count is halved because
    only physically separated footprints contribute independent area.

    Returns a :class:`DiskAreaResult` with per-rotor area, effective count,
    and total effective area.
    """
    if config.rotor_radius_m <= 0:
        raise ValueError("rotor_radius_m must be > 0")
    if config.rotor_count < 1:
        raise ValueError("rotor_count must be >= 1")

    a_single = math.pi * config.rotor_radius_m ** 2

    if config.is_coaxial:
        effective_count = config.rotor_count / 2.0
    else:
        effective_count = float(config.rotor_count)

    a_eff = a_single * effective_count
    return DiskAreaResult(
        a_single_m2=a_single,
        effective_disk_count=effective_count,
        a_eff_m2=a_eff,
    )


def ideal_induced_power(thrust_n: float, rho: float, a_eff_m2: float) -> float:
    """Ideal induced hover power from momentum theory (W).

    ``P_i_ideal = T^(3/2) / sqrt(2 · ρ · A_eff)``
    """
    if thrust_n <= 0 or rho <= 0 or a_eff_m2 <= 0:
        raise ValueError("thrust_n, rho, and a_eff_m2 must all be > 0")
    return thrust_n ** 1.5 / math.sqrt(2.0 * rho * a_eff_m2)


def shaft_power(
    p_ideal_w: float,
    fm_net: float = 0.75,
    k_profile: float = 0.25,
) -> float:
    """Installed shaft power accounting for FM and profile drag.

    ``P_shaft = P_i_ideal × (1/FM + k_profile)``
    """
    if fm_net <= 0 or fm_net > 1.0:
        raise ValueError("fm_net must be in (0, 1]")
    if k_profile < 0:
        raise ValueError("k_profile must be >= 0")
    return p_ideal_w * (1.0 / fm_net + k_profile)


def hover_power(
    gross_mass_kg: float,
    config: RotorConfig,
    fm_net: float = 0.75,
    k_profile: float = 0.25,
    rho: float = RHO_SEA_LEVEL,
) -> HoverPowerResult:
    """Full hover power computation from gross mass and rotor geometry.

    Combines :func:`effective_disk_area`, :func:`ideal_induced_power`, and
    :func:`shaft_power` into a single result.
    """
    if gross_mass_kg <= 0:
        raise ValueError("gross_mass_kg must be > 0")
    thrust_n = gross_mass_kg * G_M_S2
    area = effective_disk_area(config)
    disk_loading = thrust_n / area.a_eff_m2
    p_ideal = ideal_induced_power(thrust_n, rho, area.a_eff_m2)
    p_shaft = shaft_power(p_ideal, fm_net, k_profile)
    return HoverPowerResult(
        thrust_n=thrust_n,
        a_eff_m2=area.a_eff_m2,
        disk_loading_pa=disk_loading,
        p_ideal_w=p_ideal,
        p_shaft_w=p_shaft,
        fm_net=fm_net,
    )


# ---------------------------------------------------------------------------
# Mission closure
# ---------------------------------------------------------------------------
def mission_closure(
    phases: List[MissionPhase],
    fuel_available_kg: float,
    sfc_kg_per_wh: float,
) -> MissionClosureResult:
    """Assess whether the mission energy budget closes.

    Parameters
    ----------
    phases:
        Ordered list of flight phases.
    fuel_available_kg:
        On-board fuel mass (kg).
    sfc_kg_per_wh:
        Specific fuel consumption (kg fuel per Wh of shaft energy).

    Returns
    -------
    MissionClosureResult
        Including total time, energy, fuel required, margin, and pass/fail.
    """
    if fuel_available_kg <= 0:
        raise ValueError("fuel_available_kg must be > 0")
    if sfc_kg_per_wh <= 0:
        raise ValueError("sfc_kg_per_wh must be > 0")

    total_time_s = sum(p.duration_s for p in phases)
    total_energy_wh = sum(p.energy_wh for p in phases)
    fuel_required = total_energy_wh * sfc_kg_per_wh
    margin = (fuel_available_kg - fuel_required) / fuel_required if fuel_required > 0 else 0.0
    return MissionClosureResult(
        phases=phases,
        total_time_s=total_time_s,
        total_energy_wh=total_energy_wh,
        fuel_required_kg=fuel_required,
        fuel_available_kg=fuel_available_kg,
        margin_fraction=margin,
        closes=fuel_required <= fuel_available_kg,
    )


# ---------------------------------------------------------------------------
# Design evaluation
# ---------------------------------------------------------------------------

# DARPA LIFT constraints
DARPA_MAX_AIRCRAFT_MASS_KG: float = 24.95  # 55 lb
DARPA_MIN_PAYLOAD_KG: float = 49.9  # 110 lb
DARPA_FULL_PRIZE_PARSED: RatioResult = parse_ratio("4:1")
"""Full-prize payload-to-aircraft-mass ratio, parsed from canonical ``4:1``."""
DARPA_FULL_PRIZE_RATIO: float = DARPA_FULL_PRIZE_PARSED.ratio_value  # 220 lb payload

DARPA_COURSE_NM: float = 5.0
DARPA_ALTITUDE_FT: float = 350.0
DARPA_MAX_TIME_MIN: float = 30.0


def evaluate_design(config: DesignConfig) -> DesignEvaluation:
    """Evaluate a design against DARPA LIFT challenge constraints.

    Checks:
    - Aircraft mass (dry + fuel) ≤ 55 lb (24.95 kg)
    - Payload > 110 lb (49.9 kg)
    - Computes payload-to-aircraft-mass ratio
    """
    errors: List[str] = []
    aircraft_mass = config.dry_mass_kg + config.fuel_mass_kg
    gross_mass = aircraft_mass + config.payload_mass_kg
    ratio = config.payload_mass_kg / aircraft_mass if aircraft_mass > 0 else 0.0

    mass_ok = aircraft_mass <= DARPA_MAX_AIRCRAFT_MASS_KG
    ratio_ok = config.payload_mass_kg > DARPA_MIN_PAYLOAD_KG

    if not mass_ok:
        errors.append(
            f"Aircraft mass {aircraft_mass:.2f} kg exceeds "
            f"{DARPA_MAX_AIRCRAFT_MASS_KG} kg limit"
        )
    if not ratio_ok:
        errors.append(
            f"Payload {config.payload_mass_kg:.2f} kg below "
            f"{DARPA_MIN_PAYLOAD_KG} kg minimum"
        )

    hp = hover_power(
        gross_mass_kg=gross_mass,
        config=config.rotor_config,
        fm_net=config.fm_net,
        k_profile=config.k_profile,
        rho=config.rho_kg_m3,
    )

    return DesignEvaluation(
        design_id=config.design_id,
        name=config.name,
        aircraft_mass_kg=aircraft_mass,
        payload_mass_kg=config.payload_mass_kg,
        gross_mass_kg=gross_mass,
        payload_ratio=ratio,
        hover_power=hp,
        mass_under_limit=mass_ok,
        ratio_meets_minimum=ratio_ok,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Reference design: ALADDIN-3B (D5)
# ---------------------------------------------------------------------------
ALADDIN_3B_ROTORS = RotorConfig(rotor_radius_m=1.225, rotor_count=4, is_coaxial=False)
"""ALADDIN-3B: 4 × 2.45 m open rotors."""

ALADDIN_3B = DesignConfig(
    design_id="D5",
    name="ALADDIN-3B (Open Quad + SFCS)",
    rotor_config=ALADDIN_3B_ROTORS,
    dry_mass_kg=20.00,
    fuel_mass_kg=1.63,  # 1.55 kg fuel + 0.08 kg premix oil
    payload_mass_kg=132.0,
    installed_power_w=18000.0,
    fm_net=0.75,
    k_profile=0.25,
)
"""Reference ALADDIN-3B configuration from the design trade study."""

ALADDIN_3B_MISSION = [
    MissionPhase(name="Takeoff + climb", duration_s=60.0, power_w=14000.0),
    MissionPhase(name="Cruise out (4 nm)", duration_s=492.0, power_w=11500.0),
    MissionPhase(name="Payload release", duration_s=30.0, power_w=10000.0),
    MissionPhase(name="Cruise back (1 nm)", duration_s=102.0, power_w=9000.0),
    MissionPhase(name="Land", duration_s=75.0, power_w=8000.0),
]
"""ALADDIN-3B nominal mission profile (5 nm at 350 ft AGL)."""
