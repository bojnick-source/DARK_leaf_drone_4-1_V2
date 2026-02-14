from pathlib import Path


def test_ui_assets_present() -> None:
    root = Path(__file__).resolve().parents[1]
    ui_dir = root / "ui"

    # Assert only on UI assets that are guaranteed to be committed to the repo.
    # Additional build-generated or optional assets should be validated by
    # build-specific tests rather than hardcoded here.
    assert ui_dir.is_dir()
    assert (ui_dir / "README.md").is_file()
    assert (ui_dir / ".gitignore").is_file()


def test_cad_viewer_assets_present() -> None:
    root = Path(__file__).resolve().parents[1]
    ui_dir = root / "ui"

    assert (ui_dir / "cad_viewer.html").is_file()
    assert (ui_dir / "cad_viewer.js").is_file()
    assert (ui_dir / "cad_viewer.css").is_file()


def test_cad_viewer_html_has_three_js_import() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "ui" / "cad_viewer.html").read_text(encoding="utf-8")

    assert "three" in html.lower()
    assert "cad_viewer.js" in html
    assert "cad_viewer.css" in html


def test_cad_viewer_js_has_constraint_validation() -> None:
    root = Path(__file__).resolve().parents[1]
    js = (root / "ui" / "cad_viewer.js").read_text(encoding="utf-8")

    assert "validateConstraints" in js
    assert "constraintViolated" in js
    assert "0xff4d6a" in js or "ff4d6a" in js  # red color for constraint violation


def test_cad_viewer_js_has_interactive_controls() -> None:
    root = Path(__file__).resolve().parents[1]
    js = (root / "ui" / "cad_viewer.js").read_text(encoding="utf-8")

    assert "attachSliders" in js
    assert "onParamsChanged" in js
    assert "exportSTL" in js
    assert "applyPayload" in js


def test_dashboard_links_to_cad_viewer() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "ui" / "dashboard.html").read_text(encoding="utf-8")

    assert "cad_viewer.html" in html


# ---- Mesh3D Enhanced Mode tests ----


def test_mesh3d_enhanced_assets_present() -> None:
    root = Path(__file__).resolve().parents[1]
    ui_dir = root / "ui"

    assert (ui_dir / "mesh3d_enhanced.js").is_file()
    assert (ui_dir / "mesh3d_enhanced.css").is_file()
    assert (ui_dir / "webgpu_renderer.js").is_file()
    assert (ui_dir / "shaders" / "edges_screen.wgsl").is_file()


def test_mesh3d_enhanced_html_integration() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "ui" / "cad_viewer.html").read_text(encoding="utf-8")

    assert "mesh3d_enhanced.js" in html
    assert "mesh3d_enhanced.css" in html
    assert "webgpu_renderer.js" in html


def test_mesh3d_enhanced_js_has_toggle_system() -> None:
    root = Path(__file__).resolve().parents[1]
    js = (root / "ui" / "mesh3d_enhanced.js").read_text(encoding="utf-8")

    # Core toggle state
    assert "enhancedActive" in js
    assert "toggleEnhanced" in js
    assert "CLEAN_CAD" in js or "Clean CAD" in js
    assert "Enhanced CAD+" in js

    # Sub-toggles from spec
    assert "edges" in js
    assert "sharp" in js
    assert "silhouette" in js
    assert "curvature" in js
    assert "taa" in js
    assert "idleSSAA" in js
    assert "hiddenLines" in js


def test_mesh3d_enhanced_js_has_debug_toggles() -> None:
    root = Path(__file__).resolve().parents[1]
    js = (root / "ui" / "mesh3d_enhanced.js").read_text(encoding="utf-8")

    # Debug overlays: normals, wireframe, triangle density, BVH, LOD
    assert "wireframe" in js
    assert "normals" in js
    assert "heatmap" in js
    assert "bvhBounds" in js
    assert "lodLevel" in js


def test_mesh3d_enhanced_js_has_matcap_toggle() -> None:
    root = Path(__file__).resolve().parents[1]
    js = (root / "ui" / "mesh3d_enhanced.js").read_text(encoding="utf-8")

    assert "matcap" in js
    assert "applyMatCap" in js
    assert "MatCap" in js


def test_mesh3d_enhanced_js_has_edge_system() -> None:
    root = Path(__file__).resolve().parents[1]
    js = (root / "ui" / "mesh3d_enhanced.js").read_text(encoding="utf-8")

    assert "applyEdges" in js
    assert "EdgesGeometry" in js
    assert "WireframeGeometry" in js


def test_mesh3d_enhanced_js_has_ao_system() -> None:
    root = Path(__file__).resolve().parents[1]
    js = (root / "ui" / "mesh3d_enhanced.js").read_text(encoding="utf-8")

    assert "applyAO" in js
    assert "ShadowMaterial" in js


def test_mesh3d_enhanced_js_has_section_plane() -> None:
    root = Path(__file__).resolve().parents[1]
    js = (root / "ui" / "mesh3d_enhanced.js").read_text(encoding="utf-8")

    assert "toggleSection" in js
    assert "sectionPlaneEnabled" in js
    assert "clippingPlanes" in js


def test_mesh3d_enhanced_css_has_liquid_obsidian_palette() -> None:
    root = Path(__file__).resolve().parents[1]
    css = (root / "ui" / "mesh3d_enhanced.css").read_text(encoding="utf-8")

    # Noir backgrounds
    assert "#0A0B0E" in css
    assert "#0E1118" in css
    assert "#131827" in css

    # Ink accents
    assert "#00C0B8" in css or "--ink-teal" in css
    assert "#0088D8" in css or "--ink-blue" in css
    assert "#2868F8" in css or "--ink-indigo" in css


def test_mesh3d_enhanced_css_has_toolbar_styles() -> None:
    root = Path(__file__).resolve().parents[1]
    css = (root / "ui" / "mesh3d_enhanced.css").read_text(encoding="utf-8")

    assert ".viewport-toolbar" in css
    assert ".toolbar-btn" in css
    assert ".mesh3d-toggle" in css
    assert ".toolbar-dropdown" in css


def test_webgpu_renderer_has_render_graph() -> None:
    root = Path(__file__).resolve().parents[1]
    js = (root / "ui" / "webgpu_renderer.js").read_text(encoding="utf-8")

    assert "RenderGraph" in js
    assert "CADViewportRenderer" in js
    assert "CLEAN_CAD" in js
    assert "ENHANCED_CAD_PLUS" in js


def test_webgpu_renderer_has_render_passes() -> None:
    root = Path(__file__).resolve().parents[1]
    js = (root / "ui" / "webgpu_renderer.js").read_text(encoding="utf-8")

    # All passes from the render graph spec
    assert "_depthPrepass" in js
    assert "_gbufferPass" in js
    assert "_ssao" in js
    assert "_shade" in js
    assert "_edgesScreenSpace" in js
    assert "_edgesAnalytic" in js
    assert "_taaResolve" in js
    assert "_composite" in js
    assert "_selectionOutline" in js


def test_webgpu_renderer_has_dynamic_resolution() -> None:
    root = Path(__file__).resolve().parents[1]
    js = (root / "ui" / "webgpu_renderer.js").read_text(encoding="utf-8")

    assert "dynamicResolution" in js
    assert "idleSSAA" in js
    assert "_getRenderScale" in js


def test_edges_screen_wgsl_shader() -> None:
    root = Path(__file__).resolve().parents[1]
    wgsl = (root / "ui" / "shaders" / "edges_screen.wgsl").read_text(encoding="utf-8")

    assert "depthTex" in wgsl
    assert "normalTex" in wgsl
    assert "outEdges" in wgsl
    assert "@compute" in wgsl
    assert "linearizeDepth" in wgsl
