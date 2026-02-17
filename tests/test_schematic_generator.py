"""Tests for reidce.schematic_generator — 2D engineering schematic generator."""

from reidce.schematic_generator import (
    Annotation,
    BlueprintResult,
    BlueprintSpec,
    BOMEntry,
    DimensionLine,
    Point2D,
    TitleBlock,
    ViewPort,
    generate_drone_blueprint,
)

# ── BlueprintSpec ────────────────────────────────────────────────────────


def test_blueprint_spec_defaults() -> None:
    spec = BlueprintSpec()
    assert spec.arm_count == 4
    assert spec.sheet_width_mm == 841.0
    assert spec.title == "DARK Leaf 4-1 Competition Drone"


def test_blueprint_spec_custom() -> None:
    spec = BlueprintSpec(arm_count=6, scale=3.0, title="Custom Drone")
    assert spec.arm_count == 6
    assert spec.scale == 3.0


# ── Point2D ──────────────────────────────────────────────────────────────


def test_point2d() -> None:
    p = Point2D(10.0, 20.0)
    assert p.x == 10.0
    assert p.y == 20.0


# ── DimensionLine ────────────────────────────────────────────────────────


def test_dimension_line_length() -> None:
    dim = DimensionLine(Point2D(0.0, 0.0), Point2D(100.0, 0.0), "100")
    assert abs(dim.length_mm - 100.0) < 0.01


def test_dimension_line_vertical() -> None:
    dim = DimensionLine(Point2D(0.0, 0.0), Point2D(0.0, 50.0), "50", vertical=True)
    assert dim.vertical is True
    assert abs(dim.length_mm - 50.0) < 0.01


# ── Annotation ───────────────────────────────────────────────────────────


def test_annotation() -> None:
    ann = Annotation(Point2D(5.0, 10.0), "MOTOR M1")
    assert ann.text == "MOTOR M1"
    assert ann.font_size == 7.0


# ── TitleBlock ───────────────────────────────────────────────────────────


def test_title_block() -> None:
    tb = TitleBlock(
        title="Test",
        drawing_number="DRW-001",
        revision="B",
        scale_text="2:1",
        sheet_size="A0",
    )
    assert tb.title == "Test"
    assert tb.project == "DARK Leaf 4-1 V2"


# ── BOMEntry ─────────────────────────────────────────────────────────────


def test_bom_entry() -> None:
    entry = BOMEntry(1, "Hub", 1, "AL 7075", 45.0)
    assert entry.item == 1
    assert entry.mass_g == 45.0


# ── ViewPort ─────────────────────────────────────────────────────────────


def test_viewport_creation() -> None:
    vp = ViewPort("top", 10.0, 20.0, 300.0, 200.0, 2.0)
    assert vp.name == "top"
    assert vp.scale == 2.0


# ── generate_drone_blueprint ─────────────────────────────────────────────


def test_blueprint_default() -> None:
    result = generate_drone_blueprint()
    assert isinstance(result, BlueprintResult)
    assert result.is_valid
    assert result.view_count == 3
    assert result.dimension_count > 0
    assert result.annotation_count > 0
    assert len(result.svg_content) > 1000


def test_blueprint_contains_svg_structure() -> None:
    result = generate_drone_blueprint()
    assert result.svg_content.startswith("<svg")
    assert "</svg>" in result.svg_content
    assert "viewBox" in result.svg_content


def test_blueprint_contains_views() -> None:
    result = generate_drone_blueprint()
    assert "TOP VIEW" in result.svg_content
    assert "FRONT VIEW" in result.svg_content
    assert "SIDE VIEW" in result.svg_content


def test_blueprint_contains_dimensions() -> None:
    result = generate_drone_blueprint()
    # Should have dimension arrows (polygon elements)
    assert "<polygon" in result.svg_content
    # Should have dimension text
    assert "⌀" in result.svg_content  # diameter symbol


def test_blueprint_contains_title_block() -> None:
    result = generate_drone_blueprint()
    assert "TITLE:" in result.svg_content
    assert "DWG NO:" in result.svg_content
    assert "DRW-4-1-001" in result.svg_content


def test_blueprint_contains_bom() -> None:
    result = generate_drone_blueprint()
    assert "BILL OF MATERIALS" in result.svg_content
    assert "Central Hub" in result.svg_content
    assert "Brushless Motor" in result.svg_content
    assert len(result.bom_entries) >= 8


def test_blueprint_contains_tolerances() -> None:
    result = generate_drone_blueprint()
    assert "GENERAL TOLERANCE" in result.svg_content
    assert "SURFACE FINISH" in result.svg_content
    assert "ALL DIMENSIONS IN MILLIMETERS" in result.svg_content


def test_blueprint_custom_spec() -> None:
    spec = BlueprintSpec(
        arm_count=6,
        scale=3.0,
        title="Hex Drone Blueprint",
    )
    result = generate_drone_blueprint(spec)
    assert result.is_valid
    assert result.title == "Hex Drone Blueprint"
    assert result.view_count == 3


def test_blueprint_smaller_sheet() -> None:
    spec = BlueprintSpec(sheet_width_mm=420.0, sheet_height_mm=297.0)
    result = generate_drone_blueprint(spec)
    assert result.is_valid
    assert result.sheet_width_mm == 420.0
    assert result.sheet_height_mm == 297.0


def test_blueprint_to_dict() -> None:
    result = generate_drone_blueprint()
    d = result.to_dict()
    assert d["schema"] == "dark/blueprint_result/1.0"
    assert d["view_count"] == 3
    assert d["svg_length"] > 0
    assert d["bom_item_count"] >= 8


def test_blueprint_bom_entries_valid() -> None:
    result = generate_drone_blueprint()
    for entry in result.bom_entries:
        assert entry.item > 0
        assert len(entry.description) > 0
        assert entry.quantity > 0
        assert entry.mass_g > 0


def test_blueprint_zone_markers() -> None:
    result = generate_drone_blueprint()
    # Should have zone markers A-F
    for letter in "ABCDEF":
        assert f">{letter}<" in result.svg_content


def test_blueprint_centerline() -> None:
    result = generate_drone_blueprint()
    # Front view should have a dashed centerline
    assert 'stroke-dasharray="4,2"' in result.svg_content
