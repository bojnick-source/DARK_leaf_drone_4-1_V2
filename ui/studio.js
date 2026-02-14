const statusBadge = document.getElementById("statusBadge");
const btnLoadSample = document.getElementById("btnLoadSample");
const btnExport = document.getElementById("btnExport");
const railCount = document.getElementById("railCount");
const photonicLinks = document.getElementById("photonicLinks");
const thermalNodes = document.getElementById("thermalNodes");
const aiBest = document.getElementById("aiBest");
const aiScore = document.getElementById("aiScore");
const aiModel = document.getElementById("aiModel");
const aiConfidence = document.getElementById("aiConfidence");
const aiStatus = document.getElementById("aiStatus");
const processorLabel = document.getElementById("processorLabel");
const busVoltage = document.getElementById("busVoltage");
const thermalMargin = document.getElementById("thermalMargin");
const aiRecommendation = document.getElementById("aiRecommendation");
const electroThermal = document.getElementById("electroThermal");
const flightAlt = document.getElementById("flightAlt");
const flightSpeed = document.getElementById("flightSpeed");
const flightMode = document.getElementById("flightMode");
const shipEfficiency = document.getElementById("shipEfficiency");
const kitePower = document.getElementById("kitePower");
const grossMargin = document.getElementById("grossMargin");
const shippingCost = document.getElementById("shippingCost");
const clock = document.getElementById("clock");
const flightCanvas = document.getElementById("flightCanvas");
const thermalCanvas = document.getElementById("thermalCanvas");
const windCanvas = document.getElementById("windCanvas");
const salesCanvas = document.getElementById("salesCanvas");
const cadCanvas = document.getElementById("cadCanvas");
const feaCanvas = document.getElementById("feaCanvas");
const feaDispCanvas = document.getElementById("feaDispCanvas");
const barAI = document.getElementById("barAI");
const barFlight = document.getElementById("barFlight");
const barThermal = document.getElementById("barThermal");
const barWind = document.getElementById("barWind");
const barMesh = document.getElementById("barMesh");
const barFEA = document.getElementById("barFEA");
const valAI = document.getElementById("valAI");
const valFlight = document.getElementById("valFlight");
const valThermal = document.getElementById("valThermal");
const valWind = document.getElementById("valWind");
const valMesh = document.getElementById("valMesh");
const valFEA = document.getElementById("valFEA");
const cadQuality = document.getElementById("cadQuality");
const cadTriangles = document.getElementById("cadTriangles");
const cadVertices = document.getElementById("cadVertices");
const cadMeshScore = document.getElementById("cadMeshScore");
const cadSurfaceArea = document.getElementById("cadSurfaceArea");
const feaMaxDisp = document.getElementById("feaMaxDisp");
const feaMaxStress = document.getElementById("feaMaxStress");
const feaSafetyFactor = document.getElementById("feaSafetyFactor");
const feaConverged = document.getElementById("feaConverged");

function setStatus(text, tone = "ready") {
  statusBadge.textContent = text;
  statusBadge.dataset.tone = tone;
}

function updateClock() {
  const now = new Date();
  clock.textContent = now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function loadSample() {
  fetch("./sample_ai_output.json")
    .then((response) => response.json())
    .then(renderPayload)
    .catch(() => {
      renderPayload(getEmbeddedSample());
      setStatus("OFFLINE", "warn");
    });
}

function renderPayload(payload) {
  setStatus("LOADED", "ok");
  railCount.textContent = String(payload.system?.power_rails ?? "4");
  photonicLinks.textContent = String(payload.system?.photonic_links ?? "3");
  thermalNodes.textContent = String(payload.system?.thermal_nodes ?? "5");
  aiBest.textContent = payload.best?.name ?? "baseline_topology_2";
  aiScore.textContent = (payload.best?.score ?? 0.82).toFixed(2);
  aiRecommendation.textContent = payload.best?.tag ?? "Stiffened";
  aiModel.textContent = payload.ai?.model ?? "REIDCE v2";
  aiConfidence.textContent = (payload.ai?.confidence ?? 0.91).toFixed(2);
  aiStatus.textContent = payload.ai?.status ?? "Stable";
  processorLabel.textContent = payload.inspector?.processor ?? "Photonic Core v2";
  busVoltage.textContent = payload.inspector?.bus_voltage ?? "16 V";
  thermalMargin.textContent = payload.inspector?.thermal_margin ?? "+1.6 W";
  electroThermal.textContent = payload.inspector?.electro_thermal ?? "Converged";
  flightAlt.textContent = `${payload.flight?.target_altitude_m ?? 120} m`;
  flightSpeed.textContent = `${payload.flight?.target_speed_m_s ?? 14} m/s`;
  flightMode.textContent = payload.flight?.mode ?? "Test Pilot";
  shipEfficiency.textContent = (payload.wind?.ship_efficiency ?? 0.62).toFixed(2);
  kitePower.textContent = `${payload.wind?.kite_power_kw ?? 48} kW`;
  grossMargin.textContent = `$${formatNumber(payload.sales?.gross_margin_usd ?? 1200000)}`;
  shippingCost.textContent = `$${formatNumber(payload.sales?.shipping_cost_usd ?? 180000)}`;

  const cad = payload.cad ?? {};
  cadQuality.textContent = cad.quality ?? "High Fidelity";
  cadTriangles.textContent = String(cad.triangle_count ?? 192);
  cadVertices.textContent = String(cad.vertex_count ?? 98);
  cadMeshScore.textContent = (cad.mesh_score ?? 0.94).toFixed(2);
  cadSurfaceArea.textContent = `${(cad.surface_area ?? 0.0063).toFixed(4)} m²`;

  const fea = payload.fea ?? {};
  feaMaxDisp.textContent = `${((fea.max_displacement_m ?? 0.00012) * 1000).toFixed(2)} mm`;
  feaMaxStress.textContent = `${((fea.max_von_mises_pa ?? 45200000) / 1e6).toFixed(1)} MPa`;
  feaSafetyFactor.textContent = (fea.safety_factor ?? 5.53).toFixed(2);
  feaConverged.textContent = (fea.converged ?? true) ? "Yes" : "No";

  drawCadWireframe(cadCanvas, cad.wireframe ?? [], cad);
  drawFEAStress(feaCanvas, fea.element_stresses ?? []);
  drawFEADisplacement(feaDispCanvas, fea.nodal_displacements ?? []);
  drawFlightPath(flightCanvas, payload.flight?.path ?? []);
  drawThermalBars(thermalCanvas, payload.thermal?.nodes ?? []);
  drawWindCurve(windCanvas, payload.wind?.ship_force ?? []);
  drawSalesBars(salesCanvas, payload.sales ?? {});

  const meshQuality = Math.round((cad.mesh_score ?? 0.94) * 100);
  const feaSafety = Math.min(100, Math.round((fea.safety_factor ?? 5.53) / 10 * 100));
  updateStatusBars({
    ai: Math.round((payload.ai?.confidence ?? 0.91) * 100),
    flight: 74,
    thermal: 67,
    wind: Math.round((payload.wind?.ship_efficiency ?? 0.62) * 100),
    mesh: meshQuality,
    fea: feaSafety,
  });
}

function getEmbeddedSample() {
  return {
    ai: { model: "REIDCE v2", confidence: 0.91, status: "Stable" },
    best: { name: "baseline_topology_2", score: 0.82, tag: "Stiffened" },
    system: { power_rails: 4, photonic_links: 3, thermal_nodes: 5 },
    cad: {
      quality: "High Fidelity",
      triangle_count: 192,
      vertex_count: 98,
      mesh_score: 0.94,
      surface_area: 0.0063,
      wireframe: [
        { x1: -5, y1: 0, x2: 5, y2: 0 },
        { x1: 5, y1: 0, x2: 4.3, y2: 2.5 },
        { x1: 4.3, y1: 2.5, x2: 2.5, y2: 4.3 },
        { x1: 2.5, y1: 4.3, x2: 0, y2: 5 },
        { x1: 0, y1: 5, x2: -2.5, y2: 4.3 },
        { x1: -2.5, y1: 4.3, x2: -4.3, y2: 2.5 },
        { x1: -4.3, y1: 2.5, x2: -5, y2: 0 },
        { x1: -5, y1: 0, x2: -4.3, y2: -2.5 },
        { x1: -4.3, y1: -2.5, x2: -2.5, y2: -4.3 },
        { x1: -2.5, y1: -4.3, x2: 0, y2: -5 },
        { x1: 0, y1: -5, x2: 2.5, y2: -4.3 },
        { x1: 2.5, y1: -4.3, x2: 4.3, y2: -2.5 },
        { x1: 4.3, y1: -2.5, x2: 5, y2: 0 },
        { x1: -5, y1: 0, x2: -3, y2: 10 },
        { x1: 5, y1: 0, x2: 3, y2: 10 },
        { x1: 0, y1: 5, x2: 0, y2: 15 },
        { x1: 0, y1: -5, x2: 0, y2: 5 },
        { x1: -3, y1: 10, x2: 3, y2: 10 },
        { x1: 0, y1: 15, x2: -3, y2: 10 },
        { x1: 0, y1: 15, x2: 3, y2: 10 },
      ],
    },
    fea: {
      converged: true,
      max_displacement_m: 0.00012,
      max_von_mises_pa: 45200000,
      safety_factor: 5.53,
      element_stresses: [
        { id: 0, von_mises: 45.2 },
        { id: 1, von_mises: 40.8 },
        { id: 2, von_mises: 36.1 },
        { id: 3, von_mises: 31.5 },
        { id: 4, von_mises: 27.0 },
        { id: 5, von_mises: 22.3 },
        { id: 6, von_mises: 17.6 },
        { id: 7, von_mises: 12.9 },
        { id: 8, von_mises: 8.2 },
        { id: 9, von_mises: 3.5 },
      ],
      nodal_displacements: [
        { id: 0, ux: 0.0 },
        { id: 1, ux: 0.001 },
        { id: 2, ux: 0.004 },
        { id: 3, ux: 0.009 },
        { id: 4, ux: 0.016 },
        { id: 5, ux: 0.025 },
        { id: 6, ux: 0.036 },
        { id: 7, ux: 0.049 },
        { id: 8, ux: 0.064 },
        { id: 9, ux: 0.081 },
        { id: 10, ux: 0.12 },
      ],
    },
    flight: {
      target_altitude_m: 120,
      target_speed_m_s: 14,
      mode: "Test Pilot",
      path: [
        { t: 0.0, alt: 10.0 },
        { t: 5.0, alt: 40.0 },
        { t: 10.0, alt: 85.0 },
        { t: 15.0, alt: 110.0 },
        { t: 20.0, alt: 120.0 },
      ],
    },
    thermal: {
      nodes: [
        { name: "core", temp: 61.2 },
        { name: "pmu", temp: 54.8 },
        { name: "bus", temp: 49.6 },
        { name: "optics", temp: 58.1 },
      ],
    },
    wind: { ship_efficiency: 0.62, kite_power_kw: 48, ship_force: [0, 22, 38, 54, 68] },
    sales: { gross_margin_usd: 1200000, shipping_cost_usd: 180000, revenue_usd: 3200000 },
    inspector: { processor: "Photonic Core v2", bus_voltage: "16 V", thermal_margin: "+1.6 W", electro_thermal: "Converged" },
  };
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-US").format(value);
}

function drawFlightPath(canvas, points) {
  if (!canvas || points.length === 0) {
    return;
  }
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "rgba(255, 255, 255, 0.7)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  points.forEach((point, idx) => {
    const x = (canvas.width - 20) * (idx / (points.length - 1)) + 10;
    const y = canvas.height - 20 - (canvas.height - 40) * (point.alt / 130);
    if (idx === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();
}

function drawThermalBars(canvas, nodes) {
  if (!canvas || nodes.length === 0) {
    return;
  }
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const maxTemp = Math.max(...nodes.map((node) => node.temp));
  nodes.forEach((node, idx) => {
    const barWidth = (canvas.width - 30) / nodes.length;
    const height = ((node.temp / maxTemp) * (canvas.height - 30)) || 0;
    const x = 10 + idx * barWidth;
    const y = canvas.height - height - 10;
    ctx.fillStyle = "rgba(180, 180, 180, 0.7)";
    ctx.fillRect(x, y, barWidth * 0.6, height);
  });
}

function drawWindCurve(canvas, series) {
  if (!canvas || series.length === 0) {
    return;
  }
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "rgba(200, 200, 200, 0.7)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  series.forEach((value, idx) => {
    const x = (canvas.width - 20) * (idx / (series.length - 1)) + 10;
    const y = canvas.height - 20 - (canvas.height - 40) * (value / 80);
    if (idx === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();
}

function drawSalesBars(canvas, sales) {
  if (!canvas) {
    return;
  }
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const values = [sales.revenue_usd || 3200000, sales.gross_margin_usd || 1200000, sales.shipping_cost_usd || 180000];
  const colors = ["rgba(255, 255, 255, 0.6)", "rgba(180, 180, 180, 0.6)", "rgba(120, 120, 120, 0.6)"];
  const maxVal = Math.max(...values);
  values.forEach((value, idx) => {
    const barWidth = (canvas.width - 30) / values.length;
    const height = ((value / maxVal) * (canvas.height - 30)) || 0;
    const x = 10 + idx * barWidth;
    const y = canvas.height - height - 10;
    ctx.fillStyle = colors[idx];
    ctx.fillRect(x, y, barWidth * 0.6, height);
  });
}

function drawCadWireframe(canvas, wireframe, cadData) {
  if (!canvas) {
    return;
  }
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  // Grid backdrop
  ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
  ctx.lineWidth = 0.5;
  const gridStep = 20;
  for (let gx = 0; gx <= w; gx += gridStep) {
    ctx.beginPath();
    ctx.moveTo(gx, 0);
    ctx.lineTo(gx, h);
    ctx.stroke();
  }
  for (let gy = 0; gy <= h; gy += gridStep) {
    ctx.beginPath();
    ctx.moveTo(0, gy);
    ctx.lineTo(w, gy);
    ctx.stroke();
  }

  // Generate cylinder wireframe if no external data
  const edges = wireframe.length > 0 ? wireframe : generateCylinderWireframe(48);
  const cx = w / 2;
  const cy = h / 2;
  const scale = Math.min(w, h) / 40;

  // Draw wireframe edges with perspective glow
  ctx.lineWidth = 1.5;
  edges.forEach(function (edge, idx) {
    const alpha = 0.3 + 0.5 * (idx / edges.length);
    ctx.strokeStyle = `rgba(255, 255, 255, ${alpha.toFixed(2)})`;
    ctx.beginPath();
    ctx.moveTo(cx + edge.x1 * scale, cy - edge.y1 * scale);
    ctx.lineTo(cx + edge.x2 * scale, cy - edge.y2 * scale);
    ctx.stroke();
  });

  // Draw vertices as dots
  ctx.fillStyle = "rgba(180, 180, 180, 0.8)";
  edges.forEach(function (edge) {
    ctx.beginPath();
    ctx.arc(cx + edge.x1 * scale, cy - edge.y1 * scale, 2, 0, 2 * Math.PI);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(cx + edge.x2 * scale, cy - edge.y2 * scale, 2, 0, 2 * Math.PI);
    ctx.fill();
  });

  // Labels
  ctx.fillStyle = "rgba(200, 200, 200, 0.6)";
  ctx.font = "10px monospace";
  ctx.fillText("CAD: " + (cadData.quality || "High Fidelity"), 8, 14);
  ctx.fillText("Triangles: " + (cadData.triangle_count || 192), 8, 26);
}

function generateCylinderWireframe(segments) {
  const edges = [];
  const radius = 5;
  const height = 15;
  const skewX = 0.3;
  const skewY = 0.15;
  for (let i = 0; i < segments; i += 1) {
    const a1 = (2 * Math.PI * i) / segments;
    const a2 = (2 * Math.PI * ((i + 1) % segments)) / segments;
    const bx1 = radius * Math.cos(a1);
    const by1 = radius * Math.sin(a1) * 0.4;
    const bx2 = radius * Math.cos(a2);
    const by2 = radius * Math.sin(a2) * 0.4;
    edges.push({ x1: bx1, y1: by1 - height / 2, x2: bx2, y2: by2 - height / 2 });
    const tx1 = bx1 + skewX * height;
    const ty1 = by1 + height / 2 + skewY * height;
    const tx2 = bx2 + skewX * height;
    const ty2 = by2 + height / 2 + skewY * height;
    edges.push({ x1: tx1, y1: ty1, x2: tx2, y2: ty2 });
    if (i % 4 === 0) {
      edges.push({ x1: bx1, y1: by1 - height / 2, x2: tx1, y2: ty1 });
    }
  }
  return edges;
}

function drawFEAStress(canvas, stresses) {
  if (!canvas) {
    return;
  }
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  const data = stresses.length > 0 ? stresses : [
    { id: 0, von_mises: 45 }, { id: 1, von_mises: 40 }, { id: 2, von_mises: 36 },
    { id: 3, von_mises: 31 }, { id: 4, von_mises: 27 }, { id: 5, von_mises: 22 },
    { id: 6, von_mises: 17 }, { id: 7, von_mises: 13 }, { id: 8, von_mises: 8 },
    { id: 9, von_mises: 3 },
  ];
  const maxStress = Math.max(...data.map(function (d) { return d.von_mises; }));
  const barWidth = (w - 30) / data.length;

  data.forEach(function (elem, idx) {
    const ratio = elem.von_mises / (maxStress || 1);
    const barH = ratio * (h - 40);
    const x = 15 + idx * barWidth;
    const y = h - barH - 20;
    const r = Math.round(255 * ratio);
    const g = Math.round(255 * ratio);
    const b = Math.round(255 * ratio);
    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.8)`;
    ctx.fillRect(x, y, barWidth * 0.7, barH);
  });

  ctx.fillStyle = "rgba(200, 200, 200, 0.6)";
  ctx.font = "10px monospace";
  ctx.fillText("Von Mises (MPa)", 8, 14);
}

function drawFEADisplacement(canvas, displacements) {
  if (!canvas) {
    return;
  }
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  const data = displacements.length > 0 ? displacements : [
    { id: 0, ux: 0 }, { id: 1, ux: 0.001 }, { id: 2, ux: 0.004 },
    { id: 3, ux: 0.009 }, { id: 4, ux: 0.016 }, { id: 5, ux: 0.025 },
    { id: 6, ux: 0.036 }, { id: 7, ux: 0.049 }, { id: 8, ux: 0.064 },
    { id: 9, ux: 0.081 }, { id: 10, ux: 0.12 },
  ];
  if (data.length === 0) {
    return;
  }
  const maxDisp = Math.max(...data.map(function (d) { return Math.abs(d.ux); }));

  // Draw undeformed beam (dashed)
  ctx.setLineDash([4, 4]);
  ctx.strokeStyle = "rgba(160, 160, 160, 0.4)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(20, h / 2);
  ctx.lineTo(w - 20, h / 2);
  ctx.stroke();
  ctx.setLineDash([]);

  // Draw deformed beam
  ctx.strokeStyle = "rgba(255, 255, 255, 0.9)";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  data.forEach(function (node, idx) {
    const x = 20 + ((w - 40) * idx) / (data.length - 1);
    const yOffset = maxDisp > 0 ? (node.ux / maxDisp) * (h / 2 - 30) : 0;
    const y = h / 2 - yOffset;
    if (idx === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  // Draw nodes
  ctx.fillStyle = "rgba(180, 180, 180, 0.9)";
  data.forEach(function (node, idx) {
    const x = 20 + ((w - 40) * idx) / (data.length - 1);
    const yOffset = maxDisp > 0 ? (node.ux / maxDisp) * (h / 2 - 30) : 0;
    const y = h / 2 - yOffset;
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, 2 * Math.PI);
    ctx.fill();
  });

  // Fixed support indicator
  ctx.fillStyle = "rgba(150, 150, 150, 0.6)";
  ctx.fillRect(10, h / 2 - 15, 10, 30);

  ctx.fillStyle = "rgba(200, 200, 200, 0.6)";
  ctx.font = "10px monospace";
  ctx.fillText("Displacement (exaggerated)", 8, 14);
}

function updateStatusBars(values) {
  setBar(barAI, valAI, values.ai);
  setBar(barFlight, valFlight, values.flight);
  setBar(barThermal, valThermal, values.thermal);
  setBar(barWind, valWind, values.wind);
  setBar(barMesh, valMesh, values.mesh);
  setBar(barFEA, valFEA, values.fea);
}

function setBar(bar, label, value) {
  if (!bar || !label) {
    return;
  }
  const clamped = Math.max(0, Math.min(100, value));
  bar.style.width = `${clamped}%`;
  label.textContent = `${clamped}%`;
}

function exportSnapshot() {
  const snapshot = {
    rails: railCount.textContent,
    photonics: photonicLinks.textContent,
    thermal: thermalNodes.textContent,
    processor: processorLabel.textContent,
    bus: busVoltage.textContent,
    margin: thermalMargin.textContent,
    electroThermal: electroThermal.textContent,
    cad: {
      quality: cadQuality.textContent,
      triangles: cadTriangles.textContent,
      vertices: cadVertices.textContent,
      meshScore: cadMeshScore.textContent,
      surfaceArea: cadSurfaceArea.textContent,
    },
    fea: {
      maxDisplacement: feaMaxDisp.textContent,
      maxStress: feaMaxStress.textContent,
      safetyFactor: feaSafetyFactor.textContent,
      converged: feaConverged.textContent,
    },
    timestamp: new Date().toISOString(),
  };
  const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "studio_snapshot.json";
  link.click();
  URL.revokeObjectURL(link.href);
  setStatus("EXPORTED", "info");
}

btnLoadSample.addEventListener("click", loadSample);
btnExport.addEventListener("click", exportSnapshot);

updateClock();
setInterval(updateClock, 1000);
