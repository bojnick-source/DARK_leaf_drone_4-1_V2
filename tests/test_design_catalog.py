"""Tests for the design catalog module."""

from __future__ import annotations

from reidce.design_catalog import (
    DESIGN_CATALOG,
    CatalogValidation,
    catalog_summary,
    get_design,
    get_designs_by_category,
    validate_catalog,
    validate_design,
)


def test_catalog_has_17_designs() -> None:
    assert len(DESIGN_CATALOG) == 17


def test_catalog_unique_ids() -> None:
    ids = [e.design_id for e in DESIGN_CATALOG]
    assert len(ids) == len(set(ids))


def test_catalog_sequential_ids() -> None:
    for i, entry in enumerate(DESIGN_CATALOG, start=1):
        assert entry.design_id == f"DESIGN_{i:03d}"


def test_catalog_categories() -> None:
    categories = {e.category for e in DESIGN_CATALOG}
    assert categories == {"racing", "endurance", "heavy_lift", "agile", "balanced"}


def test_racing_count() -> None:
    assert len(get_designs_by_category("racing")) == 4


def test_endurance_count() -> None:
    assert len(get_designs_by_category("endurance")) == 3


def test_heavy_lift_count() -> None:
    assert len(get_designs_by_category("heavy_lift")) == 3


def test_agile_count() -> None:
    assert len(get_designs_by_category("agile")) == 4


def test_balanced_count() -> None:
    assert len(get_designs_by_category("balanced")) == 3


def test_get_design_exists() -> None:
    entry = get_design("DESIGN_001")
    assert entry is not None
    assert entry.name == "Viper Sprint"


def test_get_design_last() -> None:
    entry = get_design("DESIGN_017")
    assert entry is not None
    assert entry.category == "balanced"


def test_get_design_missing() -> None:
    assert get_design("DESIGN_999") is None


def test_designs_by_unknown_category() -> None:
    assert get_designs_by_category("submarine") == []


def test_validate_design_basic() -> None:
    entry = get_design("DESIGN_015")
    assert entry is not None
    result = validate_design(entry)
    assert isinstance(result, CatalogValidation)
    assert result.is_valid is True
    assert result.thrust_to_weight > 1.0


def test_validate_catalog_all_valid() -> None:
    results = validate_catalog()
    assert len(results) == 17
    for v in results:
        assert v.is_valid is True, f"{v.design_id} should be valid"


def test_validate_catalog_tw_above_one() -> None:
    for v in validate_catalog():
        assert v.thrust_to_weight > 1.0


def test_validate_design_disk_loading_positive() -> None:
    for v in validate_catalog():
        assert v.disk_loading_n_m2 > 0.0


def test_validate_design_power_loading_positive() -> None:
    for v in validate_catalog():
        assert v.power_loading_kg_w > 0.0


def test_catalog_summary_structure() -> None:
    summary = catalog_summary()
    assert summary["total"] == 17
    assert summary["valid_count"] == 17
    assert summary["invalid_count"] == 0
    assert "by_category" in summary
    assert "categories" in summary


def test_catalog_summary_categories() -> None:
    summary = catalog_summary()
    assert sorted(summary["categories"]) == [
        "agile", "balanced", "endurance", "heavy_lift", "racing"
    ]


def test_design_entry_physically_realistic() -> None:
    for entry in DESIGN_CATALOG:
        assert 1.0 <= entry.mass_kg <= 5.0, f"{entry.design_id} mass out of range"
        assert 0.1 <= entry.wing_area_m2 <= 0.6, f"{entry.design_id} wing area out of range"
        assert 0.01 <= entry.cd0 <= 0.1, f"{entry.design_id} cd0 out of range"
        assert 20.0 <= entry.max_thrust_n <= 100.0, f"{entry.design_id} thrust out of range"
        assert entry.max_speed_m_s <= 100.0, f"{entry.design_id} speed too high"
        assert 0.05 <= entry.rotor_radius_m <= 0.25, f"{entry.design_id} rotor radius range"
        assert entry.n_rotors >= 2


def test_design_entry_has_description() -> None:
    for entry in DESIGN_CATALOG:
        assert len(entry.description) > 0, f"{entry.design_id} missing description"
