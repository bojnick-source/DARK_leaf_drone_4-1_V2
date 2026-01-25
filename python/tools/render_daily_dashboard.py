#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from engine_ui.schema_validation import summarize_errors, validate_payload_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a static Daily Dashboard report.")
    parser.add_argument("payload", type=Path, help="Path to engine output JSON payload.")
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("schemas/engine_output.schema.json"),
        help="Path to engine output schema.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("ui/daily_dashboard_report.html"),
        help="Output HTML file path.",
    )
    return parser.parse_args()


def render_report(payload_path: Path, schema_path: Path, output_path: Path) -> None:
    result = validate_payload_file(payload_path, schema_path)
    payload = payload_path.read_text(encoding="utf-8")
    summary = "PASS" if result.is_valid else "FAIL"

    error_list = "\n".join(f"<li>{error}</li>" for error in result.errors) or "<li>No errors.</li>"

    html = f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <title>Daily Dashboard Report</title>
    <style>
      body {{ font-family: system-ui, sans-serif; margin: 24px; background: #f6f7fb; color: #18212f; }}
      .card {{ background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 12px 24px rgba(15,23,42,0.08); }}
      .status.pass {{ color: #15803d; font-weight: 700; }}
      .status.fail {{ color: #b91c1c; font-weight: 700; }}
      pre {{ background: #f4f6fa; padding: 12px; border-radius: 8px; overflow-x: auto; }}
    </style>
  </head>
  <body>
    <h1>Daily Dashboard Report</h1>
    <p class=\"status {summary.lower()}\">Validation: {summary}</p>
    <div class=\"card\">
      <h2>Validation Summary</h2>
      <p>{summarize_errors(result.errors)}</p>
      <ul>{error_list}</ul>
    </div>
    <div class=\"card\" style=\"margin-top:16px;\">
      <h2>Payload</h2>
      <pre>{payload}</pre>
    </div>
  </body>
</html>
"""

    output_path.write_text(html, encoding="utf-8")


def main() -> int:
    args = parse_args()
    render_report(args.payload, args.schema, args.output)
    print(f"Report written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
