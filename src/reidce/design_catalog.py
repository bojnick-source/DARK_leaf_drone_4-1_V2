"""Catalog of validated drone design configurations for DARK leaf 4-1.

Provides 17 pre-defined drone designs spanning five categories
(racing, endurance, heavy_lift, agile, balanced) with physically
realistic parameters and validation utilities.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ── Data classes ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DesignEntry:
    """A single validated drone design configuration."""

    design_id: str
    name: str
    category: str
    mass_kg: float
    wing_area_m2: float
    cd0: float
    max_thrust_n: float
    max_tilt_rad: float
    max_speed_m_s: float
    rotor_radius_m: float
    n_rotors: int = 4
    description: str = ""


@dataclass
class CatalogValidation:
    """Validation result for a single design entry."""

    design_id: str
    thrust_to_weight: float
    disk_loading_n_m2: float
    power_loading_kg_w: float
    wing_loading_n_m2: float
    is_valid: bool
    warnings: List[str] = field(default_factory=list)


# ── Catalog entries ───────────────────────────────────────────────────────

DESIGN_CATALOG: List[DesignEntry] = [
    # ── Racing (4) ────────────────────────────────────────────────────────
    DesignEntry(
        design_id="DESIGN_001",
        name="Viper Sprint",
        category="racing",
        mass_kg=1.8,
        wing_area_m2=0.22,
        cd0=0.022,
        max_thrust_n=55.0,
        max_tilt_rad=math.radians(42.0),
        max_speed_m_s=88.0,
        rotor_radius_m=0.10,
        description="Minimal-drag racer with aggressive tilt authority",
    ),
    DesignEntry(
        design_id="DESIGN_002",
        name="Bolt MkII",
        category="racing",
        mass_kg=1.6,
        wing_area_m2=0.20,
        cd0=0.020,
        max_thrust_n=50.0,
        max_tilt_rad=math.radians(44.0),
        max_speed_m_s=90.0,
        rotor_radius_m=0.09,
        description="Ultra-light speed-optimized racing frame",
    ),
    DesignEntry(
        design_id="DESIGN_003",
        name="Tempest R",
        category="racing",
        mass_kg=2.0,
        wing_area_m2=0.24,
        cd0=0.025,
        max_thrust_n=60.0,
        max_tilt_rad=math.radians(40.0),
        max_speed_m_s=85.0,
        rotor_radius_m=0.11,
        description="High-thrust racer for short-course sprints",
    ),
    DesignEntry(
        design_id="DESIGN_004",
        name="Razor Edge",
        category="racing",
        mass_kg=1.7,
        wing_area_m2=0.21,
        cd0=0.023,
        max_thrust_n=52.0,
        max_tilt_rad=math.radians(43.0),
        max_speed_m_s=87.0,
        rotor_radius_m=0.10,
        description="Low-profile racing design with swept planform",
    ),
    # ── Endurance (3) ─────────────────────────────────────────────────────
    DesignEntry(
        design_id="DESIGN_005",
        name="Albatross E",
        category="endurance",
        mass_kg=2.8,
        wing_area_m2=0.48,
        cd0=0.030,
        max_thrust_n=42.0,
        max_tilt_rad=math.radians(25.0),
        max_speed_m_s=52.0,
        rotor_radius_m=0.15,
        description="Large-wing endurance platform for long loiter",
    ),
    DesignEntry(
        design_id="DESIGN_006",
        name="Marathon",
        category="endurance",
        mass_kg=2.5,
        wing_area_m2=0.45,
        cd0=0.028,
        max_thrust_n=38.0,
        max_tilt_rad=math.radians(22.0),
        max_speed_m_s=48.0,
        rotor_radius_m=0.16,
        description="Efficiency-focused design with high aspect ratio wing",
    ),
    DesignEntry(
        design_id="DESIGN_007",
        name="Zephyr Long",
        category="endurance",
        mass_kg=2.6,
        wing_area_m2=0.46,
        cd0=0.032,
        max_thrust_n=40.0,
        max_tilt_rad=math.radians(24.0),
        max_speed_m_s=50.0,
        rotor_radius_m=0.15,
        description="Solar-ready endurance airframe with moderate thrust",
    ),
    # ── Heavy lift (3) ────────────────────────────────────────────────────
    DesignEntry(
        design_id="DESIGN_008",
        name="Atlas HL",
        category="heavy_lift",
        mass_kg=3.8,
        wing_area_m2=0.40,
        cd0=0.050,
        max_thrust_n=78.0,
        max_tilt_rad=math.radians(28.0),
        max_speed_m_s=45.0,
        rotor_radius_m=0.18,
        description="Heavy payload lifter with robust motor mounts",
    ),
    DesignEntry(
        design_id="DESIGN_009",
        name="Hercules",
        category="heavy_lift",
        mass_kg=4.0,
        wing_area_m2=0.42,
        cd0=0.055,
        max_thrust_n=80.0,
        max_tilt_rad=math.radians(26.0),
        max_speed_m_s=42.0,
        rotor_radius_m=0.18,
        description="Maximum-payload design for cargo delivery missions",
    ),
    DesignEntry(
        design_id="DESIGN_010",
        name="Titan Cargo",
        category="heavy_lift",
        mass_kg=3.6,
        wing_area_m2=0.38,
        cd0=0.048,
        max_thrust_n=72.0,
        max_tilt_rad=math.radians(30.0),
        max_speed_m_s=48.0,
        rotor_radius_m=0.17,
        description="Balanced heavy-lift with improved cruise efficiency",
    ),
    # ── Agile (4) ─────────────────────────────────────────────────────────
    DesignEntry(
        design_id="DESIGN_011",
        name="Hornet AG",
        category="agile",
        mass_kg=1.5,
        wing_area_m2=0.20,
        cd0=0.030,
        max_thrust_n=48.0,
        max_tilt_rad=math.radians(45.0),
        max_speed_m_s=75.0,
        rotor_radius_m=0.08,
        description="High T/W acrobatic platform with rapid response",
    ),
    DesignEntry(
        design_id="DESIGN_012",
        name="Mantis",
        category="agile",
        mass_kg=1.6,
        wing_area_m2=0.22,
        cd0=0.028,
        max_thrust_n=50.0,
        max_tilt_rad=math.radians(44.0),
        max_speed_m_s=78.0,
        rotor_radius_m=0.09,
        description="Compact agile frame for obstacle avoidance courses",
    ),
    DesignEntry(
        design_id="DESIGN_013",
        name="Pixie",
        category="agile",
        mass_kg=1.5,
        wing_area_m2=0.21,
        cd0=0.026,
        max_thrust_n=46.0,
        max_tilt_rad=math.radians(45.0),
        max_speed_m_s=72.0,
        rotor_radius_m=0.08,
        description="Ultra-light agile design for tight manoeuvres",
    ),
    DesignEntry(
        design_id="DESIGN_014",
        name="Switchblade",
        category="agile",
        mass_kg=1.7,
        wing_area_m2=0.23,
        cd0=0.032,
        max_thrust_n=54.0,
        max_tilt_rad=math.radians(42.0),
        max_speed_m_s=80.0,
        rotor_radius_m=0.10,
        description="Variable-geometry agile airframe for mixed tasks",
    ),
    # ── Balanced (3) ──────────────────────────────────────────────────────
    DesignEntry(
        design_id="DESIGN_015",
        name="Falcon X",
        category="balanced",
        mass_kg=2.4,
        wing_area_m2=0.32,
        cd0=0.035,
        max_thrust_n=55.0,
        max_tilt_rad=math.radians(35.0),
        max_speed_m_s=68.0,
        rotor_radius_m=0.13,
        description="Competition all-rounder optimized for 4-1 scoring",
    ),
    DesignEntry(
        design_id="DESIGN_016",
        name="Kestrel",
        category="balanced",
        mass_kg=2.2,
        wing_area_m2=0.30,
        cd0=0.033,
        max_thrust_n=52.0,
        max_tilt_rad=math.radians(34.0),
        max_speed_m_s=65.0,
        rotor_radius_m=0.12,
        description="Versatile mid-range platform with even performance",
    ),
    DesignEntry(
        design_id="DESIGN_017",
        name="Peregrine",
        category="balanced",
        mass_kg=2.6,
        wing_area_m2=0.34,
        cd0=0.036,
        max_thrust_n=58.0,
        max_tilt_rad=math.radians(36.0),
        max_speed_m_s=70.0,
        rotor_radius_m=0.14,
        description="Robust balanced design with margin for payloads",
    ),
]


# ── Lookup helpers ────────────────────────────────────────────────────────


def get_design(design_id: str) -> Optional[DesignEntry]:
    """Return a design entry by its unique ID, or ``None``."""
    for entry in DESIGN_CATALOG:
        if entry.design_id == design_id:
            return entry
    return None


def get_designs_by_category(category: str) -> List[DesignEntry]:
    """Return all designs matching the given category string."""
    return [e for e in DESIGN_CATALOG if e.category == category]


# ── Validation ────────────────────────────────────────────────────────────

_GRAVITY_DEFAULT = 9.80665
_RHO_SEA_LEVEL = 1.225  # kg/m³ ISA sea-level air density


def validate_design(
    entry: DesignEntry,
    gravity: float = _GRAVITY_DEFAULT,
) -> CatalogValidation:
    """Validate a single design and compute derived metrics."""
    weight_n = entry.mass_kg * gravity
    tw = entry.max_thrust_n / weight_n if weight_n > 0.0 else 0.0

    disk_area = (
        entry.n_rotors * math.pi * entry.rotor_radius_m ** 2
    )
    disk_loading = (
        entry.max_thrust_n / disk_area if disk_area > 0.0 else 0.0
    )

    # Approximate hover power for power-loading estimate
    induced_power = entry.max_thrust_n * math.sqrt(
        entry.max_thrust_n / (2.0 * _RHO_SEA_LEVEL * disk_area)
    ) if disk_area > 0.0 else 0.0
    power_loading = (
        entry.mass_kg / induced_power if induced_power > 0.0 else 0.0
    )

    wing_loading = weight_n / entry.wing_area_m2 if entry.wing_area_m2 > 0.0 else 0.0

    warnings: List[str] = []
    is_valid = True

    if tw <= 1.0:
        is_valid = False
        warnings.append(
            f"T/W ratio {tw:.2f} <= 1.0; vehicle cannot hover"
        )
    if disk_loading > 500.0:
        warnings.append(
            f"Disk loading {disk_loading:.1f} N/m2 exceeds 500 N/m2"
        )
    if wing_loading > 300.0:
        warnings.append(
            f"Wing loading {wing_loading:.1f} N/m2 exceeds 300 N/m2"
        )
    if entry.max_speed_m_s > 100.0:
        warnings.append(
            f"Max speed {entry.max_speed_m_s:.1f} m/s exceeds 100 m/s"
        )

    return CatalogValidation(
        design_id=entry.design_id,
        thrust_to_weight=tw,
        disk_loading_n_m2=disk_loading,
        power_loading_kg_w=power_loading,
        wing_loading_n_m2=wing_loading,
        is_valid=is_valid,
        warnings=warnings,
    )


def validate_catalog() -> List[CatalogValidation]:
    """Validate every entry in ``DESIGN_CATALOG``."""
    return [validate_design(e) for e in DESIGN_CATALOG]


# ── Summary ───────────────────────────────────────────────────────────────


def catalog_summary() -> Dict[str, Any]:
    """Return a summary dict describing the catalog and its validity."""
    validations = validate_catalog()
    by_category: Dict[str, int] = {}
    for entry in DESIGN_CATALOG:
        by_category[entry.category] = (
            by_category.get(entry.category, 0) + 1
        )
    valid_count = sum(1 for v in validations if v.is_valid)
    return {
        "total": len(DESIGN_CATALOG),
        "by_category": by_category,
        "valid_count": valid_count,
        "invalid_count": len(DESIGN_CATALOG) - valid_count,
        "categories": sorted(by_category.keys()),
    }
