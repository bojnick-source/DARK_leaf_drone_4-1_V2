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
const meshCanvas = document.getElementById("meshCanvas");
const barAI = document.getElementById("barAI");
const barFlight = document.getElementById("barFlight");
const barThermal = document.getElementById("barThermal");
const barWind = document.getElementById("barWind");
const valAI = document.getElementById("valAI");
const valFlight = document.getElementById("valFlight");
const valThermal = document.getElementById("valThermal");
const valWind = document.getElementById("valWind");

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

  drawFlightPath(flightCanvas, payload.flight?.path ?? []);
  drawThermalBars(thermalCanvas, payload.thermal?.nodes ?? []);
  drawWindCurve(windCanvas, payload.wind?.ship_force ?? []);
  drawSalesBars(salesCanvas, payload.sales ?? {});
  drawMesh(meshCanvas);
  updateStatusBars({
    ai: Math.round((payload.ai?.confidence ?? 0.91) * 100),
    flight: 74,
    thermal: 67,
    wind: Math.round((payload.wind?.ship_efficiency ?? 0.62) * 100),
  });
}

function getEmbeddedSample() {
  return {
    ai: { model: "REIDCE v2", confidence: 0.91, status: "Stable" },
    best: { name: "baseline_topology_2", score: 0.82, tag: "Stiffened" },
    system: { power_rails: 4, photonic_links: 3, thermal_nodes: 5 },
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
  ctx.strokeStyle = "rgba(56, 243, 255, 0.8)";
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
    ctx.fillStyle = "rgba(124, 92, 255, 0.7)";
    ctx.fillRect(x, y, barWidth * 0.6, height);
  });
}

function drawWindCurve(canvas, series) {
  if (!canvas || series.length === 0) {
    return;
  }
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "rgba(199, 125, 255, 0.8)";
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
  const colors = ["rgba(56, 243, 255, 0.7)", "rgba(124, 92, 255, 0.7)", "rgba(255, 120, 120, 0.6)"];
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

function drawMesh(canvas) {
  if (!canvas) {
    return;
  }
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const cols = 18;
  const rows = 6;
  const width = canvas.width;
  const height = canvas.height;
  ctx.strokeStyle = "rgba(56, 243, 255, 0.35)";
  for (let i = 0; i <= cols; i += 1) {
    const x = (width / cols) * i;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  for (let j = 0; j <= rows; j += 1) {
    const y = (height / rows) * j;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
  ctx.strokeStyle = "rgba(124, 92, 255, 0.6)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(40, height - 40);
  ctx.lineTo(width / 2, 30);
  ctx.lineTo(width - 40, height - 60);
  ctx.stroke();
  ctx.fillStyle = "rgba(56, 243, 255, 0.2)";
  ctx.fillRect(width / 2 - 60, height / 2 - 20, 120, 40);
}

function updateStatusBars(values) {
  setBar(barAI, valAI, values.ai);
  setBar(barFlight, valFlight, values.flight);
  setBar(barThermal, valThermal, values.thermal);
  setBar(barWind, valWind, values.wind);
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
