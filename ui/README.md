# UI

## v2 Studio Dashboard

Open `ui/dashboard.html` to view the v2 Studio interface with engineering workspaces,
computational output overlays (CAD wireframe, FEA analysis, Flight AI), and AI-powered inspector
panels. The UI loads sample data on demand and renders interactive canvas visualisations.

For the best experience, run a local server:

```bash
cd ui
python -m http.server
```

Then open `http://localhost:8000/dashboard.html` in your browser.

## Legacy Preview

Open `ui/dashboard_preview.html` for a static preview of the earlier dashboard shell (menu/task
bars and placeholder panels) without external assets.
