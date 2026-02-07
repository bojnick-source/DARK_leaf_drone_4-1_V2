from __future__ import annotations

import json
import pathlib
from typing import Any


def _scatter_svg(points: list[tuple[float, float]], width: int = 400, height: int = 300) -> str:
    if not points:
        return ""
    xs, ys = zip(*points)
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    def scale(value: float, min_v: float, max_v: float, span: float) -> float:
        if max_v == min_v:
            return span / 2
        return (value - min_v) / (max_v - min_v) * span

    circles = []
    for x, y in points:
        cx = scale(x, min_x, max_x, width - 20) + 10
        cy = height - (scale(y, min_y, max_y, height - 20) + 10)
        circles.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3" fill="#1f77b4" />')
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        + "\n".join(circles)
        + "</svg>"
    )


def generate_viz(results_path: pathlib.Path, output_path: pathlib.Path) -> None:
    results: dict[str, Any] = json.loads(results_path.read_text(encoding="utf-8"))
    uq = results.get("uq", {})
    metrics = uq.get("lhs_metrics", {})
    projection = uq.get("projection", [])

    scatter = _scatter_svg([(float(p[0]), float(p[1])) for p in projection])

    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>TopOpt UQ Report</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; }}
    section {{ margin-bottom: 2rem; }}
    code {{ background: #f5f5f5; padding: 0.2rem 0.4rem; }}
  </style>
</head>
<body>
  <h1>TopOpt CI-small Report</h1>
  <section>
    <h2>UQ</h2>
    <p><strong>LHS enabled:</strong> {uq.get("lhs_enabled")}</p>
    <p><strong>Batching mode:</strong> {uq.get("batching_mode")}</p>
    <p><strong>Samples:</strong> {uq.get("n_samples")}</p>
    <p><strong>Seed:</strong> {uq.get("seed")}</p>
    <h3>Quality metrics</h3>
    <pre>{json.dumps(metrics, indent=2)}</pre>
    <h3>Sample projection</h3>
    {scatter}
    <h3>Robust objective history</h3>
    <pre>{json.dumps(uq.get("robust_history", []), indent=2)}</pre>
  </section>
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
