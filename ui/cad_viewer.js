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
    const axisGeo = new THREE.BufferGeometry();

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

    const r = params.diameter / 2;
    const wallT = params.wallThickness;
    const len = params.length;
    const rInner = Math.max(r - wallT, MIN_INNER_RADIUS);

    // Color based on constraint status
    const bodyColor = constraintViolated ? 0xff4d6a : 0x3a4a72;
    const wireColor = constraintViolated ? 0xff2244 : 0x38f3ff;
    const emissiveColor = constraintViolated ? 0x440011 : 0x0a1428;

    // Outer cylinder (actuator body)
    const outerGeo = new THREE.CylinderGeometry(r, r, len, MESH_SEGMENTS, 1, false);
    const outerMat = new THREE.MeshStandardMaterial({
      color: bodyColor,
      metalness: 0.7,
      roughness: 0.3,
      emissive: emissiveColor,
      transparent: true,
      opacity: 0.85,
      side: THREE.DoubleSide,
    });
    const outerMesh = new THREE.Mesh(outerGeo, outerMat);
    outerMesh.castShadow = true;
    outerMesh.receiveShadow = true;
    group.add(outerMesh);

    // Wireframe
    const wireGeo = new THREE.WireframeGeometry(outerGeo);
    const wireMat = new THREE.LineBasicMaterial({
      color: wireColor,
      transparent: true,
      opacity: 0.25,
    });
    wireframeGroup.add(new THREE.LineSegments(wireGeo, wireMat));

    // Inner hollow (if wall thickness makes sense)
    if (rInner > MIN_INNER_RADIUS && rInner < r) {
      const innerGeo = new THREE.CylinderGeometry(rInner, rInner, len + 0.001, MESH_SEGMENTS, 1, true);
      const innerMat = new THREE.MeshStandardMaterial({
        color: 0x0f141d,
        metalness: 0.5,
        roughness: 0.5,
        side: THREE.BackSide,
      });
      group.add(new THREE.Mesh(innerGeo, innerMat));
    }

    // Top and bottom caps (annular rings)
    const capGeo = new THREE.RingGeometry(rInner, r, MESH_SEGMENTS);
    const capMat = new THREE.MeshStandardMaterial({
      color: bodyColor,
      metalness: 0.6,
      roughness: 0.35,
      emissive: emissiveColor,
      side: THREE.DoubleSide,
    });

    const topCap = new THREE.Mesh(capGeo, capMat);
    topCap.rotation.x = -Math.PI / 2;
    topCap.position.y = len / 2;
    group.add(topCap);

    const bottomCap = new THREE.Mesh(capGeo.clone(), capMat);
    bottomCap.rotation.x = Math.PI / 2;
    bottomCap.position.y = -len / 2;
    group.add(bottomCap);

    // Wing cross-arms
    const wingLen = params.diameter * 4;
    const wingGeo = new THREE.BoxGeometry(wingLen, 0.004, 0.008);
    const wingMat = new THREE.MeshStandardMaterial({
      color: constraintViolated ? 0xff4d6a : 0x2c3c5c,
      metalness: 0.6,
      roughness: 0.4,
      emissive: emissiveColor,
    });
    const wing1 = new THREE.Mesh(wingGeo, wingMat);
    wing1.castShadow = true;
    group.add(wing1);

    const wing2 = new THREE.Mesh(wingGeo.clone(), wingMat);
    wing2.rotation.y = Math.PI / 2;
    wing2.castShadow = true;
    group.add(wing2);

    // Rotor discs at wing tips
    const rotorRadius = r * 1.8;
    const rotorGeo = new THREE.CylinderGeometry(rotorRadius, rotorRadius, 0.003, 32);
    const rotorMat = new THREE.MeshStandardMaterial({
      color: constraintViolated ? 0xff2244 : 0x38f3ff,
      metalness: 0.3,
      roughness: 0.6,
      transparent: true,
      opacity: 0.35,
      emissive: constraintViolated ? 0x440011 : 0x0a2030,
    });

    const armLen = wingLen / 2;
    const rotorPositions = [
      [armLen, 0, 0],
      [-armLen, 0, 0],
      [0, 0, armLen],
      [0, 0, -armLen],
    ];

    for (const pos of rotorPositions) {
      const rotor = new THREE.Mesh(rotorGeo.clone(), rotorMat);
      rotor.position.set(pos[0], pos[1], pos[2]);
      rotor.castShadow = true;
      group.add(rotor);

      // Rotor hub
      const hubGeo = new THREE.CylinderGeometry(rotorRadius * 0.3, rotorRadius * 0.3, 0.006, 16);
      const hubMat = new THREE.MeshStandardMaterial({
        color: constraintViolated ? 0x881122 : 0x0a1220,
        metalness: 0.8,
        roughness: 0.2,
      });
      const hub = new THREE.Mesh(hubGeo, hubMat);
      hub.position.set(pos[0], pos[1], pos[2]);
      group.add(hub);
    }

    // Envelope wireframe (shows max bounding box)
    const envSize = params.envelope;
    const envGeo = new THREE.BoxGeometry(envSize, envSize, envSize);
    const envEdges = new THREE.EdgesGeometry(envGeo);
    const envMat = new THREE.LineBasicMaterial({
      color: constraintViolated ? 0xff4d6a : 0x7c5cff,
      transparent: true,
      opacity: 0.2,
    });
    wireframeGroup.add(new THREE.LineSegments(envEdges, envMat));

    droneMesh = group;
    scene.add(droneMesh);
    scene.add(wireframeGroup);
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
