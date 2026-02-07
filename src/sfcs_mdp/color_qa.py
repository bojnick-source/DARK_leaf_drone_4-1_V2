from __future__ import annotations

from enum import Enum
from math import atan2, cos, exp, pi, radians, sin, sqrt
from typing import Iterable, List

from pydantic import BaseModel, ConfigDict, Field


class OutputTransformMode(str, Enum):
    SRGB_FALLBACK = "sRGB fallback"
    REFERENCE_CLAMP = "reference clamp"
    WIDE_GAMUT_NORMAL = "wide-gamut normal"


class QaStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class PatchGroup(str, Enum):
    GRAYSCALE = "grayscale"
    NEUTRALS = "neutrals"
    SATURATED = "saturated"


class PatchRole(str, Enum):
    GRAYSCALE = "grayscale"
    NEUTRAL = "neutral"
    WARM_NEUTRAL = "warm_neutral"
    PRIMARY_RED = "primary_red"
    PRIMARY_GREEN = "primary_green"
    PRIMARY_BLUE = "primary_blue"
    SECONDARY_CYAN = "secondary_cyan"
    SECONDARY_MAGENTA = "secondary_magenta"
    SECONDARY_YELLOW = "secondary_yellow"
    DEEP_BLACK = "deep_black"
    NEAR_WHITE = "near_white"


class LabColor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    L: float = Field(..., ge=0.0, le=100.0)
    a: float
    b: float


class ColorPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    role: PatchRole
    reference_lab: LabColor
    sample_lab: LabColor


class ColorProfileInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monitor_name: str | None = None
    profile_name: str | None = None
    profile_hash: str | None = None
    trc_gamma_hint: str | None = None
    white_point_hint: str | None = None
    gamut_hint: str | None = None


class ColorProfileScene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    icc_profile: ColorProfileInfo | None = None
    reference_mode: bool = False
    output_transform_mode: OutputTransformMode | None = None
    patches: List[ColorPatch]


class PatchDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    role: PatchRole
    group: PatchGroup
    delta_e00: float
    chroma_delta: float


class GroupSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_delta_e00: float
    mean_delta_e00: float
    threshold_max: float
    threshold_mean: float
    status: QaStatus


class OversaturationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: QaStatus
    failures: List[str]


class ColorQaReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    icc_profile_hash: str
    output_transform_mode: OutputTransformMode
    patches: List[PatchDelta]
    summary: dict[str, GroupSummary]
    oversaturation: OversaturationSummary
    passed: bool


_GROUP_THRESHOLDS = {
    PatchGroup.GRAYSCALE: {"max": 1.0, "mean": 0.4},
    PatchGroup.NEUTRALS: {"max": 2.0, "mean": 0.8},
    PatchGroup.SATURATED: {"max": 3.0, "mean": 1.2},
}


def _normalize_hue(angle: float) -> float:
    if angle < 0:
        angle += 360
    return angle


def _delta_hue(h1: float, h2: float) -> float:
    delta = h2 - h1
    if abs(delta) <= 180:
        return delta
    if delta > 180:
        return delta - 360
    return delta + 360


def _mean_hue(h1: float, h2: float, c1: float, c2: float) -> float:
    if c1 * c2 == 0:
        return (h1 + h2) / 2.0
    diff = abs(h1 - h2)
    if diff <= 180:
        return (h1 + h2) / 2
    if h1 + h2 < 360:
        return (h1 + h2 + 360) / 2
    return (h1 + h2 - 360) / 2


def _lab_chroma(color: LabColor) -> float:
    return sqrt(color.a * color.a + color.b * color.b)


def delta_e_ciede2000(reference: LabColor, sample: LabColor) -> float:
    l1, a1, b1 = reference.L, reference.a, reference.b
    l2, a2, b2 = sample.L, sample.a, sample.b

    c1 = sqrt(a1 * a1 + b1 * b1)
    c2 = sqrt(a2 * a2 + b2 * b2)
    mean_c = (c1 + c2) / 2
    mean_c7 = mean_c**7
    g = 0.5 * (1 - sqrt(mean_c7 / (mean_c7 + 25**7)))

    a1_prime = (1 + g) * a1
    a2_prime = (1 + g) * a2
    c1_prime = sqrt(a1_prime * a1_prime + b1 * b1)
    c2_prime = sqrt(a2_prime * a2_prime + b2 * b2)

    h1_prime = _normalize_hue(
        0 if c1_prime == 0 else atan2(b1, a1_prime) * 180 / pi
    )
    h2_prime = _normalize_hue(
        0 if c2_prime == 0 else atan2(b2, a2_prime) * 180 / pi
    )

    delta_l_prime = l2 - l1
    delta_c_prime = c2_prime - c1_prime
    delta_h_prime = _delta_hue(h1_prime, h2_prime)
    delta_h_prime_rad = radians(delta_h_prime / 2)
    delta_h_cap = 2 * sqrt(c1_prime * c2_prime) * sin(delta_h_prime_rad)

    mean_l_prime = (l1 + l2) / 2
    mean_c_prime = (c1_prime + c2_prime) / 2
    mean_h_prime = _mean_hue(h1_prime, h2_prime, c1_prime, c2_prime)

    t = (
        1
        - 0.17 * cos(radians(mean_h_prime - 30))
        + 0.24 * cos(radians(2 * mean_h_prime))
        + 0.32 * cos(radians(3 * mean_h_prime + 6))
        - 0.20 * cos(radians(4 * mean_h_prime - 63))
    )

    delta_theta = 30 * exp(-((mean_h_prime - 275) / 25) ** 2)
    r_c = 2 * sqrt((mean_c_prime**7) / (mean_c_prime**7 + 25**7))
    s_l = 1 + (0.015 * (mean_l_prime - 50) ** 2) / sqrt(20 + (mean_l_prime - 50) ** 2)
    s_c = 1 + 0.045 * mean_c_prime
    s_h = 1 + 0.015 * mean_c_prime * t
    r_t = -sin(radians(2 * delta_theta)) * r_c

    delta_l = delta_l_prime / s_l
    delta_c = delta_c_prime / s_c
    delta_h = delta_h_cap / s_h
    return sqrt(delta_l * delta_l + delta_c * delta_c + delta_h * delta_h + r_t * delta_c * delta_h)


def _patch_group(role: PatchRole) -> PatchGroup:
    if role in {PatchRole.GRAYSCALE, PatchRole.DEEP_BLACK, PatchRole.NEAR_WHITE}:
        return PatchGroup.GRAYSCALE
    if role in {PatchRole.NEUTRAL, PatchRole.WARM_NEUTRAL}:
        return PatchGroup.NEUTRALS
    return PatchGroup.SATURATED


def _require_patch_roles(patches: Iterable[ColorPatch]) -> None:
    patch_list = list(patches)
    roles = {patch.role for patch in patch_list}
    required = {
        PatchRole.DEEP_BLACK,
        PatchRole.NEAR_WHITE,
        PatchRole.NEUTRAL,
        PatchRole.WARM_NEUTRAL,
        PatchRole.PRIMARY_RED,
        PatchRole.PRIMARY_GREEN,
        PatchRole.PRIMARY_BLUE,
        PatchRole.SECONDARY_CYAN,
        PatchRole.SECONDARY_MAGENTA,
        PatchRole.SECONDARY_YELLOW,
    }
    missing = sorted(role.value for role in required if role not in roles)
    grayscale_count = sum(1 for patch in patch_list if patch.role == PatchRole.GRAYSCALE)
    if grayscale_count < 2:
        missing.append("grayscale_ramp")
    if missing:
        raise ValueError(f"Missing required patch roles: {missing}")


def _resolve_output_mode(scene: ColorProfileScene) -> OutputTransformMode:
    profile_hash = scene.icc_profile.profile_hash if scene.icc_profile else None
    if not profile_hash:
        return OutputTransformMode.SRGB_FALLBACK
    if scene.reference_mode:
        return OutputTransformMode.REFERENCE_CLAMP
    if scene.output_transform_mode is not None:
        return scene.output_transform_mode
    gamut_hint = (scene.icc_profile.gamut_hint or "").lower() if scene.icc_profile else ""
    if gamut_hint in {"wide", "wide-gamut", "wide_gamut"}:
        return OutputTransformMode.WIDE_GAMUT_NORMAL
    return OutputTransformMode.SRGB_FALLBACK


def evaluate_color_profile_scene(scene: ColorProfileScene) -> ColorQaReport:
    _require_patch_roles(scene.patches)
    output_mode = _resolve_output_mode(scene)
    icc_hash = (
        scene.icc_profile.profile_hash
        if scene.icc_profile and scene.icc_profile.profile_hash
        else OutputTransformMode.SRGB_FALLBACK.value
    )

    patches: list[PatchDelta] = []
    group_values: dict[PatchGroup, list[float]] = {key: [] for key in _GROUP_THRESHOLDS}
    oversaturation_failures: list[str] = []
    for patch in scene.patches:
        delta_e = delta_e_ciede2000(patch.reference_lab, patch.sample_lab)
        group = _patch_group(patch.role)
        group_values[group].append(delta_e)
        chroma_delta = _lab_chroma(patch.sample_lab) - _lab_chroma(patch.reference_lab)
        if output_mode == OutputTransformMode.WIDE_GAMUT_NORMAL and patch.role in {
            PatchRole.PRIMARY_RED,
            PatchRole.PRIMARY_GREEN,
            PatchRole.PRIMARY_BLUE,
        }:
            if chroma_delta > 0 and delta_e > _GROUP_THRESHOLDS[PatchGroup.SATURATED]["max"]:
                oversaturation_failures.append(patch.name)
        patches.append(
            PatchDelta(
                name=patch.name,
                role=patch.role,
                group=group,
                delta_e00=delta_e,
                chroma_delta=chroma_delta,
            )
        )

    summary: dict[str, GroupSummary] = {}
    passed = True
    for group, values in group_values.items():
        thresholds = _GROUP_THRESHOLDS[group]
        max_value = max(values)
        mean_value = sum(values) / len(values)
        status = QaStatus.PASS
        if max_value > thresholds["max"] or mean_value > thresholds["mean"]:
            status = QaStatus.FAIL
            passed = False
        summary[group.value] = GroupSummary(
            max_delta_e00=max_value,
            mean_delta_e00=mean_value,
            threshold_max=thresholds["max"],
            threshold_mean=thresholds["mean"],
            status=status,
        )

    oversaturation_status = QaStatus.PASS
    if output_mode == OutputTransformMode.WIDE_GAMUT_NORMAL and oversaturation_failures:
        oversaturation_status = QaStatus.FAIL
        passed = False
    if output_mode != OutputTransformMode.WIDE_GAMUT_NORMAL:
        oversaturation_failures = []

    oversaturation = OversaturationSummary(
        status=oversaturation_status,
        failures=oversaturation_failures,
    )

    return ColorQaReport(
        icc_profile_hash=icc_hash,
        output_transform_mode=output_mode,
        patches=patches,
        summary=summary,
        oversaturation=oversaturation,
        passed=passed,
    )
