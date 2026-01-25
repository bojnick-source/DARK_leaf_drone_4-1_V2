# Daily Dashboard UI

This UI presents a contract-driven daily dashboard for engine output JSON. It validates payloads against the shared schema and surfaces trust signals (validation state, schema version, run ID, determinism markers, missing fields).

## Requirements

* Python 3 (for the static file server or validation tooling)
* Network access if you want to load Ajv from the CDN

## Run the UI

If viewing in GitHub PR Preview: open `ui/dashboard_preview.html`.

If running locally:

```bash
python -m http.server 8000
```

Then open `http://localhost:8000/ui/dashboard.html` in your browser.

### Load data

* **Sample payload**: Click "Load sample payload" to load `ui/sample_payloads/sample_engine_output.json`.
* **Invalid payload**: Click "Load invalid payload" to see missing-field diagnostics.
* **Custom payload**: Use the file picker to load any engine output JSON file.

### Diagnostics and errors

The dashboard prints resolved schema/payload URLs plus fetch status and content-type inside the Diagnostics panel. Any fetch/parse/validation failure renders a full error panel with actionable suggestions.

## Static HTML report (no JS required)

Generate a self-contained HTML report directly from a payload:

```bash
PYTHONPATH=python python python/tools/render_daily_dashboard.py \
  ui/sample_payloads/sample_engine_output.json \
  --output ui/daily_dashboard_report.html
```

Open `ui/daily_dashboard_report.html` in a browser.

## Validation tooling

The CLI validator uses the same JSON schema.

```bash
PYTHONPATH=python python python/tools/validate_engine_output.py ui/sample_payloads/sample_engine_output.json
```

## Trust signals displayed

* Validation pass/fail
* Schema version
* Run ID
* Determinism markers
* Missing required fields
