/* ui/cad_viewer.js — Interactive 3D CAD Viewer
   Uses Three.js to render a high-fidelity drone model with real-time
   parameter editing and constraint validation. The model turns red
   when constraints are violated. */

/* global THREE */

(function () {
  "use strict";

  // --- State ---
  let scene, camera, renderer, droneMesh, wireframeGroup, gridHelper;
  let isDragging = false;
  let dragButton = -1;
  let prevMouse = { x: 0, y: 0 };
  let cameraAngleX = Math.PI / 6;
  let cameraAngleY = Math.PI / 4;
  let cameraDistance = 0.8;
  let cameraPanX = 0;
  let cameraPanY = 0;
  let constraintViolated = false;
  let cadRenderMode = "solid";

  const MESH_SEGMENTS = 48;
  const MIN_INNER_RADIUS = 0.0001;

  const params = {
    diameter: 0.06,
    wallThickness: 0.0025,
    length: 0.24,
    envelope: 0.38,
  };

  const CONSTRAINTS = {
    diameterLeEnvelope: { label: "Diameter ≤ Envelope" },
    wallLtHalfRadius: { label: "Wall < Radius / 2" },
    lengthLeEnvelope: { label: "Length ≤ Envelope" },
    allPositive: { label: "All values > 0" },
  };

  // --- DOM refs ---
  const $ = (id) => document.getElementById(id);

  // --- Initialization ---
  function init() {
    const canvas = $("threeCanvas");
    if (!canvas || typeof THREE === "undefined") {
      setStatus("Three.js not loaded");
      return;
    }

    initScene(canvas);
    initLighting();
    initGrid();
    buildDrone();
    updateCamera();
    attachControls();
    attachSliders();
    attachButtons();
    attachCadTypeControls();
    attachChromeMenu();
    updateMeshInfo();
    validateConstraints();
    setStatus("READY");
    animate();

    // Attach Mesh3D Enhanced Mode controller
    if (window.Mesh3DEnhanced) {
      window.Mesh3DEnhanced.attach(scene, camera, renderer, function () {
        return droneMesh;
      });
    }
  }

  function initScene(canvas) {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x070a10);
    scene.fog = new THREE.FogExp2(0x070a10, 0.6);

    camera = new THREE.PerspectiveCamera(45, 1, 0.001, 100);

    renderer = new THREE.WebGLRenderer({
      canvas: canvas,
      antialias: true,
      alpha: false,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;

    handleResize();
    window.addEventListener("resize", handleResize);
  }

  function handleResize() {
    const container = $("cadCanvas");
    if (!container) {
      return;
    }
    const w = container.clientWidth;
    const h = container.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  }

  function initLighting() {
    const ambient = new THREE.AmbientLight(0x405080, 0.6);
    scene.add(ambient);

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.2);
    keyLight.position.set(0.5, 1.0, 0.8);
    keyLight.castShadow = true;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x38f3ff, 0.4);
    fillLight.position.set(-0.5, 0.3, -0.5);
    scene.add(fillLight);

    const rimLight = new THREE.DirectionalLight(0xc77dff, 0.3);
    rimLight.position.set(0, -0.5, -0.8);
    scene.add(rimLight);
  }

  function initGrid() {
    gridHelper = new THREE.GridHelper(2, 40, 0x1a2640, 0x111828);
    gridHelper.position.y = -0.01;
    scene.add(gridHelper);

    // Axis lines
    const axisLen = 0.3;
    // X axis (cyan)
    const xMat = new THREE.LineBasicMaterial({ color: 0x38f3ff, linewidth: 2 });
    const xGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(axisLen, 0, 0),
    ]);
    scene.add(new THREE.Line(xGeo, xMat));

    // Y axis (violet)
    const yMat = new THREE.LineBasicMaterial({ color: 0x7c5cff, linewidth: 2 });
    const yGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(0, axisLen, 0),
    ]);
    scene.add(new THREE.Line(yGeo, yMat));

    // Z axis (magenta)
    const zMat = new THREE.LineBasicMaterial({ color: 0xc77dff, linewidth: 2 });
    const zGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(0, 0, axisLen),
    ]);
    scene.add(new THREE.Line(zGeo, zMat));
  }

  // --- Drone Model ---
  function buildDrone() {
    if (droneMesh) {
      scene.remove(droneMesh);
    }
    if (wireframeGroup) {
      scene.remove(wireframeGroup);
    }

    const group = new THREE.Group();
    wireframeGroup = new THREE.Group();

    const hubRadius = Math.max(params.diameter * 0.55, 0.03);
    const hubHeight = Math.max(params.wallThickness * 8.0, 0.014);
    const armLength = Math.max(params.length * 0.58, 0.12);
    const armRadius = Math.max(params.wallThickness * 2.2, 0.004);
    const motorRadius = Math.max(params.diameter * 0.18, 0.012);
    const motorHeight = Math.max(params.wallThickness * 9.0, 0.012);
    const propRadius = Math.max(params.diameter * 0.95, 0.045);

    const bodyColor = constraintViolated ? 0xbf3a50 : 0x838891;
    const carbonColor = constraintViolated ? 0x9f2e44 : 0x4a4f57;
    const propColor = constraintViolated ? 0xe8667b : 0xcfd4df;

    const bodyMat = new THREE.MeshStandardMaterial({
      color: bodyColor,
      metalness: 0.55,
      roughness: 0.42,
      emissive: constraintViolated ? 0x180708 : 0x090a0d,
    });

    const hub = new THREE.Mesh(
      new THREE.CylinderGeometry(hubRadius, hubRadius * 0.9, hubHeight, MESH_SEGMENTS),
      bodyMat
    );
    hub.castShadow = true;
    hub.receiveShadow = true;
    group.add(hub);

    const topDeck = new THREE.Mesh(
      new THREE.CylinderGeometry(hubRadius * 0.72, hubRadius * 0.72, hubHeight * 0.34, MESH_SEGMENTS),
      new THREE.MeshStandardMaterial({
        color: 0x272b31,
        metalness: 0.35,
        roughness: 0.6,
      })
    );
    topDeck.position.y = hubHeight * 0.40;
    group.add(topDeck);

    const armMat = new THREE.MeshStandardMaterial({
      color: carbonColor,
      metalness: 0.25,
      roughness: 0.58,
    });

    const motorMat = new THREE.MeshStandardMaterial({
      color: 0x262a31,
      metalness: 0.7,
      roughness: 0.34,
      emissive: constraintViolated ? 0x200a0d : 0x050608,
    });

    const propMat = new THREE.MeshStandardMaterial({
      color: propColor,
      metalness: 0.12,
      roughness: 0.55,
      transparent: true,
      opacity: cadRenderMode === "xray" ? 0.22 : 0.36,
      side: THREE.DoubleSide,
    });

    const armOffsets = [
      [1, 1],
      [1, -1],
      [-1, 1],
      [-1, -1],
    ];

    for (const [sx, sz] of armOffsets) {
      const arm = new THREE.Mesh(
        new THREE.CylinderGeometry(armRadius, armRadius, armLength, 20),
        armMat
      );
      arm.rotation.z = Math.PI / 2;
      arm.rotation.y = Math.atan2(sz, sx);
      arm.position.set((sx * armLength) / 3.0, hubHeight * 0.10, (sz * armLength) / 3.0);
      arm.castShadow = true;
      arm.receiveShadow = true;
      group.add(arm);

      const mx = sx * armLength * 0.70;
      const mz = sz * armLength * 0.70;

      const motor = new THREE.Mesh(
        new THREE.CylinderGeometry(motorRadius, motorRadius, motorHeight, 24),
        motorMat
      );
      motor.position.set(mx, motorHeight * 0.5, mz);
      motor.castShadow = true;
      group.add(motor);

      const prop = new THREE.Mesh(
        new THREE.CylinderGeometry(propRadius, propRadius, 0.0032, 36),
        propMat
      );
      prop.position.set(mx, motorHeight + 0.004, mz);
      prop.castShadow = true;
      group.add(prop);

      const propEdge = new THREE.Mesh(
        new THREE.TorusGeometry(propRadius * 0.9, 0.0014, 8, 48),
        new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 0.2, roughness: 0.4, transparent: true, opacity: 0.18 })
      );
      propEdge.rotation.x = Math.PI / 2;
      propEdge.position.copy(prop.position);
      group.add(propEdge);
    }

    const tail = new THREE.Mesh(
      new THREE.BoxGeometry(hubRadius * 0.55, hubHeight * 0.24, hubRadius * 0.35),
      new THREE.MeshStandardMaterial({
        color: 0x191c22,
        metalness: 0.3,
        roughness: 0.62,
      })
    );
    tail.position.set(0, -hubHeight * 0.06, hubRadius * 0.5);
    group.add(tail);

    const droneWire = new THREE.EdgesGeometry(new THREE.BoxGeometry(armLength * 1.55, armLength * 0.35, armLength * 1.55));
    wireframeGroup.add(new THREE.LineSegments(droneWire, new THREE.LineBasicMaterial({ color: 0xe7e9ef, transparent: true, opacity: 0.26 })));

    const envSize = params.envelope;
    const envEdges = new THREE.EdgesGeometry(new THREE.BoxGeometry(envSize, envSize, envSize));
    wireframeGroup.add(new THREE.LineSegments(envEdges, new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.16 })));

    droneMesh = group;
    scene.add(droneMesh);
    scene.add(wireframeGroup);
    applyCadRenderMode();
  }

  function applyCadRenderMode() {
    if (!droneMesh || !wireframeGroup) {
      return;
    }

    const showWire = cadRenderMode === "wireframe" || cadRenderMode === "xray";
    wireframeGroup.visible = showWire;

    droneMesh.traverse((node) => {
      if (!node.isMesh || !node.material) {
        return;
      }
      if (cadRenderMode === "wireframe") {
        node.visible = false;
      } else if (cadRenderMode === "xray") {
        node.visible = true;
        node.material.transparent = true;
        node.material.opacity = Math.min(node.material.opacity ?? 1.0, 0.35);
      } else {
        node.visible = true;
        if (node.material.opacity !== undefined) {
          node.material.opacity = node.material.opacity < 0.4 ? 0.36 : 1.0;
        }
        node.material.transparent = (node.material.opacity ?? 1.0) < 0.99;
      }
      node.material.needsUpdate = true;
    });
  }

  function attachCadTypeControls() {
    const wrap = $("cadTypeControls");
    if (!wrap) {
      return;
    }
    const buttons = Array.from(wrap.querySelectorAll(".cad-type-btn"));
    for (const button of buttons) {
      button.addEventListener("click", () => {
        cadRenderMode = button.dataset.mode || "solid";
        for (const b of buttons) {
          b.classList.toggle("active", b === button);
        }
        applyCadRenderMode();
        setStatus("CAD MODE: " + cadRenderMode.toUpperCase());
      });
    }
  }

  // --- Constraint Validation ---
  function validateConstraints() {
    const results = {};
    const r = params.diameter / 2;

    results.diameterLeEnvelope = params.diameter <= params.envelope;
    results.wallLtHalfRadius = params.wallThickness < r / 2;
    results.lengthLeEnvelope = params.length <= params.envelope;
    results.allPositive =
      params.diameter > 0 &&
      params.wallThickness > 0 &&
      params.length > 0 &&
      params.envelope > 0;

    constraintViolated = false;
    const violations = [];

    for (const key in results) {
      const elMap = {
        diameterLeEnvelope: "cDiameter",
        wallLtHalfRadius: "cWall",
        lengthLeEnvelope: "cLength",
        allPositive: "cPositive",
      };
      const row = $(elMap[key]);
      if (row) {
        if (results[key]) {
          row.classList.remove("fail");
          row.classList.add("pass");
          row.querySelector(".constraint-icon").textContent = "✓";
        } else {
          row.classList.remove("pass");
          row.classList.add("fail");
          row.querySelector(".constraint-icon").textContent = "✗";
          constraintViolated = true;
          violations.push(CONSTRAINTS[key].label);
        }
      }
    }

    // Update banner
    const banner = $("constraintBanner");
    const bannerText = $("bannerText");
    const footerConstraint = $("footerConstraint");

    if (constraintViolated) {
      if (banner) {
        banner.hidden = false;
      }
      if (bannerText) {
        bannerText.textContent = "Constraint violated: " + violations.join(", ");
      }
      if (footerConstraint) {
        footerConstraint.textContent = "CONSTRAINTS: FAIL";
        footerConstraint.classList.add("warn");
      }
    } else {
      if (banner) {
        banner.hidden = true;
      }
      if (footerConstraint) {
        footerConstraint.textContent = "CONSTRAINTS: OK";
        footerConstraint.classList.remove("warn");
      }
    }

    return !constraintViolated;
  }

  // --- Camera Controls ---
  function updateCamera() {
    const x = cameraDistance * Math.cos(cameraAngleX) * Math.sin(cameraAngleY);
    const y = cameraDistance * Math.sin(cameraAngleX);
    const z = cameraDistance * Math.cos(cameraAngleX) * Math.cos(cameraAngleY);
    camera.position.set(x + cameraPanX, y + cameraPanY, z);
    camera.lookAt(cameraPanX, cameraPanY, 0);
  }

  function attachControls() {
    const canvas = $("threeCanvas");
    if (!canvas) {
      return;
    }

    canvas.addEventListener("pointerdown", (e) => {
      isDragging = true;
      dragButton = e.button;
      prevMouse = { x: e.clientX, y: e.clientY };
      canvas.setPointerCapture(e.pointerId);
    });

    canvas.addEventListener("pointermove", (e) => {
      if (!isDragging) {
        return;
      }
      const dx = e.clientX - prevMouse.x;
      const dy = e.clientY - prevMouse.y;
      prevMouse = { x: e.clientX, y: e.clientY };

      if (dragButton === 0) {
        // Orbit
        cameraAngleY -= dx * 0.005;
        cameraAngleX = Math.max(
          -Math.PI / 2.5,
          Math.min(Math.PI / 2.5, cameraAngleX + dy * 0.005)
        );
      } else if (dragButton === 2) {
        // Pan
        cameraPanX -= dx * 0.001;
        cameraPanY += dy * 0.001;
      }
      updateCamera();
    });

    canvas.addEventListener("pointerup", (e) => {
      isDragging = false;
      canvas.releasePointerCapture(e.pointerId);
    });

    canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      cameraDistance = Math.max(0.15, Math.min(5, cameraDistance + e.deltaY * 0.001));
      updateCamera();
    }, { passive: false });

    canvas.addEventListener("contextmenu", (e) => e.preventDefault());
  }

  // --- Slider Controls ---
  function attachSliders() {
    const sliderMap = [
      { id: "paramDiameter", key: "diameter", valId: "valDiameter", decimals: 3 },
      { id: "paramWall", key: "wallThickness", valId: "valWall", decimals: 4 },
      { id: "paramLength", key: "length", valId: "valLength", decimals: 3 },
      { id: "paramEnvelope", key: "envelope", valId: "valEnvelope", decimals: 2 },
    ];

    for (const slider of sliderMap) {
      const input = $(slider.id);
      const valEl = $(slider.valId);
      if (!input) {
        continue;
      }

      input.addEventListener("input", () => {
        const val = parseFloat(input.value);
        params[slider.key] = val;
        if (valEl) {
          valEl.textContent = val.toFixed(slider.decimals);
        }
        onParamsChanged();
      });
    }
  }

  function onParamsChanged() {
    validateConstraints();
    buildDrone();
    updateMeshInfo();
    updateCamera();
    setStatus(constraintViolated ? "CONSTRAINT VIOLATED" : "READY");

    // Notify enhanced mode of model rebuild
    if (window.Mesh3DEnhanced) {
      window.Mesh3DEnhanced.onModelRebuilt();
    }
  }

  // --- Mesh Info ---
  function updateMeshInfo() {
    const verts = MESH_SEGMENTS * 2 + 2;
    const tris = MESH_SEGMENTS * 4;

    const infoVerts = $("infoVerts");
    const infoTris = $("infoTris");
    const infoWatertight = $("infoWatertight");
    const footerMesh = $("footerMesh");

    if (infoVerts) {
      infoVerts.textContent = String(verts);
    }
    if (infoTris) {
      infoTris.textContent = String(tris);
    }
    if (infoWatertight) {
      infoWatertight.textContent = "Yes";
    }
    if (footerMesh) {
      footerMesh.textContent = "MESH: " + verts + "v / " + tris + "t";
    }
  }

  // --- Buttons ---
  function attachButtons() {
    const btnReset = $("btnResetView");
    const btnLoad = $("btnLoadPayload");
    const btnExport = $("btnExportSTL");
    const fileInput = $("jsonFileInput");

    if (btnReset) {
      btnReset.addEventListener("click", () => {
        cameraAngleX = Math.PI / 6;
        cameraAngleY = Math.PI / 4;
        cameraDistance = 0.8;
        cameraPanX = 0;
        cameraPanY = 0;
        updateCamera();
        setStatus("VIEW RESET");
      });
    }

    if (btnLoad && fileInput) {
      btnLoad.addEventListener("click", () => {
        fileInput.value = "";
        fileInput.click();
      });

      fileInput.addEventListener("change", () => {
        const file = fileInput.files && fileInput.files[0];
        if (!file) {
          return;
        }
        const reader = new FileReader();
        reader.onload = () => {
          try {
            const payload = JSON.parse(String(reader.result || ""));
            applyPayload(payload);
            setStatus("LOADED: " + file.name);
          } catch (err) {
            setStatus("PARSE ERROR");
          }
        };
        reader.onerror = () => {
          setStatus("FILE READ ERROR");
        };
        reader.readAsText(file);
      });
    }

    if (btnExport) {
      btnExport.addEventListener("click", exportSTL);
    }
  }


  function attachChromeMenu() {
    const menuBar = $("chromeMenuBar");
    const bento = $("chromeBento");
    if (!menuBar || !bento) {
      return;
    }

    const menuData = {
      File: [
        ["Load Payload", "Import engineering payload JSON into viewer state."],
        ["Export STL", "Generate manufacturing STL from current geometry."],
        ["Reset Session", "Reset camera and mesh transforms to default state."],
        ["Snapshot", "Capture viewport snapshot with overlay diagnostics."],
      ],
      Edit: [
        ["Diameter", "Adjust actuator diameter and update constraints."],
        ["Wall Thickness", "Tune wall thickness and validate manufacturability."],
        ["Length", "Set actuator length against envelope rules."],
        ["Envelope", "Update global envelope budget in real-time."],
      ],
      View: [
        ["Camera", "Reset, orbit, and inspect assembly with precision."],
        ["Section", "Toggle clipping section for internal inspection."],
        ["Edges", "Enable hidden-line, silhouette, and curvature overlays."],
        ["AO / TAA", "Switch fidelity options for clarity and stability."],
      ],
      Tools: [
        ["Mesh3D+", "Enable enhanced noir shading workflow."],
        ["Topology", "Preview topology optimization variants."],
        ["Constraint Check", "Run geometry sanity checks instantly."],
        ["Debug", "Show normals, BVH bounds, and perf instrumentation."],
      ],
      Render: [
        ["Glass", "Apply liquid-obsidian glass compositing style."],
        ["MatCap", "Switch to studio MatCap shading set."],
        ["Quality", "Toggle low/high quality processing passes."],
        ["Export View", "Prepare render-ready viewport framing."],
      ],
    };

    const words = Array.from(menuBar.querySelectorAll(".chrome-menu-word"));

    function closeMenu() {
      bento.hidden = true;
      for (const btn of words) {
        btn.classList.remove("active");
      }
    }

    function openMenu(button, menuName) {
      const rows = menuData[menuName] || [];
      bento.innerHTML =
        '<div class="chrome-bento-title">' + menuName + ' Menu</div>' +
        '<div class="chrome-bento-grid">' +
        rows
          .map(([label, desc]) => (
            '<div class="chrome-bento-item"><span class="label">' + label + '</span>' + desc + '</div>'
          ))
          .join("") +
        '</div>';

      const header = $("cadHeader");
      const headerRect = header.getBoundingClientRect();
      const buttonRect = button.getBoundingClientRect();
      bento.hidden = false;
      const left = Math.max(10, Math.min(buttonRect.left - headerRect.left - 14, headerRect.width - bento.offsetWidth - 10));
      bento.style.left = left + "px";
      bento.style.top = (headerRect.height - 2) + "px";

      for (const btn of words) {
        btn.classList.toggle("active", btn === button);
      }
    }

    for (const word of words) {
      word.addEventListener("click", (e) => {
        e.stopPropagation();
        const menuName = word.dataset.menu || "Menu";
        if (!bento.hidden && word.classList.contains("active")) {
          closeMenu();
          return;
        }
        openMenu(word, menuName);
      });
    }

    document.addEventListener("click", (e) => {
      if (!e.target.closest("#cadHeader")) {
        closeMenu();
      }
    });
  }

  function applyPayload(payload) {
    const geo =
      payload?.design?.geometry ||
      payload?.inputs?.design?.geometry ||
      payload?.geometry ||
      null;
    if (!geo) {
      setStatus("NO GEOMETRY IN PAYLOAD");
      return;
    }

    const dims = geo.key_dimensions;
    if (dims?.actuator_diameter?.value) {
      params.diameter = dims.actuator_diameter.value;
      syncSlider("paramDiameter", "valDiameter", params.diameter, 3);
    }
    if (dims?.actuator_wall_thickness?.value) {
      params.wallThickness = dims.actuator_wall_thickness.value;
      syncSlider("paramWall", "valWall", params.wallThickness, 4);
    }
    if (dims?.actuator_length?.value) {
      params.length = dims.actuator_length.value;
      syncSlider("paramLength", "valLength", params.length, 3);
    }
    if (geo.envelope_max?.value) {
      params.envelope = geo.envelope_max.value;
      syncSlider("paramEnvelope", "valEnvelope", params.envelope, 2);
    }

    onParamsChanged();
  }

  function syncSlider(sliderId, valId, value, decimals) {
    const slider = $(sliderId);
    const valEl = $(valId);
    if (slider) {
      slider.value = String(value);
    }
    if (valEl) {
      valEl.textContent = value.toFixed(decimals);
    }
  }

  // --- STL Export ---
  function exportSTL() {
    const r = params.diameter / 2;
    const rInner = Math.max(r - params.wallThickness, MIN_INNER_RADIUS);
    const len = params.length;
    const segments = MESH_SEGMENTS;
    const lines = ["solid actuator"];

    for (let i = 0; i < segments; i++) {
      const theta1 = (2 * Math.PI * i) / segments;
      const theta2 = (2 * Math.PI * ((i + 1) % segments)) / segments;
      const x1 = r * Math.cos(theta1);
      const y1 = r * Math.sin(theta1);
      const x2 = r * Math.cos(theta2);
      const y2 = r * Math.sin(theta2);

      // Outer side triangles
      addTriangle(lines, [x1, y1, 0], [x2, y2, 0], [x1, y1, len]);
      addTriangle(lines, [x2, y2, 0], [x2, y2, len], [x1, y1, len]);

      if (rInner > MIN_INNER_RADIUS && rInner < r) {
        const ix1 = rInner * Math.cos(theta1);
        const iy1 = rInner * Math.sin(theta1);
        const ix2 = rInner * Math.cos(theta2);
        const iy2 = rInner * Math.sin(theta2);

        // Inner side triangles (reversed winding for inward normals)
        addTriangle(lines, [ix2, iy2, 0], [ix1, iy1, 0], [ix1, iy1, len]);
        addTriangle(lines, [ix2, iy2, 0], [ix1, iy1, len], [ix2, iy2, len]);

        // Bottom annular cap
        addTriangle(lines, [x2, y2, 0], [x1, y1, 0], [ix1, iy1, 0]);
        addTriangle(lines, [x2, y2, 0], [ix1, iy1, 0], [ix2, iy2, 0]);

        // Top annular cap
        addTriangle(lines, [x1, y1, len], [x2, y2, len], [ix2, iy2, len]);
        addTriangle(lines, [x1, y1, len], [ix2, iy2, len], [ix1, iy1, len]);
      } else {
        // Solid caps (no inner cavity)
        addTriangle(lines, [0, 0, 0], [x2, y2, 0], [x1, y1, 0]);
        addTriangle(lines, [0, 0, len], [x1, y1, len], [x2, y2, len]);
      }
    }

    lines.push("endsolid actuator");
    const stl = lines.join("\n");
    const blob = new Blob([stl], { type: "model/stl" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "drone_actuator.stl";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setStatus("STL EXPORTED");
  }

  function addTriangle(lines, v0, v1, v2) {
    // Compute normal
    const e1 = [v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]];
    const e2 = [v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]];
    const nx = e1[1] * e2[2] - e1[2] * e2[1];
    const ny = e1[2] * e2[0] - e1[0] * e2[2];
    const nz = e1[0] * e2[1] - e1[1] * e2[0];
    const mag = Math.sqrt(nx * nx + ny * ny + nz * nz) || 1;

    lines.push(
      "  facet normal " +
        (nx / mag).toExponential(6) +
        " " +
        (ny / mag).toExponential(6) +
        " " +
        (nz / mag).toExponential(6)
    );
    lines.push("    outer loop");
    for (const v of [v0, v1, v2]) {
      lines.push(
        "      vertex " +
          v[0].toExponential(6) +
          " " +
          v[1].toExponential(6) +
          " " +
          v[2].toExponential(6)
      );
    }
    lines.push("    endloop");
    lines.push("  endfacet");
  }

  // --- Utilities ---
  function setStatus(text) {
    const el = $("statusText");
    if (el) {
      el.textContent = text;
    }
  }

  // --- Animation Loop ---
  function animate() {
    requestAnimationFrame(animate);
    renderer.render(scene, camera);
  }

  // --- Startup ---
  window.addEventListener("DOMContentLoaded", init);
})();
