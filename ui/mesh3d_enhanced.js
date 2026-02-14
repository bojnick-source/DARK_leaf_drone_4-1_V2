/* ui/mesh3d_enhanced.js — Mesh3D Enhanced Mode Controller
   Integrates with the Three.js CAD viewer to provide toggleable
   Clean CAD / Enhanced CAD+ rendering features:

   BASE (OFF) = "CAD Clean"
     Crisp shaded model, edge lines, optional hidden-line/ghost,
     section cuts, ground shadow, subtle AO, orthographic defaults.

   ENHANCED (ON) = "CAD+"
     Multi-layer edge system, MatCap/Studio lighting, PBR metallic
     noir materials, debug overlays, and idle-supersample hooks.

   The controller attaches to the existing Three.js scene/renderer
   and injects enhanced post-processing effects via the exposed
   window.Mesh3DEnhanced API.
*/

/* global THREE */

(function () {
  "use strict";

  // -----------------------------------------------------------------------
  // State
  // -----------------------------------------------------------------------
  let enhancedActive = false;
  let sectionPlaneEnabled = false;

  const toggles = {
    edges: { sharp: true, silhouette: true, curvature: false },
    ao: 1,           // 0=Off, 1=Low, 2=High
    taa: true,
    idleSSAA: 1.0,   // 1.0 | 1.25 | 1.5 | 2.0
    hiddenLines: "OFF",  // "OFF" | "GHOST" | "HIDDEN_LINE"
    matcap: false,
    wireframe: false,
    normals: false,
    heatmap: false,
    bvhBounds: false,
    lodLevel: false,
    debug: false,
  };

  // Lookup maps for radio → numeric conversions
  const SSAA_MAP = { "Off": 1.0, "1.25×": 1.25, "1.5×": 1.5, "2.0×": 2.0 };

  // Three.js refs (populated via attach)
  let _scene = null;
  let _camera = null;
  let _renderer = null;
  let _droneMeshGetter = null;

  // Enhanced layers
  let edgeGroup = null;
  let aoPlane = null;
  let sectionHelper = null;
  let wireframeOverlay = null;
  let normalHelper = null;
  let matcapMaterial = null;
  let heatmapOverlay = null;

  // Clipping plane for section cuts
  const clipPlane = typeof THREE !== "undefined"
    ? new THREE.Plane(new THREE.Vector3(0, -1, 0), 0.05)
    : null;

  // -----------------------------------------------------------------------
  // DOM helpers
  // -----------------------------------------------------------------------
  const $ = (sel) => document.querySelector(sel);
  const $id = (id) => document.getElementById(id);

  // -----------------------------------------------------------------------
  // Attach to Three.js scene
  // -----------------------------------------------------------------------
  function attach(scene, camera, renderer, droneMeshGetter) {
    _scene = scene;
    _camera = camera;
    _renderer = renderer;
    _droneMeshGetter = droneMeshGetter;

    buildToolbar();
    buildEnhancedBadge();
    buildDebugOverlay();
    buildSectionIndicator();
  }

  // -----------------------------------------------------------------------
  // Build Viewport Toolbar
  // -----------------------------------------------------------------------
  function buildToolbar() {
    const canvas = $id("cadCanvas");
    if (!canvas) {
      return;
    }

    const bar = document.createElement("div");
    bar.className = "viewport-toolbar";
    bar.setAttribute("role", "toolbar");
    bar.setAttribute("aria-label", "Viewport controls");

    bar.innerHTML = [
      btnHTML("Camera", "tbCamera", false, "hide-mobile"),
      btnHTML("Shading ▾", "tbShading", true, "hide-mobile"),
      btnHTML("Edges ▾", "tbEdges", true),
      btnHTML("Section", "tbSection", false),
      '<div class="toolbar-sep"></div>',
      toggleBtnHTML(),
      '<div class="toolbar-sep hide-mobile"></div>',
      btnHTML("Export", "tbExport", false, "hide-mobile"),
    ].join("");

    canvas.appendChild(bar);

    // Build dropdown panels
    buildShadingDropdown(bar);
    buildEdgesDropdown(bar);

    // Wire events
    $id("tbCamera")?.addEventListener("click", resetCamera);
    $id("tbSection")?.addEventListener("click", toggleSection);
    $id("tbExport")?.addEventListener("click", () => {
      $id("btnExportSTL")?.click();
    });

    const mesh3dBtn = $id("tbMesh3DToggle");
    if (mesh3dBtn) {
      // Filter for single click only (detail===1) to avoid double-click toggling twice
      mesh3dBtn.addEventListener("click", (e) => {
        if (e.detail === 1) {
          toggleEnhanced();
        }
      });
    }

    // Close dropdowns on outside click
    document.addEventListener("click", (e) => {
      if (!e.target.closest(".viewport-toolbar")) {
        closeAllDropdowns();
      }
    });
  }

  function btnHTML(label, id, hasDropdown, extraClass) {
    const cls = "toolbar-btn" + (extraClass ? " " + extraClass : "");
    const aria = hasDropdown ? ' aria-expanded="false" aria-haspopup="true"' : "";
    return '<button id="' + id + '" class="' + cls + '"' + aria + ' type="button">'
      + label + "</button>";
  }

  function toggleBtnHTML() {
    return '<button id="tbMesh3DToggle" class="toolbar-btn mesh3d-toggle" '
      + 'data-active="false" type="button" title="Toggle Mesh3D Enhanced Mode">'
      + '<span>Mesh3D+</span> '
      + '<span class="toggle-mode-label" id="toggleModeLabel">Clean CAD</span>'
      + "</button>";
  }

  // -----------------------------------------------------------------------
  // Shading Dropdown
  // -----------------------------------------------------------------------
  function buildShadingDropdown(bar) {
    const panel = createDropdown("shadingDropdown");
    panel.innerHTML = [
      '<div class="dropdown-heading">Hidden Lines</div>',
      radioRow("hlOff",   "OFF",         "hiddenLines", true),
      radioRow("hlGhost", "Ghost",       "hiddenLines", false),
      radioRow("hlHidden","Hidden-line",  "hiddenLines", false),
      '<div class="dropdown-heading">Shading</div>',
      switchRow("dbgMatCap", "MatCap / Studio", false),
      '<div class="dropdown-heading">Ambient Occlusion</div>',
      radioRow("aoOff",  "Off",  "ao", false),
      radioRow("aoLow",  "Low",  "ao", true),
      radioRow("aoHigh", "High", "ao", false),
      '<div class="dropdown-heading">Debug</div>',
      switchRow("dbgWire",    "Wireframe overlay", false),
      switchRow("dbgNormals", "Normals",           false),
      switchRow("dbgHeatmap", "Triangle density",  false),
      switchRow("dbgBVH",     "BVH bounds",        false),
      switchRow("dbgLOD",     "LOD level",         false),
      switchRow("dbgInfo",    "Perf info",         false),
    ].join("");

    bar.appendChild(panel);
    wireDropdownToggle("tbShading", panel);
    wireShadingEvents(panel);
  }

  function wireShadingEvents(panel) {
    // Hidden-line radios
    for (const row of panel.querySelectorAll("[data-group='hiddenLines']")) {
      row.addEventListener("click", () => {
        selectRadio(panel, "hiddenLines", row.dataset.value);
        toggles.hiddenLines = row.dataset.value;
        applyHiddenLines();
      });
    }
    // AO radios
    const aoLevelMap = { "Off": 0, "Low": 1, "High": 2 };
    for (const row of panel.querySelectorAll("[data-group='ao']")) {
      row.addEventListener("click", () => {
        selectRadio(panel, "ao", row.dataset.value);
        toggles.ao = aoLevelMap[row.dataset.value] ?? 0;
        applyAO();
      });
    }
    // MatCap toggle
    $id("dbgMatCap")?.addEventListener("click", () => {
      toggles.matcap = !toggles.matcap;
      flipSwitch($id("dbgMatCap"), toggles.matcap);
      applyMatCap();
    });
    // Debug switches
    $id("dbgWire")?.addEventListener("click", () => {
      toggles.wireframe = !toggles.wireframe;
      flipSwitch($id("dbgWire"), toggles.wireframe);
      applyWireframe();
    });
    $id("dbgNormals")?.addEventListener("click", () => {
      toggles.normals = !toggles.normals;
      flipSwitch($id("dbgNormals"), toggles.normals);
      applyNormals();
    });
    $id("dbgHeatmap")?.addEventListener("click", () => {
      toggles.heatmap = !toggles.heatmap;
      flipSwitch($id("dbgHeatmap"), toggles.heatmap);
      applyHeatmap();
    });
    $id("dbgBVH")?.addEventListener("click", () => {
      toggles.bvhBounds = !toggles.bvhBounds;
      flipSwitch($id("dbgBVH"), toggles.bvhBounds);
      applyDebugOverlay();
    });
    $id("dbgLOD")?.addEventListener("click", () => {
      toggles.lodLevel = !toggles.lodLevel;
      flipSwitch($id("dbgLOD"), toggles.lodLevel);
      applyDebugOverlay();
    });
    $id("dbgInfo")?.addEventListener("click", () => {
      toggles.debug = !toggles.debug;
      flipSwitch($id("dbgInfo"), toggles.debug);
      applyDebugOverlay();
    });
  }

  // -----------------------------------------------------------------------
  // Edges Dropdown
  // -----------------------------------------------------------------------
  function buildEdgesDropdown(bar) {
    const panel = createDropdown("edgesDropdown");
    panel.innerHTML = [
      '<div class="dropdown-heading">Edge Layers</div>',
      switchRow("edSharp",      "Sharp edges",     true),
      switchRow("edSilhouette", "Silhouette",      true),
      switchRow("edCurvature",  "Curvature lines", false),
      '<div class="dropdown-heading">TAA</div>',
      switchRow("edTAA", "Temporal AA", true),
      '<div class="dropdown-heading">Idle Supersample</div>',
      radioRow("ssOff",  "Off",   "ssaa", true),
      radioRow("ss125",  "1.25×", "ssaa", false),
      radioRow("ss150",  "1.5×",  "ssaa", false),
      radioRow("ss200",  "2.0×",  "ssaa", false),
    ].join("");

    bar.appendChild(panel);
    wireDropdownToggle("tbEdges", panel);
    wireEdgesEvents(panel);
  }

  function wireEdgesEvents(panel) {
    $id("edSharp")?.addEventListener("click", () => {
      toggles.edges.sharp = !toggles.edges.sharp;
      flipSwitch($id("edSharp"), toggles.edges.sharp);
      applyEdges();
    });
    $id("edSilhouette")?.addEventListener("click", () => {
      toggles.edges.silhouette = !toggles.edges.silhouette;
      flipSwitch($id("edSilhouette"), toggles.edges.silhouette);
      applyEdges();
    });
    $id("edCurvature")?.addEventListener("click", () => {
      toggles.edges.curvature = !toggles.edges.curvature;
      flipSwitch($id("edCurvature"), toggles.edges.curvature);
      applyEdges();
    });
    $id("edTAA")?.addEventListener("click", () => {
      toggles.taa = !toggles.taa;
      flipSwitch($id("edTAA"), toggles.taa);
    });

    // SSAA radios
    for (const row of panel.querySelectorAll("[data-group='ssaa']")) {
      row.addEventListener("click", () => {
        selectRadio(panel, "ssaa", row.dataset.value);
        toggles.idleSSAA = SSAA_MAP[row.dataset.value] || 1.0;
      });
    }
  }

  // -----------------------------------------------------------------------
  // Dropdown helpers
  // -----------------------------------------------------------------------
  function createDropdown(id) {
    const div = document.createElement("div");
    div.id = id;
    div.className = "toolbar-dropdown";
    div.setAttribute("role", "menu");
    return div;
  }

  function radioRow(id, label, group, selected) {
    const sel = selected ? ' data-selected="true"' : "";
    return '<div id="' + id + '" class="dropdown-radio-row" data-group="'
      + group + '" data-value="' + label + '"' + sel + ' role="menuitemradio">'
      + '<span class="radio-dot"></span><span>' + label + "</span></div>";
  }

  function switchRow(id, label, on) {
    const state = on ? "true" : "false";
    return '<div id="' + id + '" class="dropdown-row" role="menuitemcheckbox">'
      + "<span>" + label + '</span><span class="switch-track" data-on="'
      + state + '"></span></div>';
  }

  function wireDropdownToggle(btnId, panel) {
    const btn = $id(btnId);
    if (!btn) {
      return;
    }
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const isOpen = panel.classList.contains("open");
      closeAllDropdowns();
      if (!isOpen) {
        panel.classList.add("open");
        btn.setAttribute("aria-expanded", "true");
      }
    });
  }

  function closeAllDropdowns() {
    for (const dd of document.querySelectorAll(".toolbar-dropdown.open")) {
      dd.classList.remove("open");
    }
    for (const btn of document.querySelectorAll(".toolbar-btn[aria-expanded='true']")) {
      btn.setAttribute("aria-expanded", "false");
    }
  }

  function selectRadio(panel, group, value) {
    for (const r of panel.querySelectorAll("[data-group='" + group + "']")) {
      r.dataset.selected = String(r.dataset.value === value);
    }
  }

  function flipSwitch(row, on) {
    if (!row) {
      return;
    }
    const track = row.querySelector(".switch-track");
    if (track) {
      track.dataset.on = String(on);
    }
  }

  // -----------------------------------------------------------------------
  // Enhanced Badge + Debug Overlay + Section Indicator
  // -----------------------------------------------------------------------
  function buildEnhancedBadge() {
    const canvas = $id("cadCanvas");
    if (!canvas) {
      return;
    }
    const badge = document.createElement("div");
    badge.id = "enhancedBadge";
    badge.className = "enhanced-badge";
    badge.innerHTML = '<span class="enhanced-dot"></span><span>Enhanced CAD+</span>';
    canvas.appendChild(badge);
  }

  function buildDebugOverlay() {
    const canvas = $id("cadCanvas");
    if (!canvas) {
      return;
    }
    const overlay = document.createElement("div");
    overlay.id = "debugOverlay";
    overlay.className = "debug-overlay";
    overlay.innerHTML = [
      '<div class="debug-row"><span class="label">Mode</span><span class="value" id="dbgMode">Clean CAD</span></div>',
      '<div class="debug-row"><span class="label">Edges</span><span class="value" id="dbgEdges">—</span></div>',
      '<div class="debug-row"><span class="label">AO</span><span class="value" id="dbgAO">Low</span></div>',
      '<div class="debug-row"><span class="label">TAA</span><span class="value" id="dbgTAA">On</span></div>',
      '<div class="debug-row"><span class="label">SSAA</span><span class="value" id="dbgSSAA">1.0×</span></div>',
      '<div class="debug-row"><span class="label">Hidden</span><span class="value" id="dbgHidden">Off</span></div>',
      '<div class="debug-row"><span class="label">MatCap</span><span class="value" id="dbgMatCapVal">Off</span></div>',
      '<div class="debug-row"><span class="label">Heatmap</span><span class="value" id="dbgHeatmapVal">Off</span></div>',
      '<div class="debug-row"><span class="label">BVH</span><span class="value" id="dbgBVHVal">Off</span></div>',
      '<div class="debug-row"><span class="label">LOD</span><span class="value" id="dbgLODVal">Off</span></div>',
      '<div class="debug-row"><span class="label">WebGPU</span><span class="value" id="dbgGPU">—</span></div>',
    ].join("");
    canvas.appendChild(overlay);
  }

  function buildSectionIndicator() {
    const canvas = $id("cadCanvas");
    if (!canvas) {
      return;
    }
    const ind = document.createElement("div");
    ind.id = "sectionIndicator";
    ind.className = "section-indicator";
    ind.textContent = "✂ Section Plane Active";
    canvas.appendChild(ind);
  }

  // -----------------------------------------------------------------------
  // Toggle Enhanced Mode
  // -----------------------------------------------------------------------
  function toggleEnhanced() {
    enhancedActive = !enhancedActive;

    const btn = $id("tbMesh3DToggle");
    const label = $id("toggleModeLabel");
    const badge = $id("enhancedBadge");

    if (btn) {
      btn.dataset.active = String(enhancedActive);
    }
    if (label) {
      label.textContent = enhancedActive ? "Enhanced CAD+" : "Clean CAD";
    }
    if (badge) {
      badge.classList.toggle("visible", enhancedActive);
    }

    applyEnhancedMode();
    updateDebugInfo();
  }

  function applyEnhancedMode() {
    if (!_scene || !_renderer) {
      return;
    }

    if (enhancedActive) {
      // Enhanced: PBR metallic noir materials + MatCap-style lighting
      if (toggles.matcap) {
        applyMatCap();
      } else {
        applyNoirMaterials();
      }
      applyEdges();
      // Boost tone mapping for enhanced look
      _renderer.toneMappingExposure = 1.4;
    } else {
      // Clean CAD: restore standard materials
      restoreStandardMaterials();
      removeEdgeOverlays();
      removeMatCap();
      _renderer.toneMappingExposure = 1.2;
    }

    // Ground shadow + subtle AO available in both modes per spec
    applyAO();
    applyHiddenLines();
    applyWireframe();
    applyNormals();
    applyHeatmap();
  }

  // -----------------------------------------------------------------------
  // Material application — PBR Metallic Noir
  // -----------------------------------------------------------------------
  function applyNoirMaterials() {
    const drone = _droneMeshGetter ? _droneMeshGetter() : null;
    if (!drone || typeof THREE === "undefined") {
      return;
    }

    drone.traverse((child) => {
      if (child.isMesh && child.material) {
        // Store original for restoration (once only)
        if (!child.userData._origMaterial) {
          child.userData._origMaterial = child.material.clone();
        }
        // Restore from original before applying noir to prevent compounding
        child.material.copy(child.userData._origMaterial);
        // Apply noir metallic look
        if (child.material.isMeshStandardMaterial) {
          child.material.metalness = Math.min(child.material.metalness + 0.2, 1.0);
          child.material.roughness = Math.max(child.material.roughness - 0.1, 0.1);
          child.material.envMapIntensity = 1.5;
          child.material.needsUpdate = true;
        }
      }
    });
  }

  function restoreStandardMaterials() {
    const drone = _droneMeshGetter ? _droneMeshGetter() : null;
    if (!drone) {
      return;
    }

    drone.traverse((child) => {
      if (child.isMesh && child.userData._origMaterial) {
        child.material.copy(child.userData._origMaterial);
        child.material.needsUpdate = true;
      }
    });
  }

  // -----------------------------------------------------------------------
  // MatCap / Studio Lighting Material
  // -----------------------------------------------------------------------
  function applyMatCap() {
    if (!toggles.matcap || !_scene) {
      removeMatCap();
      return;
    }

    const drone = _droneMeshGetter ? _droneMeshGetter() : null;
    if (!drone || typeof THREE === "undefined") {
      return;
    }

    // Create a procedural matcap-style material using studio lighting colors
    if (!matcapMaterial) {
      matcapMaterial = new THREE.MeshPhongMaterial({
        color: 0x888899,
        specular: 0xffffff,
        shininess: 120,
        reflectivity: 0.9,
        emissive: 0x050508,
      });
    }

    drone.traverse((child) => {
      if (child.isMesh && child.material) {
        if (!child.userData._origMaterial) {
          child.userData._origMaterial = child.material.clone();
        }
        child.material = matcapMaterial;
        child.material.needsUpdate = true;
      }
    });
  }

  function removeMatCap() {
    // Restore original materials on all meshes when disabling MatCap
    const drone = _droneMeshGetter ? _droneMeshGetter() : null;
    if (drone) {
      drone.traverse((child) => {
        if (child.isMesh && child.userData._origMaterial) {
          child.material.copy(child.userData._origMaterial);
          child.material.needsUpdate = true;
        }
      });
    }
    matcapMaterial = null;
  }

  // -----------------------------------------------------------------------
  // Edge System — analytic sharp + silhouette edges via Three.js
  // -----------------------------------------------------------------------
  function applyEdges() {
    removeEdgeOverlays();
    if (!enhancedActive || !_scene) {
      return;
    }

    const drone = _droneMeshGetter ? _droneMeshGetter() : null;
    if (!drone || typeof THREE === "undefined") {
      return;
    }

    edgeGroup = new THREE.Group();
    edgeGroup.name = "mesh3d_edges";

    drone.traverse((child) => {
      if (!child.isMesh || !child.geometry) {
        return;
      }

      // Sharp edges — crease angle 30° for CAD-like feel
      if (toggles.edges.sharp) {
        const edgesGeo = new THREE.EdgesGeometry(child.geometry, 30);
        const edgesMat = new THREE.LineBasicMaterial({
          color: 0x00C0B8,
          transparent: true,
          opacity: 0.45,
          linewidth: 1,
        });
        const lines = new THREE.LineSegments(edgesGeo, edgesMat);
        lines.position.copy(child.position);
        lines.rotation.copy(child.rotation);
        lines.scale.copy(child.scale);
        edgeGroup.add(lines);
      }

      // Silhouette edges — wider, subtler
      if (toggles.edges.silhouette) {
        const silGeo = new THREE.EdgesGeometry(child.geometry, 1);
        const silMat = new THREE.LineBasicMaterial({
          color: 0xffffff,
          transparent: true,
          opacity: 0.12,
          linewidth: 1,
        });
        const silLines = new THREE.LineSegments(silGeo, silMat);
        silLines.position.copy(child.position);
        silLines.rotation.copy(child.rotation);
        silLines.scale.copy(child.scale);
        edgeGroup.add(silLines);
      }

      // Curvature lines — screen-space approximation via wireframe at low opacity
      if (toggles.edges.curvature) {
        const curveGeo = new THREE.WireframeGeometry(child.geometry);
        const curveMat = new THREE.LineBasicMaterial({
          color: 0x2868F8,
          transparent: true,
          opacity: 0.08,
          linewidth: 1,
        });
        const curveLines = new THREE.LineSegments(curveGeo, curveMat);
        curveLines.position.copy(child.position);
        curveLines.rotation.copy(child.rotation);
        curveLines.scale.copy(child.scale);
        edgeGroup.add(curveLines);
      }
    });

    _scene.add(edgeGroup);
  }

  function removeEdgeOverlays() {
    if (edgeGroup && _scene) {
      _scene.remove(edgeGroup);
      edgeGroup = null;
    }
  }

  // -----------------------------------------------------------------------
  // AO — Ground shadow plane (approximate AO via shadow)
  // -----------------------------------------------------------------------
  function applyAO() {
    removeAO();
    if (toggles.ao === 0 || !_scene || typeof THREE === "undefined") {
      return;
    }

    const opacity = toggles.ao === 2 ? 0.25 : 0.12;
    const geo = new THREE.PlaneGeometry(2, 2);
    const mat = new THREE.ShadowMaterial({ opacity: opacity });
    aoPlane = new THREE.Mesh(geo, mat);
    aoPlane.rotation.x = -Math.PI / 2;
    aoPlane.position.y = -0.01;
    aoPlane.receiveShadow = true;
    aoPlane.name = "mesh3d_ao";
    _scene.add(aoPlane);
  }

  function removeAO() {
    if (aoPlane && _scene) {
      _scene.remove(aoPlane);
      aoPlane = null;
    }
  }

  // -----------------------------------------------------------------------
  // Hidden Lines
  // -----------------------------------------------------------------------
  function applyHiddenLines() {
    const drone = _droneMeshGetter ? _droneMeshGetter() : null;
    if (!drone) {
      return;
    }

    drone.traverse((child) => {
      if (!child.isMesh || !child.material) {
        return;
      }

      switch (toggles.hiddenLines) {
        case "GHOST":
          child.material.transparent = true;
          child.material.opacity = 0.35;
          child.material.depthWrite = false;
          break;
        case "HIDDEN_LINE":
          child.material.transparent = true;
          child.material.opacity = 0.08;
          child.material.depthWrite = false;
          break;
        default:
          // Restore from stored original if available
          if (child.userData._origMaterial) {
            child.material.transparent = child.userData._origMaterial.transparent;
            child.material.opacity = child.userData._origMaterial.opacity;
            child.material.depthWrite = true;
          } else {
            child.material.opacity = 1.0;
            child.material.transparent = false;
            child.material.depthWrite = true;
          }
      }
      child.material.needsUpdate = true;
    });
  }

  // -----------------------------------------------------------------------
  // Wireframe overlay
  // -----------------------------------------------------------------------
  function applyWireframe() {
    removeWireframe();
    if (!toggles.wireframe || !_scene) {
      return;
    }

    const drone = _droneMeshGetter ? _droneMeshGetter() : null;
    if (!drone || typeof THREE === "undefined") {
      return;
    }

    wireframeOverlay = new THREE.Group();
    wireframeOverlay.name = "mesh3d_wireframe";

    drone.traverse((child) => {
      if (!child.isMesh || !child.geometry) {
        return;
      }
      const wfGeo = new THREE.WireframeGeometry(child.geometry);
      const wfMat = new THREE.LineBasicMaterial({
        color: 0xffffff,
        transparent: true,
        opacity: 0.15,
      });
      const wfLines = new THREE.LineSegments(wfGeo, wfMat);
      wfLines.position.copy(child.position);
      wfLines.rotation.copy(child.rotation);
      wfLines.scale.copy(child.scale);
      wireframeOverlay.add(wfLines);
    });

    _scene.add(wireframeOverlay);
  }

  function removeWireframe() {
    if (wireframeOverlay && _scene) {
      _scene.remove(wireframeOverlay);
      wireframeOverlay = null;
    }
  }

  // -----------------------------------------------------------------------
  // Normals visualization
  // -----------------------------------------------------------------------
  function applyNormals() {
    removeNormals();
    if (!toggles.normals || !_scene) {
      return;
    }

    const drone = _droneMeshGetter ? _droneMeshGetter() : null;
    if (!drone || typeof THREE === "undefined") {
      return;
    }

    // Simple normal-colored material override
    normalHelper = new THREE.Group();
    normalHelper.name = "mesh3d_normals";

    drone.traverse((child) => {
      if (!child.isMesh || !child.geometry) {
        return;
      }
      const normalMat = new THREE.MeshNormalMaterial({
        transparent: true,
        opacity: 0.6,
      });
      const clone = new THREE.Mesh(child.geometry, normalMat);
      clone.position.copy(child.position);
      clone.rotation.copy(child.rotation);
      clone.scale.copy(child.scale);
      normalHelper.add(clone);
    });

    _scene.add(normalHelper);
  }

  function removeNormals() {
    if (normalHelper && _scene) {
      _scene.remove(normalHelper);
      normalHelper = null;
    }
  }

  // -----------------------------------------------------------------------
  // Triangle Density Heatmap — colours faces by relative triangle area
  // -----------------------------------------------------------------------
  function applyHeatmap() {
    removeHeatmap();
    if (!toggles.heatmap || !_scene) {
      return;
    }

    const drone = _droneMeshGetter ? _droneMeshGetter() : null;
    if (!drone || typeof THREE === "undefined") {
      return;
    }

    heatmapOverlay = new THREE.Group();
    heatmapOverlay.name = "mesh3d_heatmap";

    drone.traverse((child) => {
      if (!child.isMesh || !child.geometry) {
        return;
      }
      // Use vertex-color material to visualise triangle density
      const geo = child.geometry.clone();
      const posAttr = geo.getAttribute("position");
      if (!posAttr) {
        return;
      }

      const count = posAttr.count;
      const colors = new Float32Array(count * 3);

      // Assign gradient based on vertex height (proxy for density in procedural geo)
      let minY = Infinity;
      let maxY = -Infinity;
      for (let i = 0; i < count; i++) {
        const y = posAttr.getY(i);
        if (y < minY) { minY = y; }
        if (y > maxY) { maxY = y; }
      }
      const rangeY = maxY - minY || 1;

      for (let i = 0; i < count; i++) {
        const t = (posAttr.getY(i) - minY) / rangeY;
        // Cool (blue) → Warm (red) heatmap
        colors[i * 3 + 0] = t;                   // R
        colors[i * 3 + 1] = 0.3 * (1.0 - Math.abs(t - 0.5) * 2.0); // G
        colors[i * 3 + 2] = 1.0 - t;             // B
      }

      geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));

      const heatMat = new THREE.MeshBasicMaterial({
        vertexColors: true,
        transparent: true,
        opacity: 0.55,
        side: THREE.DoubleSide,
        depthWrite: false,
      });
      const mesh = new THREE.Mesh(geo, heatMat);
      mesh.position.copy(child.position);
      mesh.rotation.copy(child.rotation);
      mesh.scale.copy(child.scale);
      heatmapOverlay.add(mesh);
    });

    _scene.add(heatmapOverlay);
  }

  function removeHeatmap() {
    if (heatmapOverlay && _scene) {
      _scene.remove(heatmapOverlay);
      heatmapOverlay = null;
    }
  }

  // -----------------------------------------------------------------------
  // Section Plane
  // -----------------------------------------------------------------------
  function toggleSection() {
    sectionPlaneEnabled = !sectionPlaneEnabled;
    const ind = $id("sectionIndicator");
    if (ind) {
      ind.classList.toggle("visible", sectionPlaneEnabled);
    }

    if (!_renderer || !clipPlane) {
      return;
    }

    if (sectionPlaneEnabled) {
      _renderer.clippingPlanes = [clipPlane];
      _renderer.localClippingEnabled = true;
    } else {
      _renderer.clippingPlanes = [];
    }
  }

  // -----------------------------------------------------------------------
  // Camera reset (via toolbar)
  // -----------------------------------------------------------------------
  function resetCamera() {
    $id("btnResetView")?.click();
  }

  // -----------------------------------------------------------------------
  // Debug Overlay
  // -----------------------------------------------------------------------
  function applyDebugOverlay() {
    const overlay = $id("debugOverlay");
    if (overlay) {
      overlay.classList.toggle("visible", toggles.debug);
    }
    updateDebugInfo();
  }

  function updateDebugInfo() {
    const mode = $id("dbgMode");
    const edges = $id("dbgEdges");
    const ao = $id("dbgAO");
    const taa = $id("dbgTAA");
    const ssaa = $id("dbgSSAA");
    const hidden = $id("dbgHidden");
    const matcapVal = $id("dbgMatCapVal");
    const heatmapVal = $id("dbgHeatmapVal");
    const bvhVal = $id("dbgBVHVal");
    const lodVal = $id("dbgLODVal");
    const gpu = $id("dbgGPU");

    if (mode) {
      mode.textContent = enhancedActive ? "Enhanced" : "Clean CAD";
    }
    if (edges) {
      const parts = [];
      if (toggles.edges.sharp) { parts.push("S"); }
      if (toggles.edges.silhouette) { parts.push("Si"); }
      if (toggles.edges.curvature) { parts.push("C"); }
      edges.textContent = parts.length ? parts.join("+") : "Off";
    }
    if (ao) {
      ao.textContent = ["Off", "Low", "High"][toggles.ao] || "Off";
    }
    if (taa) {
      taa.textContent = toggles.taa ? "On" : "Off";
    }
    if (ssaa) {
      ssaa.textContent = toggles.idleSSAA + "×";
    }
    if (hidden) {
      hidden.textContent = toggles.hiddenLines;
    }
    if (matcapVal) {
      matcapVal.textContent = toggles.matcap ? "On" : "Off";
    }
    if (heatmapVal) {
      heatmapVal.textContent = toggles.heatmap ? "On" : "Off";
    }
    if (bvhVal) {
      bvhVal.textContent = toggles.bvhBounds ? "On" : "Off";
    }
    if (lodVal) {
      lodVal.textContent = toggles.lodLevel ? "On" : "Off";
    }
    if (gpu) {
      gpu.textContent = (typeof navigator !== "undefined" && navigator.gpu) ? "Available" : "N/A";
    }
  }

  // -----------------------------------------------------------------------
  // Re-apply on model rebuild
  // -----------------------------------------------------------------------
  function onModelRebuilt() {
    if (enhancedActive) {
      applyEnhancedMode();
    } else {
      // Re-apply base mode features (ground shadow, debug overlays)
      applyAO();
      applyWireframe();
      applyNormals();
      applyHeatmap();
    }
  }

  // -----------------------------------------------------------------------
  // Public API
  // -----------------------------------------------------------------------
  window.Mesh3DEnhanced = {
    attach: attach,
    toggle: toggleEnhanced,
    isActive: () => enhancedActive,
    getToggles: () => ({ ...toggles }),
    onModelRebuilt: onModelRebuilt,
  };
})();
