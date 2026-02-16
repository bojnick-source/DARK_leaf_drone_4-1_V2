/* global THREE */
(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));

  let scene, camera, renderer, droneGroup, wireGroup;
  let mode = "shaded";

  function switchView(name) {
    $$(".rail-btn[data-view]").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
    $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${name}`));
    if (name !== "cad") {
      drawCharts();
    }
  }

  function initCad() {
    const canvas = $("#cadCanvas");
    if (!canvas || typeof THREE === "undefined") return;

    scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x0a0b0e, 0.45);

    camera = new THREE.PerspectiveCamera(45, 16 / 9, 0.01, 100);
    camera.position.set(1.2, 0.9, 1.2);
    camera.lookAt(0, 0.1, 0);

    renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setClearColor(0x0a0b0e, 1);

    const amb = new THREE.AmbientLight(0xffffff, 0.55);
    const key = new THREE.DirectionalLight(0xffffff, 0.9);
    key.position.set(2, 3, 2);
    const rim = new THREE.DirectionalLight(0xaab8d6, 0.4);
    rim.position.set(-1.5, 0.8, -2);
    scene.add(amb, key, rim);

    scene.add(new THREE.GridHelper(4, 80, 0x2a3346, 0x1b2230));

    droneGroup = new THREE.Group();
    wireGroup = new THREE.Group();
    scene.add(droneGroup, wireGroup);

    buildDroneModel(40);
    applyMode();
    resize();
    window.addEventListener("resize", resize);

    let dragging = false;
    let px = 0;
    let py = 0;
    canvas.addEventListener("pointerdown", (e) => { dragging = true; px = e.clientX; py = e.clientY; });
    window.addEventListener("pointerup", () => { dragging = false; });
    canvas.addEventListener("pointermove", (e) => {
      if (!dragging) return;
      droneGroup.rotation.y += (e.clientX - px) * 0.006;
      droneGroup.rotation.x += (e.clientY - py) * 0.003;
      wireGroup.rotation.copy(droneGroup.rotation);
      px = e.clientX;
      py = e.clientY;
    });

    animate();
  }

  function resize() {
    const canvas = $("#cadCanvas");
    if (!canvas || !camera || !renderer) return;
    const rect = canvas.getBoundingClientRect();
    const w = Math.max(10, Math.floor(rect.width));
    const h = Math.max(10, Math.floor(rect.height));
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
  }

  function mat(color, metalness = 0.5, roughness = 0.38) {
    return new THREE.MeshStandardMaterial({ color, metalness, roughness });
  }

  function buildDroneModel(segments) {
    droneGroup.clear();
    wireGroup.clear();

    const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.11, 0.08, segments), mat(0x7b879d, 0.62, 0.32));
    hub.castShadow = true;
    droneGroup.add(hub);

    const topDeck = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 0.025, segments), mat(0x2a303b, 0.35, 0.55));
    topDeck.position.y = 0.045;
    droneGroup.add(topDeck);

    for (let i = 0; i < 8; i++) {
      const a = (Math.PI * 2 * i) / 8;
      const screw = new THREE.Mesh(new THREE.CylinderGeometry(0.005, 0.005, 0.012, 8), mat(0xdfe6f4, 0.1, 0.6));
      screw.position.set(Math.cos(a) * 0.075, 0.056, Math.sin(a) * 0.075);
      droneGroup.add(screw);
    }

    const armDirs = [[1,1],[1,-1],[-1,1],[-1,-1]];
    armDirs.forEach(([sx, sz]) => {
      const armLen = 0.58;
      const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.014, 0.014, armLen, 24), mat(0xcfd6e4, 0.35, 0.42));
      arm.rotation.z = Math.PI / 2;
      arm.rotation.y = Math.atan2(sz, sx);
      arm.position.set((sx * armLen) / 3.3, 0.01, (sz * armLen) / 3.3);
      droneGroup.add(arm);

      const mx = sx * armLen * 0.72;
      const mz = sz * armLen * 0.72;

      const mount = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.045, 0.018, 30), mat(0x1f2532, 0.7, 0.25));
      mount.position.set(mx, 0.02, mz);
      droneGroup.add(mount);

      const rotor = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 0.004, 48), mat(0xd9e0ed, 0.05, 0.7));
      rotor.position.set(mx, 0.034, mz);
      rotor.material.transparent = true;
      rotor.material.opacity = 0.44;
      droneGroup.add(rotor);

      const ring = new THREE.Mesh(new THREE.TorusGeometry(0.16, 0.003, 12, 56), mat(0xf1f5fc, 0.15, 0.45));
      ring.rotation.x = Math.PI / 2;
      ring.position.copy(rotor.position);
      droneGroup.add(ring);

      const guard = new THREE.Mesh(new THREE.TorusGeometry(0.18, 0.006, 12, 64), mat(0x8f9bb2, 0.45, 0.4));
      guard.rotation.x = Math.PI / 2;
      guard.position.set(mx, 0.035, mz);
      droneGroup.add(guard);
    });

    const gimbal = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.035, 0.05), mat(0x202734, 0.3, 0.55));
    gimbal.position.set(0, -0.05, 0.08);
    droneGroup.add(gimbal);

    const lens = new THREE.Mesh(new THREE.SphereGeometry(0.014, 18, 18), mat(0xe4ebf8, 0.1, 0.6));
    lens.position.set(0, -0.05, 0.102);
    droneGroup.add(lens);

    droneGroup.traverse((child) => {
      if (!child.isMesh) return;
      const edges = new THREE.EdgesGeometry(child.geometry, 25);
      const lines = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0xe7edf9, transparent: true, opacity: 0.32 }));
      lines.position.copy(child.position);
      lines.rotation.copy(child.rotation);
      lines.scale.copy(child.scale);
      wireGroup.add(lines);
    });

    updateGeometryStats();
  }

  function updateGeometryStats() {
    let tris = 0;
    let verts = 0;
    droneGroup.traverse((c) => {
      if (!c.isMesh || !c.geometry) return;
      const g = c.geometry;
      const pos = g.attributes.position;
      if (pos) verts += pos.count;
      if (g.index) tris += g.index.count / 3;
      else if (pos) tris += pos.count / 3;
    });
    const triRow = $("#triRow");
    const vertRow = $("#vertRow");
    if (triRow) triRow.textContent = `Triangles: ${Math.round(tris).toLocaleString()}`;
    if (vertRow) vertRow.textContent = `Vertices: ${Math.round(verts).toLocaleString()}`;
  }

  function applyMode() {
    const modeRow = $("#modeRow");
    if (modeRow) modeRow.textContent = mode.charAt(0).toUpperCase() + mode.slice(1);
    if (!droneGroup || !wireGroup) return;

    if (mode === "wire") {
      droneGroup.visible = false;
      wireGroup.visible = true;
    } else if (mode === "xray") {
      droneGroup.visible = true;
      wireGroup.visible = true;
      droneGroup.traverse((m) => {
        if (m.isMesh && m.material) {
          m.material.transparent = true;
          m.material.opacity = 0.28;
          m.material.needsUpdate = true;
        }
      });
    } else {
      droneGroup.visible = true;
      wireGroup.visible = true;
      droneGroup.traverse((m) => {
        if (m.isMesh && m.material) {
          m.material.transparent = false;
          m.material.opacity = 1;
          m.material.needsUpdate = true;
        }
      });
    }
  }

  function drawBars(canvas, values, colorFn) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.fillStyle = "#0a0b0e";
    ctx.fillRect(0, 0, w, h);
    const bw = (w - 80) / values.length;
    values.forEach((v, i) => {
      const bh = v * (h - 70);
      ctx.fillStyle = colorFn(i);
      ctx.fillRect(40 + i * bw, h - 30 - bh, bw - 12, bh);
      ctx.fillStyle = "#c9d1d9";
      ctx.font = "12px Segoe UI";
      ctx.fillText((v * 100).toFixed(0) + "%", 40 + i * bw, h - 36 - bh);
    });
  }

  function drawCharts() {
    drawBars($("#compareCanvas"), [0.66, 0.82, 0.74, 0.89, 0.77], (i) => (i % 2 ? "rgba(232,236,245,.9)" : "rgba(146,155,172,.7)"));
    drawBars($("#coeffCanvas"), [0.12, 0.34, 0.18, 0.27, 0.09], () => "rgba(184,192,207,.8)");
    drawBars($("#simCanvas"), [0.35, 0.6, 0.82, 0.74, 0.65, 0.92, 0.58], () => "rgba(210,220,236,.74)");
  }

  function wireUi() {
    $$(".rail-btn[data-view]").forEach((b) => b.addEventListener("click", () => switchView(b.dataset.view)));

    const buttonModes = [
      ["#btnShaded", "shaded"],
      ["#btnWire", "wire"],
      ["#btnXray", "xray"],
    ];
    buttonModes.forEach(([selector, m]) => {
      const btn = $(selector);
      if (!btn) return;
      btn.addEventListener("click", () => {
        mode = m;
        $$(".action-btn").forEach((b) => b.classList.toggle("active", b === btn));
        applyMode();
      });
    });
  }

  function animate() {
    requestAnimationFrame(animate);
    if (droneGroup) {
      droneGroup.rotation.y += 0.0024;
      wireGroup.rotation.copy(droneGroup.rotation);
    }
    if (renderer && scene && camera) renderer.render(scene, camera);
  }

  document.addEventListener("DOMContentLoaded", () => {
    wireUi();
    initCad();
    drawCharts();
  });
})();
