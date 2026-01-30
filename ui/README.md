# UI

## Daily Dashboard Shell

Open `ui/dashboard.html` to view the dashboard shell with always-visible menu and task bars. The
shell remains visible even if JavaScript or network requests fail.

For the best experience, run a local server:

```bash
cd ui
python -m http.server
```

Then open `http://localhost:8000/dashboard.html` in your browser.

## Preview-safe shell

Open `ui/dashboard_preview.html` for a single-file fallback preview that renders menu/task bars
and placeholder panels without external assets.
