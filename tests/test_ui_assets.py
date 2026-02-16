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


# ---- Compute Tab tests ----


def test_dashboard_has_compute_tab() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "ui" / "dashboard.html").read_text(encoding="utf-8")

    assert 'data-tab="compute"' in html
    assert "COMPUTE" in html
    assert "computeGrid" in html
    assert 'data-tab-panel="compute"' in html


def test_dashboard_compute_tab_has_generate_button() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "ui" / "dashboard.html").read_text(encoding="utf-8")

    assert "compute-generate" in html
    assert "Generate Drone" in html


def test_dashboard_compute_tab_has_module_list() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "ui" / "dashboard.html").read_text(encoding="utf-8")

    assert "Design Loop AI" in html
    assert "Energy Maneuverability" in html
    assert "Aerospace" in html
    assert "Flight Simulation" in html
    assert "Drivetrain" in html
    assert "FEA" in html
    assert "CAD Mesh Rendering" in html


def test_dashboard_compute_tab_has_results_panel() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "ui" / "dashboard.html").read_text(encoding="utf-8")

    assert "Computation Results" in html
    assert "Energy-Maneuverability" in html
    assert "Vehicle Parameters" in html
    assert "Test Results" in html
    assert "compScore" in html
    assert "compPs" in html
    assert "compLoadFactor" in html
    assert "compTurnRate" in html


def test_dashboard_js_has_compute_tab_support() -> None:
    root = Path(__file__).resolve().parents[1]
    js = (root / "ui" / "dashboard.js").read_text(encoding="utf-8")

    assert '"compute"' in js
    assert "COMPUTE" in js
    assert "runComputeGenerate" in js
    assert "clearComputeResults" in js
    assert "DRONE_COMPONENTS" in js


def test_dashboard_js_has_design_loop_simulation() -> None:
    root = Path(__file__).resolve().parents[1]
    js = (root / "ui" / "dashboard.js").read_text(encoding="utf-8")

    assert "_simDesignLoop" in js
    assert "_renderDroneModel" in js
    assert "_updateComputeResults" in js


def test_dashboard_js_drone_components_are_labeled() -> None:
    root = Path(__file__).resolve().parents[1]
    js = (root / "ui" / "dashboard.js").read_text(encoding="utf-8")

    # Components must have meaningful names, not generic shapes
    assert "Fuselage" in js
    assert "Battery Pack" in js
    assert "Flight Controller" in js
    assert "Motor" in js
    assert "Propeller" in js
    assert "ESC" in js
    assert "GPS" in js
    assert "Landing Gear" in js
    assert "Camera Gimbal" in js
    assert "Payload Bay" in js


def test_dashboard_css_has_compute_styles() -> None:
    root = Path(__file__).resolve().parents[1]
    css = (root / "ui" / "dashboard.css").read_text(encoding="utf-8")

    assert "#computeGrid" in css
    assert ".compute-placeholder" in css
    assert ".compute-progress" in css
    assert ".progress-bar" in css
    assert ".progress-fill" in css


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


# ---- Glass System 100/100 tests ----


def test_glass_system_shader_files_present() -> None:
    root = Path(__file__).resolve().parents[1]
    shaders = root / "ui" / "shaders"

    assert (shaders / "downsample_r32f.wgsl").is_file()
    assert (shaders / "downsample_rgba16f.wgsl").is_file()
    assert (shaders / "bilateral_blur.wgsl").is_file()
    assert (shaders / "glass_composite.wgsl").is_file()


def test_downsample_r32f_shader() -> None:
    root = Path(__file__).resolve().parents[1]
    wgsl = (root / "ui" / "shaders" / "downsample_r32f.wgsl").read_text(encoding="utf-8")

    assert "@compute" in wgsl
    assert "srcTex" in wgsl
    assert "dstTex" in wgsl
    assert "r32float" in wgsl
    assert "min" in wgsl  # conservative min-of-4 downsample


def test_downsample_rgba16f_shader() -> None:
    root = Path(__file__).resolve().parents[1]
    wgsl = (root / "ui" / "shaders" / "downsample_rgba16f.wgsl").read_text(encoding="utf-8")

    assert "@compute" in wgsl
    assert "srcTex" in wgsl
    assert "dstTex" in wgsl
    assert "rgba16float" in wgsl
    assert "karisWeight" in wgsl  # Karis-average for HDR firefly suppression


def test_bilateral_blur_shader() -> None:
    root = Path(__file__).resolve().parents[1]
    wgsl = (root / "ui" / "shaders" / "bilateral_blur.wgsl").read_text(encoding="utf-8")

    assert "@compute" in wgsl
    assert "colorTex" in wgsl
    assert "depthTex" in wgsl
    assert "depthWeight" in wgsl
    assert "gaussianWeight" in wgsl
    assert "depthSigma" in wgsl  # cross-bilateral depth rejection


def test_glass_composite_shader() -> None:
    root = Path(__file__).resolve().parents[1]
    wgsl = (root / "ui" / "shaders" / "glass_composite.wgsl").read_text(encoding="utf-8")

    assert "@compute" in wgsl
    assert "beerLambert" in wgsl
    assert "oitAccum" in wgsl
    assert "oitReveal" in wgsl
    assert "absorptionColor" in wgsl
    assert "transmittance" in wgsl
    assert "fresnelPower" in wgsl

    # Enhanced absorption features
    assert "linearDepth" in wgsl
    assert "chromaticDispersion" in wgsl
    assert "chromaticAbsorption" in wgsl
    assert "minTransmittance" in wgsl
    assert "depthScale" in wgsl
    assert "effectiveThickness" in wgsl


def test_webgpu_renderer_has_glass_system() -> None:
    root = Path(__file__).resolve().parents[1]
    js = (root / "ui" / "webgpu_renderer.js").read_text(encoding="utf-8")

    # Glass toggle state
    assert "glass" in js
    assert "absorptionColor" in js
    assert "absorptionDensity" in js
    assert "oitEnabled" in js

    # Enhanced absorption parameters
    assert "chromaticDispersion" in js
    assert "minTransmittance" in js
    assert "depthScale" in js

    # Glass render targets
    assert "_rtLinearDepth" in js
    assert "_rtDepthPyramid" in js
    assert "_rtColorPyramid" in js
    assert "_rtOITAccum" in js
    assert "_rtOITReveal" in js

    # Glass pipelines
    assert "_pipeDownsampleR32F" in js
    assert "_pipeBilateralBlur" in js
    assert "_pipeGlassComposite" in js

    # Glass render passes
    assert "_glassDepthPyramid" in js
    assert "_glassColorPyramid" in js
    assert "_glassBilateralBlur" in js
    assert "_glassOITAccumulate" in js
    assert "_glassComposite" in js


def test_glass_system_css_tokens() -> None:
    root = Path(__file__).resolve().parents[1]
    css = (root / "ui" / "mesh3d_enhanced.css").read_text(encoding="utf-8")

    # Glass design tokens
    assert "--glass-blur" in css
    assert "--glass-alpha" in css
    assert "--glass-tint" in css
    assert "--glass-specular" in css
    assert "--glass-absorption-density" in css
    assert "--glass-thickness" in css
    assert "--glass-fresnel-power" in css

    # Glass panel variants
    assert ".glass-panel" in css
    assert ".glass-panel--frosted" in css
    assert ".glass-panel--clear" in css
    assert ".glass-panel--noir" in css


# ---- CAD-Tuned TAA tests ----


def test_taa_shader_files_present() -> None:
    root = Path(__file__).resolve().parents[1]
    shaders = root / "ui" / "shaders"

    assert (shaders / "motion_from_depth.wgsl").is_file()
    assert (shaders / "taa_resolve.wgsl").is_file()


def test_motion_from_depth_shader() -> None:
    root = Path(__file__).resolve().parents[1]
    wgsl = (root / "ui" / "shaders" / "motion_from_depth.wgsl").read_text(
        encoding="utf-8"
    )

    assert "@compute" in wgsl
    assert "depthTex" in wgsl
    assert "outVelocity" in wgsl
    assert "rg16float" in wgsl
    assert "invCurrVP" in wgsl
    assert "prevVP" in wgsl
    assert "velocity" in wgsl


def test_taa_resolve_shader() -> None:
    root = Path(__file__).resolve().parents[1]
    wgsl = (root / "ui" / "shaders" / "taa_resolve.wgsl").read_text(encoding="utf-8")

    assert "@compute" in wgsl
    # Inputs
    assert "currentColor" in wgsl
    assert "historyColor" in wgsl
    assert "velocityTex" in wgsl
    assert "reactiveMask" in wgsl
    assert "depthTex" in wgsl
    # Core TAA features
    assert "neighborhoodClamp" in wgsl
    assert "rgbToYCoCg" in wgsl
    assert "depthRejection" in wgsl
    assert "reactiveBoost" in wgsl
    assert "sharpenStrength" in wgsl
    assert "blendMin" in wgsl
    assert "blendMax" in wgsl


def test_webgpu_renderer_has_taa_system() -> None:
    root = Path(__file__).resolve().parents[1]
    js = (root / "ui" / "webgpu_renderer.js").read_text(encoding="utf-8")

    # TAA render targets
    assert "_rtMotionVectors" in js
    assert "_rtReactiveMask" in js
    assert "_rtTAAOutput" in js
    assert "_rtTAAHistory" in js

    # TAA pipelines
    assert "_pipeMotionVectors" in js
    assert "_pipeTAAResolve" in js

    # TAA render passes
    assert "_taaMotionVectors" in js
    assert "_taaBuildReactiveMask" in js
    assert "_taaResolve" in js

    # TAA frame state
    assert "_prevViewProj" in js
    assert "_taaFrameIndex" in js
