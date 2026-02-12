"""Electromagnetic library for axial flux motor synthesis.

Provides linear and non-linear B-H curve modelling, winding calculations,
axial flux motor geometry, torque/power estimation, and efficiency mapping.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

MU_0: float = 4.0 * math.pi * 1e-7  # vacuum permeability (H/m)


# ---------------------------------------------------------------------------
# B-H curve models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LinearBHCurve:
    """Linear (constant permeability) B-H model."""

    mu_r: float  # relative permeability

    def permeability(self) -> float:
        return MU_0 * self.mu_r

    def b_from_h(self, h_a_per_m: float) -> float:
        return self.permeability() * h_a_per_m

    def h_from_b(self, b_t: float) -> float:
        mu = self.permeability()
        if mu <= 0.0:
            raise ValueError("Permeability must be > 0")
        return b_t / mu


@dataclass(frozen=True)
class NonLinearBHCurve:
    """Non-linear (saturating) B-H model using the Jiles–Atherton-like
    arctangent approximation:  B = B_sat * (2/π) * arctan(π * μ_r * μ_0 * H / (2 * B_sat))
    """

    mu_r_initial: float  # initial relative permeability
    b_saturation_t: float  # saturation flux density (T)

    def b_from_h(self, h_a_per_m: float) -> float:
        if self.b_saturation_t <= 0.0:
            raise ValueError("B_sat must be > 0")
        scale = math.pi * self.mu_r_initial * MU_0 * h_a_per_m / (2.0 * self.b_saturation_t)
        return self.b_saturation_t * (2.0 / math.pi) * math.atan(scale)

    def incremental_mu_r(self, h_a_per_m: float) -> float:
        """Incremental (differential) relative permeability at given H."""
        scale = math.pi * self.mu_r_initial * MU_0 / (2.0 * self.b_saturation_t)
        return self.mu_r_initial / (1.0 + (scale * h_a_per_m) ** 2)


# ---------------------------------------------------------------------------
# Winding specification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Winding:
    """Concentrated or distributed winding specification."""

    turns_per_coil: int
    num_coils: int
    wire_diameter_m: float
    resistivity_ohm_m: float = 1.68e-8  # copper
    mean_turn_length_m: float = 0.1

    def total_turns(self) -> int:
        return self.turns_per_coil * self.num_coils

    def wire_area_m2(self) -> float:
        return math.pi * (self.wire_diameter_m / 2.0) ** 2

    def resistance(self) -> float:
        length = self.total_turns() * self.mean_turn_length_m
        area = self.wire_area_m2()
        if area <= 0.0:
            raise ValueError("Wire area must be > 0")
        return self.resistivity_ohm_m * length / area

    def copper_loss_w(self, current_a: float) -> float:
        return current_a ** 2 * self.resistance()


# ---------------------------------------------------------------------------
# Axial flux motor geometry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AxialFluxGeometry:
    """Axial flux motor geometry (single-stator, dual-rotor or variants)."""

    outer_radius_m: float
    inner_radius_m: float
    airgap_m: float
    rotor_thickness_m: float
    stator_thickness_m: float
    num_poles: int
    num_stator_slots: int = 0  # 0 means slotless

    def active_area_m2(self) -> float:
        if self.outer_radius_m <= self.inner_radius_m:
            raise ValueError("Outer radius must exceed inner radius")
        return math.pi * (self.outer_radius_m ** 2 - self.inner_radius_m ** 2)

    def mean_radius_m(self) -> float:
        return (self.outer_radius_m + self.inner_radius_m) / 2.0

    def pole_pitch_m(self) -> float:
        if self.num_poles <= 0:
            raise ValueError("Number of poles must be > 0")
        return 2.0 * math.pi * self.mean_radius_m() / self.num_poles

    def axial_length_m(self) -> float:
        return 2.0 * self.rotor_thickness_m + self.stator_thickness_m + 2.0 * self.airgap_m


# ---------------------------------------------------------------------------
# Magnet specification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PermanentMagnet:
    """Permanent magnet properties (NdFeB, ferrite, etc.)."""

    remanence_t: float  # Br
    coercivity_a_per_m: float  # Hc
    relative_permeability: float = 1.05  # recoil μ_r

    def magnet_length_for_airgap(self, airgap_m: float, target_b_t: float) -> float:
        """Estimate magnet length to achieve target airgap flux density."""
        if target_b_t <= 0.0 or self.remanence_t <= 0.0:
            raise ValueError("Target B and Br must be > 0")
        # Simplified magnetic circuit: B_g = Br * l_m / (l_m + mu_r * g)
        # Solving for l_m: l_m = mu_r * g * B_g / (Br - B_g)
        if target_b_t >= self.remanence_t:
            raise ValueError("Target B must be less than Br")
        return (
            self.relative_permeability
            * airgap_m
            * target_b_t
            / (self.remanence_t - target_b_t)
        )


# ---------------------------------------------------------------------------
# Axial flux motor model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AxialFluxMotor:
    """Axial flux motor combining geometry, magnets, windings, and B-H curve."""

    name: str
    geometry: AxialFluxGeometry
    winding: Winding
    magnet: PermanentMagnet
    bh_curve: LinearBHCurve | NonLinearBHCurve
    phases: int = 3

    def airgap_flux_density_t(self) -> float:
        """Estimate airgap flux density using simplified magnetic circuit."""
        br = self.magnet.remanence_t
        mu_r = self.magnet.relative_permeability
        g = self.geometry.airgap_m
        lm = self.geometry.rotor_thickness_m
        if (lm + mu_r * g) <= 0.0:
            raise ValueError("Invalid geometry for flux calculation")
        return br * lm / (lm + mu_r * g)

    def flux_per_pole_wb(self) -> float:
        """Flux per pole: Φ = B_g × active_area / num_poles."""
        bg = self.airgap_flux_density_t()
        return bg * self.geometry.active_area_m2() / self.geometry.num_poles

    def back_emf_constant_v_s_per_rad(self) -> float:
        """Back-EMF constant: Ke = N_turns × Φ × p / (2π) for fundamental."""
        phi = self.flux_per_pole_wb()
        n = self.winding.total_turns()
        p = self.geometry.num_poles
        return n * phi * p / (2.0 * math.pi)

    def torque_constant_nm_per_a(self) -> float:
        """For a balanced multi-phase motor, Kt ≈ Ke (in SI units)."""
        return self.back_emf_constant_v_s_per_rad()

    def electromagnetic_torque_nm(self, current_a: float) -> float:
        return self.torque_constant_nm_per_a() * current_a

    def mechanical_power_w(self, current_a: float, speed_rpm: float) -> float:
        omega = speed_rpm * 2.0 * math.pi / 60.0
        return self.electromagnetic_torque_nm(current_a) * omega

    def copper_loss_w(self, current_a: float) -> float:
        return self.winding.copper_loss_w(current_a) * self.phases

    def core_loss_estimate_w(self, speed_rpm: float, k_core: float = 0.01) -> float:
        """Simplified Steinmetz-like core loss: P_core = k * B^2 * f^1.5."""
        bg = self.airgap_flux_density_t()
        freq_hz = (self.geometry.num_poles / 2.0) * speed_rpm / 60.0
        return k_core * bg ** 2 * freq_hz ** 1.5

    def efficiency(
        self,
        current_a: float,
        speed_rpm: float,
        k_core: float = 0.01,
    ) -> float:
        """Motor efficiency at given operating point."""
        p_mech = self.mechanical_power_w(current_a, speed_rpm)
        p_cu = self.copper_loss_w(current_a)
        p_core = self.core_loss_estimate_w(speed_rpm, k_core)
        p_total = p_mech + p_cu + p_core
        if p_total <= 0.0:
            return 0.0
        return p_mech / p_total


# ---------------------------------------------------------------------------
# Motor synthesis helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MotorDesignPoint:
    """A single operating-point evaluation."""

    speed_rpm: float
    current_a: float
    torque_nm: float
    power_w: float
    copper_loss_w: float
    core_loss_w: float
    efficiency: float


def evaluate_motor(
    motor: AxialFluxMotor,
    speed_rpm: float,
    current_a: float,
    k_core: float = 0.01,
) -> MotorDesignPoint:
    """Evaluate motor at a single operating point."""
    return MotorDesignPoint(
        speed_rpm=speed_rpm,
        current_a=current_a,
        torque_nm=motor.electromagnetic_torque_nm(current_a),
        power_w=motor.mechanical_power_w(current_a, speed_rpm),
        copper_loss_w=motor.copper_loss_w(current_a),
        core_loss_w=motor.core_loss_estimate_w(speed_rpm, k_core),
        efficiency=motor.efficiency(current_a, speed_rpm, k_core),
    )


def efficiency_map(
    motor: AxialFluxMotor,
    speed_range_rpm: Tuple[float, float],
    current_range_a: Tuple[float, float],
    n_speed: int = 10,
    n_current: int = 10,
    k_core: float = 0.01,
) -> List[MotorDesignPoint]:
    """Generate an efficiency map over a speed/current grid."""
    if n_speed < 2 or n_current < 2:
        raise ValueError("Grid dimensions must be >= 2")
    speed_step = (speed_range_rpm[1] - speed_range_rpm[0]) / (n_speed - 1)
    current_step = (current_range_a[1] - current_range_a[0]) / (n_current - 1)
    points: List[MotorDesignPoint] = []
    for si in range(n_speed):
        speed = speed_range_rpm[0] + si * speed_step
        for ci in range(n_current):
            current = current_range_a[0] + ci * current_step
            points.append(evaluate_motor(motor, speed, current, k_core))
    return points


# ---------------------------------------------------------------------------
# Non-linear saturation analysis
# ---------------------------------------------------------------------------


def saturation_curve(
    bh_curve: NonLinearBHCurve,
    h_max_a_per_m: float,
    n_points: int = 50,
) -> List[Tuple[float, float]]:
    """Generate (H, B) pairs along the non-linear B-H curve."""
    if n_points < 2:
        raise ValueError("n_points must be >= 2")
    step = h_max_a_per_m / (n_points - 1)
    return [(i * step, bh_curve.b_from_h(i * step)) for i in range(n_points)]
