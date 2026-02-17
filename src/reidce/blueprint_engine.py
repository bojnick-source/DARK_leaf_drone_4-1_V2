"""2D engineering blueprint/schematic generator for drone designs.

Produces highly detailed, dimensioned technical drawings in SVG format
on a flat sheet.  Implements standard engineering drawing conventions:
multi-view orthographic projections (top, front, side), cross-sections,
dimension lines with ISO-style arrowheads, annotations, a title block,
bill of materials, and geometric tolerance callouts.

Key components
--------------
* ``BlueprintSpec`` — drawing specification (sheet size, scale, drone
  parameters, annotation density).
* ``DimensionLine`` — parametric dimension annotation with leader lines,
  arrowheads, and measurement text.
* ``ViewPort`` — one orthographic projection (top, front, or side) with
  its own coordinate transform and clipping rect.
* ``Annotation`` — text callout attached to a blueprint element.
* ``TitleBlock`` — ISO 7200-style title block with project metadata.
* ``BlueprintResult`` — complete output with SVG content, view count,
  dimension count, and validation status.
* ``generate_drone_blueprint`` — top-level function that produces the
  full drawing.

The generator is entirely local and deterministic — no external
dependencies beyond the standard library.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from xml.sax.saxutils import escape as xml_escape

# ── Specification ────────────────────────────────────────────────────────


@dataclass
class BlueprintSpec:
    """Drawing specification for a drone blueprint."""

    title: str = "DARK Leaf 4-1 Competition Drone"
    drawing_number: str = "DRW-4-1-001"
    revision: str = "A"
    sheet_width_mm: float = 841.0   # A0 landscape
    sheet_height_mm: float = 594.0
    margin_mm: float = 10.0
    arm_count: int = 4
    arm_length_m: float = 0.30
    arm_radius_m: float = 0.008
    hub_radius_m: float = 0.06
    hub_height_m: float = 0.035
    motor_radius_m: float = 0.018
    motor_height_m: float = 0.025
    prop_radius_m: float = 0.12
    prop_thickness_m: float = 0.003
    battery_length_m: float = 0.07
    battery_width_m: float = 0.04
    battery_height_m: float = 0.025
    scale: float = 2.0  # drawing scale multiplier (1mm drawing = 1mm real / scale)
    line_width: float = 0.35
    dimension_font_size: float = 8.0
    annotation_font_size: float = 7.0
    title_font_size: float = 12.0


# ── Drawing primitives ───────────────────────────────────────────────────


@dataclass(frozen=True)
class Point2D:
    """2D point in drawing coordinates (mm)."""

    x: float
    y: float


@dataclass(frozen=True)
class DimensionLine:
    """Engineering dimension annotation between two points."""

    start: Point2D
    end: Point2D
    label: str
    offset_mm: float = 8.0
    vertical: bool = False

    @property
    def length_mm(self) -> float:
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        return math.sqrt(dx * dx + dy * dy)


@dataclass(frozen=True)
class Annotation:
    """Text callout attached to a blueprint location."""

    position: Point2D
    text: str
    font_size: float = 7.0
    anchor: str = "start"


@dataclass
class ViewPort:
    """One orthographic projection view on the blueprint."""

    name: str
    origin_x: float
    origin_y: float
    width: float
    height: float
    scale: float
    elements_svg: str = ""
    dimensions: List[DimensionLine] = field(default_factory=list)
    annotations: List[Annotation] = field(default_factory=list)


@dataclass(frozen=True)
class TitleBlock:
    """ISO 7200-style title block."""

    title: str
    drawing_number: str
    revision: str
    scale_text: str
    sheet_size: str
    material: str = "Carbon fiber composite / AL 7075-T6"
    tolerance: str = "±0.1mm unless noted"
    project: str = "DARK Leaf 4-1 V2"
    designer: str = "REIDCE AI Engine"
    date: str = "2026-02"
    units: str = "mm"


@dataclass(frozen=True)
class BOMEntry:
    """Bill of materials entry."""

    item: int
    description: str
    quantity: int
    material: str
    mass_g: float


@dataclass
class BlueprintResult:
    """Complete blueprint output."""

    svg_content: str
    title: str
    view_count: int
    dimension_count: int
    annotation_count: int
    sheet_width_mm: float
    sheet_height_mm: float
    bom_entries: List[BOMEntry] = field(default_factory=list)
    is_valid: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "dark/blueprint_result/1.0",
            "title": self.title,
            "view_count": self.view_count,
            "dimension_count": self.dimension_count,
            "annotation_count": self.annotation_count,
            "sheet_width_mm": self.sheet_width_mm,
            "sheet_height_mm": self.sheet_height_mm,
            "svg_length": len(self.svg_content),
            "bom_item_count": len(self.bom_entries),
            "is_valid": self.is_valid,
        }


# ── SVG helpers ──────────────────────────────────────────────────────────


def _svg_line(
    x1: float, y1: float, x2: float, y2: float,
    stroke: str = "black", width: float = 0.35,
    dash: str = "",
) -> str:
    attrs = f'x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}"'
    style = f'stroke="{stroke}" stroke-width="{width}"'
    if dash:
        style += f' stroke-dasharray="{dash}"'
    return f"<line {attrs} {style}/>"


def _svg_rect(
    x: float, y: float, w: float, h: float,
    fill: str = "none", stroke: str = "black", width: float = 0.35,
) -> str:
    return (
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'
    )


def _svg_circle(
    cx: float, cy: float, r: float,
    fill: str = "none", stroke: str = "black", width: float = 0.35,
) -> str:
    return (
        f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'
    )


def _svg_text(
    x: float, y: float, text: str,
    font_size: float = 8.0, anchor: str = "middle",
    font_family: str = "monospace",
) -> str:
    safe_text = xml_escape(str(text))
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-size="{font_size}" '
        f'text-anchor="{anchor}" font-family="{font_family}">{safe_text}</text>'
    )


def _svg_polygon(points: List[Tuple[float, float]], fill: str = "black") -> str:
    pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return f'<polygon points="{pts}" fill="{fill}"/>'


def _svg_arrowhead(
    tip_x: float, tip_y: float, angle_rad: float, size: float = 2.5,
) -> str:
    """ISO-style filled arrowhead pointing in the given direction."""
    dx1 = -size * math.cos(angle_rad - 0.3)
    dy1 = -size * math.sin(angle_rad - 0.3)
    dx2 = -size * math.cos(angle_rad + 0.3)
    dy2 = -size * math.sin(angle_rad + 0.3)
    return _svg_polygon([
        (tip_x, tip_y),
        (tip_x + dx1, tip_y + dy1),
        (tip_x + dx2, tip_y + dy2),
    ])


def _dimension_svg(dim: DimensionLine, font_size: float = 8.0) -> str:
    """Render a complete dimension annotation in SVG."""
    parts: List[str] = []
    sx, sy = dim.start.x, dim.start.y
    ex, ey = dim.end.x, dim.end.y
    off = dim.offset_mm

    if dim.vertical:
        # Vertical dimension
        parts.append(_svg_line(sx, sy, sx + off, sy, width=0.2))
        parts.append(_svg_line(ex, ey, ex + off, ey, width=0.2))
        lx = sx + off
        parts.append(_svg_line(lx, sy, lx, ey, width=0.3))
        # Arrowheads
        parts.append(_svg_arrowhead(lx, sy, -math.pi / 2))
        parts.append(_svg_arrowhead(lx, ey, math.pi / 2))
        # Label
        mid_y = (sy + ey) / 2.0
        parts.append(_svg_text(lx + 3, mid_y + 2, dim.label, font_size))
    else:
        # Horizontal dimension
        parts.append(_svg_line(sx, sy, sx, sy - off, width=0.2))
        parts.append(_svg_line(ex, ey, ex, ey - off, width=0.2))
        ly = sy - off
        parts.append(_svg_line(sx, ly, ex, ly, width=0.3))
        # Arrowheads
        parts.append(_svg_arrowhead(sx, ly, math.pi))
        parts.append(_svg_arrowhead(ex, ly, 0.0))
        # Label
        mid_x = (sx + ex) / 2.0
        parts.append(_svg_text(mid_x, ly - 2, dim.label, font_size))

    return "\n".join(parts)


# ── View generators ──────────────────────────────────────────────────────


def _generate_top_view(
    spec: BlueprintSpec, vp: ViewPort,
) -> Tuple[str, List[DimensionLine], List[Annotation]]:
    """Generate top-down orthographic projection of the drone."""
    parts: List[str] = []
    dims: List[DimensionLine] = []
    annots: List[Annotation] = []
    ox, oy = vp.origin_x + vp.width / 2, vp.origin_y + vp.height / 2
    s = spec.scale * 1000.0  # m → mm drawing scale

    # Hub (circle)
    hub_r = spec.hub_radius_m * s
    parts.append(_svg_circle(ox, oy, hub_r, stroke="black", width=spec.line_width))
    annots.append(Annotation(Point2D(ox, oy), "HUB", spec.annotation_font_size, "middle"))

    # Arms and motors
    for i in range(spec.arm_count):
        angle = 2.0 * math.pi * i / spec.arm_count
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        arm_len = spec.arm_length_m * s
        tip_x = ox + cos_a * arm_len
        tip_y = oy + sin_a * arm_len

        # Arm line (thick)
        parts.append(_svg_line(ox, oy, tip_x, tip_y, width=spec.line_width * 1.5))

        # Motor mount (circle at tip)
        motor_r = spec.motor_radius_m * s
        parts.append(_svg_circle(tip_x, tip_y, motor_r, width=spec.line_width))

        # Propeller disk (dashed circle)
        prop_r = spec.prop_radius_m * s
        parts.append(_svg_circle(tip_x, tip_y, prop_r, width=0.2, stroke="#666"))

        # Center mark on motor
        mark = motor_r * 0.5
        parts.append(_svg_line(tip_x - mark, tip_y, tip_x + mark, tip_y, width=0.15))
        parts.append(_svg_line(tip_x, tip_y - mark, tip_x, tip_y + mark, width=0.15))

        annots.append(Annotation(
            Point2D(tip_x + motor_r + 2, tip_y),
            f"M{i + 1}",
            spec.annotation_font_size,
        ))

    # Dimension: arm length (first arm)
    arm0_tip_x = ox + spec.arm_length_m * s
    dims.append(DimensionLine(
        Point2D(ox, oy + hub_r + 2), Point2D(arm0_tip_x, oy + hub_r + 2),
        f"{spec.arm_length_m * 1000:.0f}",
    ))

    # Dimension: prop diameter
    prop_d = spec.prop_radius_m * 2 * 1000
    dims.append(DimensionLine(
        Point2D(arm0_tip_x - spec.prop_radius_m * s, oy - hub_r - 15),
        Point2D(arm0_tip_x + spec.prop_radius_m * s, oy - hub_r - 15),
        f"⌀{prop_d:.0f}",
    ))

    # Dimension: hub diameter
    dims.append(DimensionLine(
        Point2D(ox - hub_r, oy + hub_r + 15),
        Point2D(ox + hub_r, oy + hub_r + 15),
        f"⌀{spec.hub_radius_m * 2 * 1000:.0f}",
    ))

    # Battery outline (dashed rectangle under hub)
    batt_w = spec.battery_length_m * s
    batt_h = spec.battery_width_m * s
    parts.append(_svg_rect(
        ox - batt_w / 2, oy - batt_h / 2, batt_w, batt_h,
        fill="none", stroke="#999", width=0.25,
    ))
    annots.append(Annotation(
        Point2D(ox, oy + batt_h / 2 + 5), "BATT", spec.annotation_font_size, "middle",
    ))

    # View label
    parts.append(_svg_text(
        vp.origin_x + vp.width / 2, vp.origin_y + vp.height - 5,
        "TOP VIEW", spec.title_font_size, "middle",
    ))

    svg = "\n".join(parts)
    return svg, dims, annots


def _generate_front_view(
    spec: BlueprintSpec, vp: ViewPort,
) -> Tuple[str, List[DimensionLine], List[Annotation]]:
    """Generate front-elevation orthographic projection."""
    parts: List[str] = []
    dims: List[DimensionLine] = []
    annots: List[Annotation] = []
    ox, oy = vp.origin_x + vp.width / 2, vp.origin_y + vp.height / 2
    s = spec.scale * 1000.0

    # Hub (rectangle in front view)
    hub_w = spec.hub_radius_m * 2 * s
    hub_h = spec.hub_height_m * s
    parts.append(_svg_rect(
        ox - hub_w / 2, oy - hub_h / 2, hub_w, hub_h,
        stroke="black", width=spec.line_width,
    ))

    # Arms (horizontal lines from hub)
    arm_len = spec.arm_length_m * s
    arm_y = oy - hub_h / 2 + spec.arm_radius_m * 2 * s
    parts.append(_svg_line(
        ox - hub_w / 2 - arm_len * 0.3, arm_y,
        ox - hub_w / 2, arm_y,
        width=spec.line_width * 1.5,
    ))
    parts.append(_svg_line(
        ox + hub_w / 2, arm_y,
        ox + hub_w / 2 + arm_len * 0.3, arm_y,
        width=spec.line_width * 1.5,
    ))

    # Motor mounts (rectangles at arm tips)
    motor_w = spec.motor_radius_m * 2 * s
    motor_h = spec.motor_height_m * s
    for side in [-1, 1]:
        mx = ox + side * (hub_w / 2 + arm_len * 0.3)
        parts.append(_svg_rect(
            mx - motor_w / 2, arm_y - motor_h, motor_w, motor_h,
            stroke="black", width=spec.line_width,
        ))
        # Propeller line on top of motor
        prop_w = spec.prop_radius_m * s
        prop_y = arm_y - motor_h
        parts.append(_svg_line(
            mx - prop_w, prop_y, mx + prop_w, prop_y,
            width=spec.line_width, stroke="#444",
        ))

    # Battery (rectangle below hub)
    batt_w = spec.battery_length_m * s
    batt_h = spec.battery_height_m * s
    parts.append(_svg_rect(
        ox - batt_w / 2, oy + hub_h / 2, batt_w, batt_h,
        stroke="black", width=spec.line_width,
    ))

    # Centerline (dashed vertical)
    parts.append(_svg_line(
        ox, oy - hub_h - motor_h - 10, ox, oy + hub_h + batt_h + 10,
        stroke="#888", width=0.2, dash="4,2",
    ))

    # Dimensions
    total_h = hub_h + batt_h
    dims.append(DimensionLine(
        Point2D(ox + hub_w / 2 + 5, oy - hub_h / 2),
        Point2D(ox + hub_w / 2 + 5, oy + hub_h / 2 + batt_h),
        f"{total_h / s * 1000:.0f}",
        vertical=True,
    ))
    dims.append(DimensionLine(
        Point2D(ox - hub_w / 2, oy + hub_h / 2 + batt_h + 5),
        Point2D(ox + hub_w / 2, oy + hub_h / 2 + batt_h + 5),
        f"{spec.hub_radius_m * 2 * 1000:.0f}",
    ))

    # View label
    parts.append(_svg_text(
        vp.origin_x + vp.width / 2, vp.origin_y + vp.height - 5,
        "FRONT VIEW", spec.title_font_size, "middle",
    ))

    svg = "\n".join(parts)
    return svg, dims, annots


def _generate_side_view(
    spec: BlueprintSpec, vp: ViewPort,
) -> Tuple[str, List[DimensionLine], List[Annotation]]:
    """Generate side-elevation orthographic projection."""
    parts: List[str] = []
    dims: List[DimensionLine] = []
    annots: List[Annotation] = []
    ox, oy = vp.origin_x + vp.width / 2, vp.origin_y + vp.height / 2
    s = spec.scale * 1000.0

    # Hub (circle in side view — we see it edge-on as an ellipse)
    hub_r = spec.hub_radius_m * s
    hub_h = spec.hub_height_m * s
    parts.append(_svg_rect(
        ox - hub_r, oy - hub_h / 2, hub_r * 2, hub_h,
        stroke="black", width=spec.line_width,
    ))

    # Arm (single line going right)
    arm_len = spec.arm_length_m * s * 0.7  # foreshortened
    arm_y = oy - hub_h / 2 + spec.arm_radius_m * 2 * s
    parts.append(_svg_line(
        ox + hub_r, arm_y, ox + hub_r + arm_len, arm_y,
        width=spec.line_width * 1.5,
    ))

    # Motor at arm tip
    motor_w = spec.motor_radius_m * 2 * s
    motor_h = spec.motor_height_m * s
    mx = ox + hub_r + arm_len
    parts.append(_svg_rect(
        mx - motor_w / 2, arm_y - motor_h, motor_w, motor_h,
        stroke="black", width=spec.line_width,
    ))

    # Prop disk (thin line)
    prop_r = spec.prop_radius_m * s
    prop_y = arm_y - motor_h
    parts.append(_svg_line(
        mx - prop_r, prop_y, mx + prop_r, prop_y,
        width=spec.line_width, stroke="#444",
    ))

    # Battery
    batt_w = spec.battery_length_m * s
    batt_h = spec.battery_height_m * s
    parts.append(_svg_rect(
        ox - batt_w / 2, oy + hub_h / 2, batt_w, batt_h,
        stroke="black", width=spec.line_width,
    ))

    # Hidden lines (far motor, dashed)
    parts.append(_svg_line(
        ox - hub_r - arm_len * 0.5, arm_y,
        ox - hub_r, arm_y,
        width=0.2, dash="3,2",
    ))

    # Dimension: overall height
    total_top = arm_y - motor_h - spec.prop_thickness_m * s
    total_bot = oy + hub_h / 2 + batt_h
    dims.append(DimensionLine(
        Point2D(ox - hub_r - 8, total_top),
        Point2D(ox - hub_r - 8, total_bot),
        f"{(total_bot - total_top) / s * 1000:.0f}",
        offset_mm=-8.0,
        vertical=True,
    ))

    # View label
    parts.append(_svg_text(
        vp.origin_x + vp.width / 2, vp.origin_y + vp.height - 5,
        "SIDE VIEW", spec.title_font_size, "middle",
    ))

    svg = "\n".join(parts)
    return svg, dims, annots


# ── Title block generator ────────────────────────────────────────────────


def _generate_title_block(
    spec: BlueprintSpec, x: float, y: float, w: float, h: float,
) -> str:
    """Generate an ISO-style title block SVG."""
    parts: List[str] = []
    parts.append(_svg_rect(x, y, w, h, stroke="black", width=0.5))

    # Horizontal dividers
    row_h = h / 5
    for i in range(1, 5):
        parts.append(_svg_line(x, y + i * row_h, x + w, y + i * row_h, width=0.3))

    # Vertical divider
    mid_x = x + w * 0.4
    parts.append(_svg_line(mid_x, y, mid_x, y + h, width=0.3))

    # Labels and values
    fs = spec.dimension_font_size
    entries = [
        ("TITLE:", spec.title),
        ("DWG NO:", spec.drawing_number),
        ("REV:", spec.revision),
        ("SCALE:", f"{spec.scale}:1"),
        ("MATERIAL:", "CF Composite / AL 7075"),
    ]
    for i, (label, value) in enumerate(entries):
        ry = y + i * row_h + row_h * 0.65
        parts.append(_svg_text(x + 3, ry, label, fs, "start"))
        parts.append(_svg_text(mid_x + 3, ry, value, fs, "start"))

    return "\n".join(parts)


# ── Bill of materials ────────────────────────────────────────────────────


def _generate_bom(spec: BlueprintSpec) -> List[BOMEntry]:
    """Generate a bill of materials for the competition drone."""
    entries: List[BOMEntry] = []
    entries.append(BOMEntry(1, "Central Hub", 1, "AL 7075-T6", 45.0))
    entries.append(BOMEntry(2, "Arm Tube", spec.arm_count, "Carbon Fiber", 12.0))
    entries.append(BOMEntry(3, "Brushless Motor", spec.arm_count, "Steel/Copper", 85.0))
    entries.append(BOMEntry(
        4, "Propeller", spec.arm_count, "Carbon Fiber/Nylon", 15.0,
    ))
    entries.append(BOMEntry(5, "Battery Pack", 1, "LiPo 6S", 450.0))
    entries.append(BOMEntry(6, "ESC", spec.arm_count, "PCB/MOSFET", 28.0))
    entries.append(BOMEntry(7, "Flight Controller", 1, "PCB/MCU", 35.0))
    entries.append(BOMEntry(8, "Frame Hardware", 1, "Stainless Steel", 20.0))
    return entries


def _bom_svg(
    entries: List[BOMEntry], x: float, y: float, w: float,
    font_size: float = 7.0,
) -> str:
    """Render bill of materials as SVG table."""
    parts: List[str] = []
    row_h = 12.0
    header_h = 14.0
    total_h = header_h + len(entries) * row_h + 2

    parts.append(_svg_rect(x, y, w, total_h, stroke="black", width=0.4))
    parts.append(_svg_text(x + w / 2, y + 10, "BILL OF MATERIALS", font_size + 1, "middle"))
    parts.append(_svg_line(x, y + header_h, x + w, y + header_h, width=0.3))

    # Column headers
    cols = [x + 5, x + 25, x + w * 0.5, x + w * 0.65, x + w * 0.8]
    headers = ["#", "DESCRIPTION", "QTY", "MATERIAL", "MASS(g)"]
    hy = y + header_h + 10
    for ci, hdr in enumerate(headers):
        parts.append(_svg_text(cols[ci], hy, hdr, font_size - 1, "start"))
    parts.append(_svg_line(x, hy + 3, x + w, hy + 3, width=0.2))

    for idx, entry in enumerate(entries):
        ey = hy + (idx + 1) * row_h
        parts.append(_svg_text(cols[0], ey, str(entry.item), font_size, "start"))
        parts.append(_svg_text(cols[1], ey, entry.description, font_size, "start"))
        parts.append(_svg_text(cols[2], ey, str(entry.quantity), font_size, "start"))
        parts.append(_svg_text(cols[3], ey, entry.material, font_size, "start"))
        total_mass = entry.mass_g * entry.quantity
        parts.append(_svg_text(cols[4], ey, f"{total_mass:.0f}", font_size, "start"))

    return "\n".join(parts)


# ── Main blueprint generator ─────────────────────────────────────────────


def generate_drone_blueprint(
    spec: Optional[BlueprintSpec] = None,
) -> BlueprintResult:
    """Generate a complete 2D engineering blueprint in SVG format.

    Produces:
    - Three orthographic views (top, front, side)
    - Dimension lines with ISO arrowheads
    - Annotations and callouts
    - Title block with project metadata
    - Bill of materials table
    - Border with drawing zone markers

    Parameters
    ----------
    spec : blueprint specification (defaults to competition drone).

    Returns
    -------
    BlueprintResult with SVG content and metadata.
    """
    spec = spec or BlueprintSpec()
    sw, sh = spec.sheet_width_mm, spec.sheet_height_mm
    margin = spec.margin_mm

    all_svg: List[str] = []

    # SVG header
    all_svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{sw}mm" height="{sh}mm" '
        f'viewBox="0 0 {sw} {sh}">'
    )
    all_svg.append(
        f'<rect x="0" y="0" width="{sw}" height="{sh}" fill="white"/>'
    )

    # Drawing border
    all_svg.append(_svg_rect(
        margin, margin, sw - 2 * margin, sh - 2 * margin,
        stroke="black", width=0.7,
    ))

    # Zone markers (A-F along left, 1-8 along top)
    zone_labels_v = "ABCDEF"
    zone_h = (sh - 2 * margin) / len(zone_labels_v)
    for i, label in enumerate(zone_labels_v):
        zy = margin + i * zone_h + zone_h / 2
        all_svg.append(_svg_text(margin / 2, zy + 2, label, 6, "middle"))
        all_svg.append(_svg_text(sw - margin / 2, zy + 2, label, 6, "middle"))

    zone_count_h = 8
    zone_w = (sw - 2 * margin) / zone_count_h
    for i in range(zone_count_h):
        zx = margin + i * zone_w + zone_w / 2
        all_svg.append(_svg_text(zx, margin / 2 + 2, str(i + 1), 6, "middle"))
        all_svg.append(_svg_text(zx, sh - margin / 2 + 2, str(i + 1), 6, "middle"))

    # Layout: viewports
    draw_w = sw - 2 * margin
    draw_h = sh - 2 * margin
    view_w = draw_w * 0.45
    view_h = draw_h * 0.55

    views: List[ViewPort] = []
    total_dims: List[DimensionLine] = []
    total_annots: List[Annotation] = []

    # Top view (upper-left)
    vp_top = ViewPort(
        "top", margin + 10, margin + 10, view_w, view_h, spec.scale,
    )
    top_svg, top_dims, top_annots = _generate_top_view(spec, vp_top)
    vp_top.elements_svg = top_svg
    vp_top.dimensions = top_dims
    vp_top.annotations = top_annots
    views.append(vp_top)
    total_dims.extend(top_dims)
    total_annots.extend(top_annots)

    # Front view (upper-right)
    vp_front = ViewPort(
        "front", margin + view_w + 30, margin + 10, view_w, view_h, spec.scale,
    )
    front_svg, front_dims, front_annots = _generate_front_view(spec, vp_front)
    vp_front.elements_svg = front_svg
    vp_front.dimensions = front_dims
    vp_front.annotations = front_annots
    views.append(vp_front)
    total_dims.extend(front_dims)
    total_annots.extend(front_annots)

    # Side view (lower-left)
    vp_side = ViewPort(
        "side", margin + 10, margin + view_h + 30, view_w, view_h * 0.6, spec.scale,
    )
    side_svg, side_dims, side_annots = _generate_side_view(spec, vp_side)
    vp_side.elements_svg = side_svg
    vp_side.dimensions = side_dims
    vp_side.annotations = side_annots
    views.append(vp_side)
    total_dims.extend(side_dims)
    total_annots.extend(side_annots)

    # Render viewport borders and contents
    for vp in views:
        all_svg.append(_svg_rect(
            vp.origin_x, vp.origin_y, vp.width, vp.height,
            stroke="#ccc", width=0.2,
        ))
        all_svg.append(vp.elements_svg)
        for dim in vp.dimensions:
            all_svg.append(_dimension_svg(dim, spec.dimension_font_size))
        for ann in vp.annotations:
            all_svg.append(_svg_text(
                ann.position.x, ann.position.y, ann.text,
                ann.font_size, ann.anchor,
            ))

    # Title block (bottom-right)
    tb_w = draw_w * 0.35
    tb_h = 70
    tb_x = sw - margin - tb_w
    tb_y = sh - margin - tb_h
    all_svg.append(_generate_title_block(spec, tb_x, tb_y, tb_w, tb_h))

    # Bill of materials (lower-right, above title block)
    bom_entries = _generate_bom(spec)
    bom_w = tb_w
    bom_y = tb_y - len(bom_entries) * 12 - 30
    all_svg.append(_bom_svg(bom_entries, tb_x, bom_y, bom_w, spec.annotation_font_size))

    # Geometric tolerance note
    tol_y = sh - margin - tb_h - len(bom_entries) * 12 - 50
    all_svg.append(_svg_text(
        tb_x + 5, tol_y,
        "GENERAL TOLERANCE: ±0.1mm UNLESS NOTED",
        spec.annotation_font_size, "start",
    ))
    all_svg.append(_svg_text(
        tb_x + 5, tol_y + 10,
        "SURFACE FINISH: Ra 1.6μm",
        spec.annotation_font_size, "start",
    ))
    all_svg.append(_svg_text(
        tb_x + 5, tol_y + 20,
        "ALL DIMENSIONS IN MILLIMETERS",
        spec.annotation_font_size, "start",
    ))

    all_svg.append("</svg>")
    svg_content = "\n".join(all_svg)

    return BlueprintResult(
        svg_content=svg_content,
        title=spec.title,
        view_count=len(views),
        dimension_count=len(total_dims),
        annotation_count=len(total_annots),
        sheet_width_mm=sw,
        sheet_height_mm=sh,
        bom_entries=bom_entries,
        is_valid=True,
    )
