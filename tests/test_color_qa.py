import pytest

from sfcs_mdp.color_qa import (
    ColorPatch,
    ColorProfileInfo,
    ColorProfileScene,
    LabColor,
    OutputTransformMode,
    PatchRole,
    QaStatus,
    evaluate_color_profile_scene,
)


def _patch(name: str, role: PatchRole, reference: LabColor, sample: LabColor) -> ColorPatch:
    return ColorPatch(name=name, role=role, reference_lab=reference, sample_lab=sample)


def _baseline_patches() -> list[ColorPatch]:
    return [
        _patch("gray_10", PatchRole.GRAYSCALE, LabColor(L=10, a=0, b=0), LabColor(L=10, a=0, b=0)),
        _patch("gray_50", PatchRole.GRAYSCALE, LabColor(L=50, a=0, b=0), LabColor(L=50, a=0, b=0)),
        _patch(
            "neutral_mid",
            PatchRole.NEUTRAL,
            LabColor(L=50, a=0.5, b=-0.2),
            LabColor(L=50, a=0.5, b=-0.2),
        ),
        _patch(
            "warm_mid",
            PatchRole.WARM_NEUTRAL,
            LabColor(L=55, a=4, b=6),
            LabColor(L=55, a=4, b=6),
        ),
        _patch(
            "red",
            PatchRole.PRIMARY_RED,
            LabColor(L=50, a=70, b=40),
            LabColor(L=50, a=70, b=40),
        ),
        _patch(
            "green",
            PatchRole.PRIMARY_GREEN,
            LabColor(L=50, a=-60, b=60),
            LabColor(L=50, a=-60, b=60),
        ),
        _patch(
            "blue",
            PatchRole.PRIMARY_BLUE,
            LabColor(L=50, a=0, b=-70),
            LabColor(L=50, a=0, b=-70),
        ),
        _patch(
            "cyan",
            PatchRole.SECONDARY_CYAN,
            LabColor(L=60, a=-40, b=-20),
            LabColor(L=60, a=-40, b=-20),
        ),
        _patch(
            "magenta",
            PatchRole.SECONDARY_MAGENTA,
            LabColor(L=50, a=70, b=-20),
            LabColor(L=50, a=70, b=-20),
        ),
        _patch(
            "yellow",
            PatchRole.SECONDARY_YELLOW,
            LabColor(L=70, a=-5, b=70),
            LabColor(L=70, a=-5, b=70),
        ),
        _patch(
            "deep_black",
            PatchRole.DEEP_BLACK,
            LabColor(L=0, a=0, b=0),
            LabColor(L=0, a=0, b=0),
        ),
        _patch(
            "near_white",
            PatchRole.NEAR_WHITE,
            LabColor(L=98, a=0, b=0),
            LabColor(L=98, a=0, b=0),
        ),
    ]


def test_color_qa_passes_srgb_fallback() -> None:
    scene = ColorProfileScene(
        icc_profile=ColorProfileInfo(profile_hash=None),
        reference_mode=False,
        patches=_baseline_patches(),
    )
    report = evaluate_color_profile_scene(scene)
    assert report.passed is True
    assert report.output_transform_mode == OutputTransformMode.SRGB_FALLBACK
    assert report.icc_profile_hash == OutputTransformMode.SRGB_FALLBACK.value


def test_color_qa_flags_wide_gamut_oversaturation() -> None:
    patches = _baseline_patches()
    patches[4] = _patch(
        "red",
        PatchRole.PRIMARY_RED,
        LabColor(L=50, a=70, b=40),
        LabColor(L=50, a=95, b=50),
    )
    scene = ColorProfileScene(
        icc_profile=ColorProfileInfo(profile_hash="HASH1", gamut_hint="wide"),
        reference_mode=False,
        patches=patches,
    )
    report = evaluate_color_profile_scene(scene)
    assert report.output_transform_mode == OutputTransformMode.WIDE_GAMUT_NORMAL
    assert report.oversaturation.status == QaStatus.FAIL
    assert report.passed is False


def test_color_qa_reference_clamp_mode() -> None:
    scene = ColorProfileScene(
        icc_profile=ColorProfileInfo(profile_hash="HASH2"),
        reference_mode=True,
        patches=_baseline_patches(),
    )
    report = evaluate_color_profile_scene(scene)
    assert report.output_transform_mode == OutputTransformMode.REFERENCE_CLAMP
    assert report.passed is True


def test_color_qa_missing_required_patches() -> None:
    scene = ColorProfileScene(
        icc_profile=ColorProfileInfo(profile_hash="HASH2"),
        reference_mode=False,
        patches=_baseline_patches()[:2],
    )
    with pytest.raises(ValueError, match="Missing required patch roles"):
        evaluate_color_profile_scene(scene)


def test_color_qa_grayscale_threshold_failure() -> None:
    patches = _baseline_patches()
    patches[0] = _patch(
        "gray_10",
        PatchRole.GRAYSCALE,
        LabColor(L=10, a=0, b=0),
        LabColor(L=25, a=0, b=0),
    )
    scene = ColorProfileScene(
        icc_profile=ColorProfileInfo(profile_hash=None),
        reference_mode=False,
        patches=patches,
    )
    report = evaluate_color_profile_scene(scene)
    assert report.summary["grayscale"].status == QaStatus.FAIL


def test_color_qa_neutral_threshold_failure() -> None:
    patches = _baseline_patches()
    patches[2] = _patch(
        "neutral_mid",
        PatchRole.NEUTRAL,
        LabColor(L=50, a=0.5, b=-0.2),
        LabColor(L=50, a=10, b=-10),
    )
    scene = ColorProfileScene(
        icc_profile=ColorProfileInfo(profile_hash=None),
        reference_mode=False,
        patches=patches,
    )
    report = evaluate_color_profile_scene(scene)
    assert report.summary["neutrals"].status == QaStatus.FAIL


def test_delta_e_handles_achromatic() -> None:
    scene = ColorProfileScene(
        icc_profile=ColorProfileInfo(profile_hash=None),
        reference_mode=False,
        patches=[
            _patch(
                "gray_20",
                PatchRole.GRAYSCALE,
                LabColor(L=20, a=0, b=0),
                LabColor(L=20, a=0, b=0),
            ),
            _patch(
                "gray_40",
                PatchRole.GRAYSCALE,
                LabColor(L=40, a=0, b=0),
                LabColor(L=40, a=0, b=0),
            ),
            _patch(
                "neutral_mid",
                PatchRole.NEUTRAL,
                LabColor(L=50, a=0.5, b=-0.2),
                LabColor(L=50, a=0.5, b=-0.2),
            ),
            _patch(
                "warm_mid",
                PatchRole.WARM_NEUTRAL,
                LabColor(L=55, a=4, b=6),
                LabColor(L=55, a=4, b=6),
            ),
            _patch(
                "red",
                PatchRole.PRIMARY_RED,
                LabColor(L=50, a=70, b=40),
                LabColor(L=50, a=70, b=40),
            ),
            _patch(
                "green",
                PatchRole.PRIMARY_GREEN,
                LabColor(L=50, a=-60, b=60),
                LabColor(L=50, a=-60, b=60),
            ),
            _patch(
                "blue",
                PatchRole.PRIMARY_BLUE,
                LabColor(L=50, a=0, b=-70),
                LabColor(L=50, a=0, b=-70),
            ),
            _patch(
                "cyan",
                PatchRole.SECONDARY_CYAN,
                LabColor(L=60, a=-40, b=-20),
                LabColor(L=60, a=-40, b=-20),
            ),
            _patch(
                "magenta",
                PatchRole.SECONDARY_MAGENTA,
                LabColor(L=50, a=70, b=-20),
                LabColor(L=50, a=70, b=-20),
            ),
            _patch(
                "yellow",
                PatchRole.SECONDARY_YELLOW,
                LabColor(L=70, a=-5, b=70),
                LabColor(L=70, a=-5, b=70),
            ),
            _patch(
                "deep_black",
                PatchRole.DEEP_BLACK,
                LabColor(L=0, a=0, b=0),
                LabColor(L=0, a=0, b=0),
            ),
            _patch(
                "near_white",
                PatchRole.NEAR_WHITE,
                LabColor(L=98, a=0, b=0),
                LabColor(L=98, a=0, b=0),
            ),
        ],
    )
    report = evaluate_color_profile_scene(scene)
    assert all(patch.delta_e00 == pytest.approx(0.0) for patch in report.patches)
