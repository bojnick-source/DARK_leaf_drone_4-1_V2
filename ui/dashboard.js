const safeText = (el, value) => {
  if (!el) {
    return;
  }
  el.textContent = String(value);
};
const getElementById = (id) => document.getElementById(id);

let notice;
let statusPill;
let selfTestPill;
let clockPill;
let modePill;
let schemaPill;
let payloadPill;
let tripwireBanner;
let jsonFileInput;
const SAMPLE_FETCH_TIMEOUT_MS = 5000;
const STATUS_COLORS = {
  ready: "#1f2937",
  info: "#1e3a8a",
  warn: "#7c2d12",
  ok: "#14532d",
  fail: "#7f1d1d",
  loading: "#92400e"
};
const CAD_TILT_MAX_DEG = 12;
let currentPayload = null;
const TAB_STORAGE_KEY = "daily-dashboard-tab";
const TAB_OPTIONS = ["cad", "sim", "insights", "compute"];
const TAB_MODE_LABELS = {
  cad: "CAD",
  sim: "SIM",
  insights: "INSIGHTS",
  compute: "COMPUTE"
};
const WORKSPACE_STORAGE_KEY = "darkleaf.workspaces.v1";
let activeWorkspaceId = "ws-1";

function formatQuantity(quantity, fallback) {
  if (!quantity || quantity.value === null || quantity.value === undefined || !quantity.unit) {
    return fallback;
  }
  return `${quantity.value} ${quantity.unit}`;
}

function getGeometryPayload(payload) {
  return (
    payload?.design?.geometry ||
    payload?.inputs?.design?.geometry ||
    payload?.inputs?.geometry ||
    payload?.geometry ||
    payload?.cad?.geometry ||
    null
  );
}

function updateCadInspector(payload) {
  const spanEl = getElementById("cadSpan");
  const massEl = getElementById("cadMass");
  const batteryEl = getElementById("cadBattery");
  const envelopeEl = getElementById("cadEnvelope");
  const actuatorEl = getElementById("cadActuator");
  const toleranceEl = getElementById("cadTolerance");
  const geometry = getGeometryPayload(payload);

  if (spanEl) {
    spanEl.textContent = formatQuantity(geometry?.envelope_max, spanEl.dataset.default || spanEl.textContent);
  }
  if (massEl) {
    massEl.textContent = massEl.dataset.default || massEl.textContent;
  }
  if (batteryEl) {
    batteryEl.textContent = batteryEl.dataset.default || batteryEl.textContent;
  }
  if (envelopeEl) {
    envelopeEl.textContent = formatQuantity(geometry?.envelope_max, envelopeEl.dataset.default || envelopeEl.textContent);
  }
  if (actuatorEl) {
    actuatorEl.textContent = formatQuantity(
      geometry?.key_dimensions?.actuator_diameter,
      actuatorEl.dataset.default || actuatorEl.textContent
    );
  }
  if (toleranceEl) {
    toleranceEl.textContent = formatQuantity(
      geometry?.tolerances?.general_linear,
      toleranceEl.dataset.default || toleranceEl.textContent
    );
  }
}

function initCadViewport() {
  const cadViewport = getElementById("cadViewport");
  if (!cadViewport) {
    return;
  }
  let targetX = 0;
  let targetY = 0;
  let currentX = 0;
  let currentY = 0;
  let rafId;

  const updateFrame = () => {
    currentX += (targetX - currentX) * 0.08;
    currentY += (targetY - currentY) * 0.08;
    cadViewport.style.setProperty("--cad-tilt-x", `${currentY}deg`);
    cadViewport.style.setProperty("--cad-tilt-y", `${currentX}deg`);
    cadViewport.style.setProperty("--cad-shift-x", `${currentX * 0.7}px`);
    cadViewport.style.setProperty("--cad-shift-y", `${currentY * 0.7}px`);
    rafId = window.requestAnimationFrame(updateFrame);
  };

  const handlePointerMove = (event) => {
    const rect = cadViewport.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width - 0.5;
    const y = (event.clientY - rect.top) / rect.height - 0.5;
    targetX = Math.max(Math.min(x * CAD_TILT_MAX_DEG * 2, CAD_TILT_MAX_DEG), -CAD_TILT_MAX_DEG);
    targetY = Math.max(Math.min(-y * CAD_TILT_MAX_DEG * 2, CAD_TILT_MAX_DEG), -CAD_TILT_MAX_DEG);
  };

  const resetTilt = () => {
    targetX = 0;
    targetY = 0;
  };

  cadViewport.addEventListener("pointermove", handlePointerMove);
  cadViewport.addEventListener("pointerleave", resetTilt);
  cadViewport.addEventListener("pointerdown", (event) => {
    cadViewport.setPointerCapture(event.pointerId);
  });
  cadViewport.addEventListener("pointerup", (event) => {
    cadViewport.releasePointerCapture(event.pointerId);
  });

  rafId = window.requestAnimationFrame(updateFrame);

  window.addEventListener("beforeunload", () => {
    if (rafId) {
      window.cancelAnimationFrame(rafId);
    }
  });
}

function setStatus(label, tone, state = null) {
  safeText(statusPill, `STATUS: ${label}`);
  if (statusPill) {
    statusPill.style.background = tone;
    if (state) {
      statusPill.dataset.state = state;
    } else {
      statusPill.removeAttribute("data-state");
    }
  }
}

function showNotice(title, message) {
  if (!notice) {
    return;
  }
  const titleEl = document.createElement("div");
  titleEl.className = "title";
  titleEl.textContent = String(title);
  const hintEl = document.createElement("div");
  hintEl.className = "hint";
  hintEl.textContent = String(message);
  notice.replaceChildren(titleEl, hintEl);
}

function updateClock() {
  const now = new Date();
  const time = now.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
  safeText(clockPill, `TIME: ${time}`);
}

function attachHandlers() {
  const btnLoadSample = getElementById("btnLoadSample");
  const btnValidate = getElementById("btnValidate");
  const btnHelp = getElementById("btnHelp");
  const btnExport = getElementById("btnExport");
  const tabButtons = document.querySelectorAll("[data-tab]");
  const menuTriggers = document.querySelectorAll(".menu-trigger");
  const menuActions = document.querySelectorAll("[data-action]");
  const workspaceTabs = document.querySelectorAll(".workspace-tab");
  const workspaceAdd = document.getElementById("workspaceAdd");
  const modeToolButtons = document.querySelectorAll("[data-mode-tools] [data-action]");

  if (btnLoadSample) {
    btnLoadSample.addEventListener("click", async () => {
      setStatus("LOADING", STATUS_COLORS.loading, "warn");
      showNotice("Loading sample...", "Attempting to fetch sample payload.");
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), SAMPLE_FETCH_TIMEOUT_MS);
      try {
        const response = await fetch("./sample_payload.json", {
          cache: "no-store",
          signal: controller.signal
        });
        if (!response.ok) {
          throw new Error(`Sample payload request failed (${response.status})`);
        }
        const contentType = response.headers.get("content-type") || "";
        const normalizedType = contentType.toLowerCase().split(";")[0].trim();
        const isJson =
          normalizedType === "application/json" ||
          normalizedType === "text/json" ||
          normalizedType.endsWith("+json");
        if (!isJson) {
          throw new Error("Sample payload response was not JSON");
        }
        const payload = await response.json();
        currentPayload = payload;
        safeText(payloadPill, "PAYLOAD: SAMPLE");
        const schemaLabel = payload.schema ? String(payload.schema) : "(unknown)";
        safeText(schemaPill, `SCHEMA: ${schemaLabel}`);
        updateCadInspector(payload);
        showNotice("Sample loaded", "Sample payload retrieved successfully.");
        setStatus("OK", STATUS_COLORS.ok, "ok");
      } catch (error) {
        setStatus("FAIL", STATUS_COLORS.fail, "fail");
        showNotice("Sample load failed", `${error.message}`);
      } finally {
        clearTimeout(timeoutId);
      }
    });
  }

  if (btnValidate) {
    btnValidate.addEventListener("click", () => {
      if (!currentPayload) {
        setStatus("WARN", STATUS_COLORS.warn, "warn");
        showNotice("Validation skipped", "Load a payload before running validation.");
        return;
      }
      if (window.validateDashboardPayload) {
        try {
          const result = window.validateDashboardPayload(currentPayload);
          showNotice("Validation complete", result || "Validation executed.");
          setStatus("OK", STATUS_COLORS.ok, "ok");
        } catch (error) {
          setStatus("FAIL", STATUS_COLORS.fail, "fail");
          showNotice("Validation error", `${error.message}`);
        }
      } else {
        setStatus("WARN", STATUS_COLORS.warn, "warn");
        showNotice(
          "Validator not wired yet",
          "Hook up validateDashboardPayload() to enable validation."
        );
      }
    });
  }

  if (btnHelp) {
    btnHelp.addEventListener("click", () => {
      setStatus("INFO", STATUS_COLORS.info, "info");
      const helpMessage = [
        "Serve the ui folder with a simple HTTP server (e.g. 'python -m http.server')",
        "and open /dashboard.html."
      ].join(" ");
      showNotice("Local run tips", helpMessage);
    });
  }

  if (btnExport) {
    btnExport.addEventListener("click", () => {
      exportLayoutJson();
    });
  }

  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.dataset.tab;
      if (!target) {
        return;
      }
      setActiveTab(target);
    });
  });

  menuTriggers.forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.dataset.menu;
      toggleMenu(target);
    });
  });

  menuActions.forEach((button) => {
    button.addEventListener("click", () => {
      handleMenuAction(button.dataset.action);
    });
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".menu-panel") && !event.target.closest(".menu-trigger")) {
      closeMenus();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeMenus();
    }
  });

  workspaceTabs.forEach((tab) => {
    tab.addEventListener("click", (event) => {
      if (event.target.classList.contains("tab-close")) {
        closeWorkspace(tab.dataset.workspace);
        return;
      }
      setActiveWorkspace(tab.dataset.workspace);
    });
    tab.addEventListener("dblclick", () => {
      startWorkspaceRename(tab);
    });
  });

  if (workspaceAdd) {
    workspaceAdd.addEventListener("click", () => {
      addWorkspace();
    });
  }

  modeToolButtons.forEach((button) => {
    button.addEventListener("click", () => {
      handleMenuAction(button.dataset.action);
    });
  });
}

function handleGlobalError(message) {
  setStatus("FAIL", STATUS_COLORS.fail, "fail");
  showNotice("Dashboard error", String(message));
}

window.addEventListener("error", (event) => {
  handleGlobalError(event.error ? event.error.message : event.message);
});

window.addEventListener("unhandledrejection", (event) => {
  let message = "Unhandled promise rejection";
  if (event.reason) {
    message = event.reason.message || String(event.reason);
  }
  handleGlobalError(message);
});

let clockIntervalId;

function renderSelfTest() {
  const hasMenu = Boolean(document.getElementById("menuBar"));
  const hasTask = Boolean(document.getElementById("taskBar"));
  const now = new Date().toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
  const message = [
    "UI loaded",
    now,
    `Menu: ${hasMenu ? "YES" : "NO"}`,
    `Task: ${hasTask ? "YES" : "NO"}`
  ].join(" · ");
  safeText(selfTestPill, `SELF-TEST: ${message}`);
}

function setActiveTab(tabName, updateUrl = true) {
  try {
    if (!TAB_OPTIONS.includes(tabName)) {
      throw new Error(`Unknown tab: ${tabName}`);
    }
    const panels = document.querySelectorAll("[data-tab-panel]");
    panels.forEach((panel) => {
      const isActive = panel.dataset.tabPanel === tabName;
      panel.classList.toggle("active", isActive);
    });
    document.querySelectorAll("[data-tab]").forEach((button) => {
      button.classList.toggle("active", button.dataset.tab === tabName);
    });
    document.querySelectorAll("[data-mode-tools]").forEach((tools) => {
      tools.classList.toggle("active", tools.dataset.modeTools === tabName);
    });
    const label = TAB_MODE_LABELS[tabName] || "CAD";
    safeText(modePill, `MODE: ${label}`);
    updateWorkspaceTab(tabName);
    if (updateUrl) {
      window.location.hash = `#${tabName}`;
    }
    localStorage.setItem(TAB_STORAGE_KEY, tabName);
  } catch (error) {
    console.error("Tab update failed", error);
    showNotice("Tab update failed", String(error.message || error));
    setStatus("FAIL", STATUS_COLORS.fail, "fail");
  }
}

function getInitialTab() {
  const hash = window.location.hash.replace("#", "");
  if (TAB_OPTIONS.includes(hash)) {
    return hash;
  }
  const stored = localStorage.getItem(TAB_STORAGE_KEY);
  if (TAB_OPTIONS.includes(stored)) {
    return stored;
  }
  return "cad";
}

function exportLayoutJson() {
  const currentTab =
    document.querySelector("[data-tab].active")?.dataset.tab || getInitialTab();
  const payload = {
    tab: currentTab,
    timestamp: new Date().toISOString(),
    status: statusPill ? statusPill.textContent : "STATUS: READY"
  };
  downloadJson(payload, `dashboard-${currentTab}.json`);
  setStatus("EXPORTED", STATUS_COLORS.ok, "ok");
  showNotice("Export complete", "Layout JSON exported.");
}

function openMenu(menuId) {
  const panels = document.querySelectorAll(".menu-panel");
  panels.forEach((panel) => {
    const isTarget = panel.dataset.menuPanel === menuId;
    panel.classList.toggle("active", isTarget);
    if (!isTarget) {
      panel.classList.remove("active");
    }
  });
}

function toggleMenu(menuId) {
  const target = document.querySelector(`.menu-panel[data-menu-panel='${menuId}']`);
  if (target?.classList.contains("active")) {
    closeMenus();
    return;
  }
  openMenu(menuId);
}

function closeMenus() {
  document.querySelectorAll(".menu-panel").forEach((panel) => panel.classList.remove("active"));
}

function handleMenuAction(action) {
  switch (action) {
    case "open-json":
      if (jsonFileInput) {
        jsonFileInput.value = "";
        jsonFileInput.click();
      }
      break;
    case "export-diagnostics":
      exportDiagnostics();
      break;
    case "self-test":
      runTripwires();
      break;
    case "reset-layout":
      showNotice("Layout reset", "Layout reset stub executed.");
      setStatus("RESET", STATUS_COLORS.info, "info");
      break;
    case "compute-generate":
      runComputeGenerate();
      break;
    case "compute-clear":
      clearComputeResults();
      break;
    default:
      break;
  }
  closeMenus();
}

function exportDiagnostics() {
  const payload = {
    timestamp: new Date().toISOString(),
    workspace: activeWorkspaceId,
    tab: document.querySelector("[data-tab].active")?.dataset.tab || getInitialTab(),
    status: statusPill ? statusPill.textContent : "STATUS: READY",
    mode: modePill ? modePill.textContent : "MODE: UNKNOWN",
    validation: currentPayload ? "payload-loaded" : "no-payload"
  };
  downloadJson(payload, `diagnostics-${activeWorkspaceId}.json`);
  showNotice("Diagnostics exported", "Exported diagnostics JSON.");
  setStatus("DIAGNOSTICS", STATUS_COLORS.ok, "ok");
}

function downloadJson(payload, filename) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json"
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function addWorkspace() {
  const workspaceId = `ws-${Date.now()}`;
  const workspace = {
    id: workspaceId,
    title: "New Workspace",
    tab: getInitialTab()
  };
  const state = loadWorkspaceState();
  state.tabs.push(workspace);
  state.activeId = workspaceId;
  saveWorkspaceState(state);
  renderWorkspaces(state.tabs);
  setActiveWorkspace(workspaceId);
}

function closeWorkspace(workspaceId) {
  const state = loadWorkspaceState();
  if (state.tabs.length <= 1) {
    showNotice("Workspace locked", "At least one workspace must remain open.");
    return;
  }
  const filtered = state.tabs.filter((tab) => tab.id !== workspaceId);
  state.tabs = filtered;
  if (state.activeId === workspaceId) {
    state.activeId = filtered[0].id;
  }
  saveWorkspaceState(state);
  renderWorkspaces(filtered);
  if (activeWorkspaceId === workspaceId) {
    setActiveWorkspace(state.activeId);
  }
}

function setActiveWorkspace(workspaceId) {
  const state = loadWorkspaceState();
  const target = state.tabs.find((tab) => tab.id === workspaceId);
  if (!target) {
    return;
  }
  activeWorkspaceId = workspaceId;
  state.activeId = workspaceId;
  saveWorkspaceState(state);
  renderWorkspaces(state.tabs);
  if (target.tab) {
    setActiveTab(target.tab);
  }
}

function startWorkspaceRename(tabEl) {
  const titleEl = tabEl.querySelector(".tab-title");
  if (!titleEl) {
    return;
  }
  const currentText = titleEl.textContent;
  const input = document.createElement("input");
  input.type = "text";
  input.value = currentText;
  input.className = "tab-rename";
  tabEl.appendChild(input);
  input.focus();
  input.select();
  const finalize = (commit) => {
    input.remove();
    if (commit) {
      updateWorkspaceTitle(tabEl.dataset.workspace, input.value);
    }
  };
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      finalize(true);
    }
    if (event.key === "Escape") {
      finalize(false);
    }
  });
  input.addEventListener("blur", () => finalize(true));
}

function updateWorkspaceTitle(workspaceId, title) {
  const state = loadWorkspaceState();
  const target = state.tabs.find((tab) => tab.id === workspaceId);
  if (target) {
    target.title = title || target.title;
    saveWorkspaceState(state);
    renderWorkspaces(state.tabs);
  }
}

function loadWorkspaceState() {
  const stored = localStorage.getItem(WORKSPACE_STORAGE_KEY);
  if (stored) {
    try {
      const parsed = JSON.parse(stored);
      if (Array.isArray(parsed)) {
        return { version: 1, activeId: parsed[0]?.id || "ws-1", tabs: parsed };
      }
      return parsed;
    } catch (error) {
      console.error("Workspace load failed", error);
    }
  }
  return {
    version: 1,
    activeId: "ws-1",
    tabs: [
      { id: "ws-1", title: "Daily Dashboard", tab: "cad" },
      { id: "ws-2", title: "Run Review", tab: "sim" },
      { id: "ws-3", title: "Comparison", tab: "insights" }
    ]
  };
}

function saveWorkspaceState(state) {
  localStorage.setItem(WORKSPACE_STORAGE_KEY, JSON.stringify(state));
}

function renderWorkspaces(workspaces) {
  const container = document.getElementById("workspaceTabs");
  if (!container) {
    return;
  }
  container.querySelectorAll(".workspace-tab").forEach((tab) => tab.remove());
  workspaces.forEach((workspace) => {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = `workspace-tab${workspace.id === activeWorkspaceId ? " active" : ""}`;
    tab.dataset.workspace = workspace.id;
    tab.innerHTML = `
      <svg class="tab-shape" viewBox="0 0 200 32" preserveAspectRatio="none" aria-hidden="true">
        <path d="M0 30 C0 18 6 6 20 4 L60 0 L140 0 L180 4 C194 6 200 18 200 30 L200 32 L0 32 Z" />
      </svg>
      <span class="tab-title">${workspace.title}</span>
      <span class="tab-close" aria-label="Close workspace">×</span>
    `;
    tab.addEventListener("click", (event) => {
      if (event.target.classList.contains("tab-close")) {
        closeWorkspace(workspace.id);
        return;
      }
      setActiveWorkspace(workspace.id);
    });
    tab.addEventListener("dblclick", () => {
      startWorkspaceRename(tab);
    });
    container.insertBefore(tab, document.getElementById("workspaceAdd"));
  });
}

function updateWorkspaceTab(tabName) {
  const state = loadWorkspaceState();
  const target = state.tabs.find((tab) => tab.id === activeWorkspaceId);
  if (target) {
    target.tab = tabName;
    saveWorkspaceState(state);
  }
}

function runTripwires() {
  const failures = [];
  if (!document.getElementById("chromeStrip")) {
    failures.push("Chrome strip missing");
  }
  const workspaceCount = document.querySelectorAll(".workspace-tab").length;
  if (workspaceCount < 1) {
    failures.push("No workspace tabs");
  }
  const activeWorkspace = document.querySelector(".workspace-tab.active");
  if (!activeWorkspace) {
    failures.push("Active workspace missing");
  }
  if (activeWorkspace) {
    const zIndex = Number(window.getComputedStyle(activeWorkspace).zIndex || 0);
    if (zIndex < 2) {
      failures.push("Active workspace z-index low");
    }
  }
  const fileMenu = document.querySelector("[data-menu-panel='file']");
  openMenu("file");
  if (!fileMenu?.classList.contains("active")) {
    failures.push("Menu open failed");
  }
  const escEvent = new KeyboardEvent("keydown", { key: "Escape" });
  document.dispatchEvent(escEvent);
  if (fileMenu?.classList.contains("active")) {
    failures.push("Menu Esc close failed");
  }
  if (!document.getElementById("taskBar")) {
    failures.push("Taskbar missing");
  }
  const currentMode = modePill?.textContent || "";
  if (!currentMode.includes("MODE")) {
    failures.push("Mode pill missing");
  }
  const originalTab = document.querySelector("[data-tab].active")?.dataset.tab || "cad";
  setActiveTab("sim", false);
  if (!modePill?.textContent.includes("SIM")) {
    failures.push("Mode tab sync failed");
  }
  setActiveTab(originalTab, false);
  if (failures.length > 0) {
    showTripwireBanner(failures);
  } else {
    hideTripwireBanner();
    showNotice("Self-test passed", "All UI tripwires passed.");
    setStatus("OK", STATUS_COLORS.ok, "ok");
  }
}

function showTripwireBanner(failures) {
  if (!tripwireBanner) {
    return;
  }
  tripwireBanner.hidden = false;
  tripwireBanner.textContent = `Tripwire failures: ${failures.join(", ")}`;
  setStatus("FAIL", STATUS_COLORS.fail, "fail");
}

function hideTripwireBanner() {
  if (tripwireBanner) {
    tripwireBanner.hidden = true;
  }
}

// ── Computational AI drone generation ────────────────────────────────────

const DRONE_COMPONENTS = [
  { id: "fuselage", name: "Fuselage / Airframe", desc: "Central carbon-fiber monocoque body", color: "#3a4a72" },
  { id: "top_shell", name: "Top Shell Cover", desc: "Aerodynamic fairing with cooling vents", color: "#4a5a82" },
  { id: "bottom_plate", name: "Bottom Mounting Plate", desc: "Structural base with vibration dampeners", color: "#2a3a62" },
  { id: "arm_front_l", name: "Arm — Front Left", desc: "Carbon-fiber motor arm with wire routing", color: "#3a5a6a" },
  { id: "arm_front_r", name: "Arm — Front Right", desc: "Carbon-fiber motor arm with wire routing", color: "#3a5a6a" },
  { id: "arm_rear_l", name: "Arm — Rear Left", desc: "Carbon-fiber motor arm with wire routing", color: "#3a5a6a" },
  { id: "arm_rear_r", name: "Arm — Rear Right", desc: "Carbon-fiber motor arm with wire routing", color: "#3a5a6a" },
  { id: "motor_fl", name: "Motor — Front Left", desc: "Brushless DC axial-flux motor (from EM module)", color: "#5a6a9a" },
  { id: "motor_fr", name: "Motor — Front Right", desc: "Brushless DC axial-flux motor (from EM module)", color: "#5a6a9a" },
  { id: "motor_rl", name: "Motor — Rear Left", desc: "Brushless DC axial-flux motor (from EM module)", color: "#5a6a9a" },
  { id: "motor_rr", name: "Motor — Rear Right", desc: "Brushless DC axial-flux motor (from EM module)", color: "#5a6a9a" },
  { id: "propeller_fl", name: "Propeller — Front Left", desc: "Variable-pitch rotor blade (thrust from E-M)", color: "#38f3ff" },
  { id: "propeller_fr", name: "Propeller — Front Right", desc: "Variable-pitch rotor blade (thrust from E-M)", color: "#38f3ff" },
  { id: "propeller_rl", name: "Propeller — Rear Left", desc: "Variable-pitch rotor blade (thrust from E-M)", color: "#38f3ff" },
  { id: "propeller_rr", name: "Propeller — Rear Right", desc: "Variable-pitch rotor blade (thrust from E-M)", color: "#38f3ff" },
  { id: "battery", name: "Battery Pack", desc: "4S LiPo pack sized by endurance test", color: "#4a7a3a" },
  { id: "esc_board", name: "ESC / Power Distribution", desc: "4-in-1 ESC with current sensing", color: "#7a5a2a" },
  { id: "flight_controller", name: "Flight Controller", desc: "IMU + barometer + GPS — PID autopilot", color: "#8a4a8a" },
  { id: "gps_module", name: "GPS / Navigation Module", desc: "Multi-constellation GNSS receiver", color: "#4a6a4a" },
  { id: "camera_gimbal", name: "Camera Gimbal Assembly", desc: "2-axis stabilized gimbal mount", color: "#6a5a3a" },
  { id: "landing_gear", name: "Landing Gear", desc: "Shock-absorbing skid landing struts", color: "#5a5a5a" },
  { id: "receiver", name: "RC Receiver / Telemetry", desc: "Long-range control link with failsafe", color: "#5a4a6a" },
  { id: "led_array", name: "LED Navigation Lights", desc: "Forward white, rear red, arm-tip strobes", color: "#aa3a3a" },
  { id: "canopy", name: "Canopy / Radome", desc: "Transparent RF-permeable top cover", color: "#6a7aaa" },
  { id: "payload_bay", name: "Payload Bay", desc: "Modular quick-release cargo mount", color: "#c77dff" },
];

function _simDesignLoop(iterations) {
  let mass = 2.4;
  let wingArea = 0.35;
  let maxThrust = 45.0;
  let cd0 = 0.04;
  let maxTilt = 0.5236;
  let maxSpeed = 60.0;
  let bestScore = 0;
  let bestIter = 0;
  const records = [];

  for (let i = 0; i < iterations; i++) {
    const weight = mass * 9.80665;
    const cruiseSpeed = Math.min(12.0, maxSpeed * 0.6);
    const q = 0.5 * 1.225 * cruiseSpeed * cruiseSpeed;
    const clRequired = weight / Math.max(q * wingArea, 1e-6);
    const cdInduced = 0.6 * (clRequired / 4.8) * (clRequired / 4.8);
    const drag = q * wingArea * (cd0 + cdInduced);
    const thrust = 0.8 * maxThrust;
    const ps = cruiseSpeed * (thrust - drag) / weight;

    const maxBank = Math.min(maxTilt, 1.047);
    const cosBank = Math.cos(maxBank);
    const loadFactor = 1.0 / Math.max(cosBank, 1e-6);
    const omega = 9.80665 * Math.sqrt(Math.max(loadFactor * loadFactor - 1, 0)) / cruiseSpeed;
    const turnRadius = cruiseSpeed / Math.max(omega, 1e-9);
    const specificEnergy = 30 + cruiseSpeed * cruiseSpeed / (2 * 9.80665);

    const climbPass = maxThrust > mass * 9.80665 * 1.2;
    const speedPass = maxSpeed <= 60;
    const turnPass = Math.degrees ? false : omega * 57.2958 > 5;
    const turnDegS = omega * 57.2958;
    const endurancePass = mass < 5.0;
    const passCount = [climbPass, speedPass, turnDegS > 5, endurancePass].filter(Boolean).length;
    const score = (passCount / 4) * 50 + Math.min(ps / 5, 1) * 25 + Math.min(turnDegS / 60, 1) * 25;

    records.push({
      iteration: i, mass, wingArea, maxThrust, cd0, maxTilt, maxSpeed,
      ps: Math.round(ps * 1000) / 1000,
      loadFactor: Math.round(loadFactor * 1000) / 1000,
      turnRateDegS: Math.round(turnDegS * 100) / 100,
      turnRadius: Math.round(turnRadius * 100) / 100,
      specificEnergy: Math.round(specificEnergy * 100) / 100,
      drag: Math.round(drag * 1000) / 1000,
      thrustAvailable: Math.round(thrust * 100) / 100,
      score: Math.round(score * 10) / 10,
      climbPass, speedPass, turnPass: turnDegS > 5, endurancePass,
    });

    if (score > bestScore) { bestScore = score; bestIter = i; }
    if (score >= 85) { break; }

    if (!climbPass) { maxThrust = Math.min(maxThrust * 1.15, 120); }
    if (!endurancePass) { mass = Math.max(mass * 0.95, 0.5); }
    if (turnDegS <= 5) { wingArea = Math.min(wingArea * 1.1, 1.0); }
  }

  const best = records[bestIter];
  const g = 9.80665;
  const twRatio = maxThrust / (mass * g);
  const wingLoading = (mass * g) / wingArea;
  const ldRatio = best ? (4.8 * 0.2) / Math.max(cd0, 0.001) : 0;

  return {
    records, bestIter, bestScore: Math.round(bestScore * 10) / 10,
    converged: bestScore >= 85,
    best, twRatio: Math.round(twRatio * 100) / 100,
    wingLoading: Math.round(wingLoading * 100) / 100,
    ldRatio: Math.round(ldRatio * 10) / 10,
  };
}

function _renderDroneModel(data) {
  const svg = getElementById("computeModelSvg");
  const group = getElementById("computeModelGroup");
  if (!svg || !group) { return; }

  const scale = data.best ? Math.min(data.best.wingArea * 2, 1.5) : 1.0;
  const armLen = 140 * scale;
  const bodyRx = 60 * scale;
  const bodyRy = 32 * scale;
  const rotorR = 36 * scale;

  const cx = 400;
  const cy = 210;

  const armPositions = [
    { x: cx - armLen, y: cy - armLen * 0.5, label: "FL" },
    { x: cx + armLen, y: cy - armLen * 0.5, label: "FR" },
    { x: cx - armLen, y: cy + armLen * 0.5, label: "RL" },
    { x: cx + armLen, y: cy + armLen * 0.5, label: "RR" },
  ];

  let svgContent = "";

  svgContent += `<ellipse cx="${cx}" cy="${cy + 30}" rx="${bodyRx + 80}" ry="30" fill="rgba(8,12,18,0.5)"/>`;

  armPositions.forEach((pos) => {
    svgContent += `<line x1="${cx}" y1="${cy}" x2="${pos.x}" y2="${pos.y}" stroke="#3a5a6a" stroke-width="6" stroke-linecap="round"/>`;
  });

  svgContent += `<ellipse cx="${cx}" cy="${cy}" rx="${bodyRx}" ry="${bodyRy}" fill="url(#compFuseGrad)" stroke="rgba(255,255,255,0.18)" stroke-width="1.4"/>`;

  svgContent += `<rect x="${cx - 20}" y="${cy - 12}" width="40" height="24" rx="4" fill="url(#compBattGrad)" stroke="rgba(74,122,58,0.6)" stroke-width="1" opacity="0.9"/>`;
  svgContent += `<text x="${cx}" y="${cy + 3}" text-anchor="middle" fill="rgba(255,255,255,0.6)" font-size="8" font-family="monospace">BAT</text>`;

  svgContent += `<rect x="${cx - 14}" y="${cy + 14}" width="28" height="10" rx="2" fill="url(#compEscGrad)" stroke="rgba(122,90,42,0.6)" stroke-width="0.8" opacity="0.9"/>`;
  svgContent += `<text x="${cx}" y="${cy + 22}" text-anchor="middle" fill="rgba(255,255,255,0.5)" font-size="6" font-family="monospace">ESC</text>`;

  svgContent += `<rect x="${cx - 10}" y="${cy - bodyRy + 4}" width="20" height="12" rx="3" fill="#8a4a8a" stroke="rgba(138,74,138,0.6)" stroke-width="0.8" opacity="0.85"/>`;
  svgContent += `<text x="${cx}" y="${cy - bodyRy + 13}" text-anchor="middle" fill="rgba(255,255,255,0.6)" font-size="5" font-family="monospace">FC</text>`;

  svgContent += `<circle cx="${cx}" cy="${cy - bodyRy - 4}" r="5" fill="#4a6a4a" stroke="rgba(74,106,74,0.8)" stroke-width="0.8"/>`;
  svgContent += `<text x="${cx}" y="${cy - bodyRy - 10}" text-anchor="middle" fill="rgba(255,255,255,0.5)" font-size="5" font-family="monospace">GPS</text>`;

  armPositions.forEach((pos) => {
    svgContent += `<circle cx="${pos.x}" cy="${pos.y}" r="${rotorR}" fill="url(#compRotorGlow)" stroke="rgba(56,243,255,0.3)" stroke-width="1" opacity="0.6"/>`;
    svgContent += `<circle cx="${pos.x}" cy="${pos.y}" r="${rotorR * 0.35}" fill="url(#compMotorGrad)" stroke="rgba(90,106,154,0.6)" stroke-width="1"/>`;
    svgContent += `<text x="${pos.x}" y="${pos.y + 3}" text-anchor="middle" fill="rgba(255,255,255,0.7)" font-size="7" font-family="monospace">${pos.label}</text>`;
  });

  svgContent += `<rect x="${cx - 16}" y="${cy + bodyRy + 2}" width="32" height="14" rx="4" fill="#6a5a3a" stroke="rgba(106,90,58,0.6)" stroke-width="0.8" opacity="0.85"/>`;
  svgContent += `<text x="${cx}" y="${cy + bodyRy + 12}" text-anchor="middle" fill="rgba(255,255,255,0.5)" font-size="6" font-family="monospace">CAM</text>`;

  const lgY = cy + bodyRy + 20;
  svgContent += `<line x1="${cx - 30}" y1="${lgY}" x2="${cx - 30}" y2="${lgY + 16}" stroke="#5a5a5a" stroke-width="3" stroke-linecap="round"/>`;
  svgContent += `<line x1="${cx + 30}" y1="${lgY}" x2="${cx + 30}" y2="${lgY + 16}" stroke="#5a5a5a" stroke-width="3" stroke-linecap="round"/>`;

  svgContent += `<circle cx="${armPositions[0].x}" cy="${armPositions[0].y - rotorR - 4}" r="3" fill="#ffffff" opacity="0.8"/>`;
  svgContent += `<circle cx="${armPositions[1].x}" cy="${armPositions[1].y - rotorR - 4}" r="3" fill="#ffffff" opacity="0.8"/>`;
  svgContent += `<circle cx="${armPositions[2].x}" cy="${armPositions[2].y + rotorR + 4}" r="3" fill="#aa3a3a" opacity="0.8"/>`;
  svgContent += `<circle cx="${armPositions[3].x}" cy="${armPositions[3].y + rotorR + 4}" r="3" fill="#aa3a3a" opacity="0.8"/>`;

  svgContent += `<path d="${`M${cx - bodyRx - 10} ${cy - bodyRy - 6} Q${cx} ${cy - bodyRy - 20} ${cx + bodyRx + 10} ${cy - bodyRy - 6}`}" fill="none" stroke="#6a7aaa" stroke-width="1.5" stroke-dasharray="3,3" opacity="0.5"/>`;

  svgContent += `<ellipse cx="${cx}" cy="${cy + bodyRy + 24}" rx="16" ry="6" fill="none" stroke="#c77dff" stroke-width="1" stroke-dasharray="2,2" opacity="0.6"/>`;
  svgContent += `<text x="${cx}" y="${cy + bodyRy + 36}" text-anchor="middle" fill="rgba(199,125,255,0.6)" font-size="6" font-family="monospace">PAYLOAD</text>`;

  svgContent += `<g class="model-outline" opacity="0.3">`;
  svgContent += `<ellipse cx="${cx}" cy="${cy}" rx="${bodyRx + 4}" ry="${bodyRy + 4}" fill="none" stroke="rgba(56,243,255,0.4)" stroke-width="1"/>`;
  armPositions.forEach((pos) => {
    svgContent += `<circle cx="${pos.x}" cy="${pos.y}" r="${rotorR + 4}" fill="none" stroke="rgba(56,243,255,0.3)" stroke-width="0.8"/>`;
  });
  svgContent += `</g>`;

  group.innerHTML = svgContent;
  svg.hidden = false;
}

function _updateComputeResults(data) {
  const best = data.best;
  if (!best) { return; }

  safeText(getElementById("compScore"), `${data.bestScore} / 100`);
  safeText(getElementById("compBestIter"), `#${data.bestIter + 1} of ${data.records.length}`);
  safeText(getElementById("compPs"), `${best.ps} m/s`);
  safeText(getElementById("compLoadFactor"), `${best.loadFactor} g`);
  safeText(getElementById("compTurnRate"), `${best.turnRateDegS} °/s`);
  safeText(getElementById("compSpecEnergy"), `${best.specificEnergy} J/kg`);
  safeText(getElementById("compMass"), `${best.mass} kg`);
  safeText(getElementById("compWingArea"), `${best.wingArea} m²`);
  safeText(getElementById("compThrust"), `${best.maxThrust} N`);
  safeText(getElementById("compMaxSpeed"), `${best.maxSpeed} m/s`);
  safeText(getElementById("compTWRatio"), `${data.twRatio}`);
  safeText(getElementById("compWingLoad"), `${data.wingLoading} N/m²`);
  safeText(getElementById("compLDRatio"), `${data.ldRatio}`);
  safeText(getElementById("compTestClimb"), best.climbPass ? "✓ Pass" : "✗ Fail");
  safeText(getElementById("compTestSpeed"), best.speedPass ? "✓ Pass" : "✗ Fail");
  safeText(getElementById("compTestTurn"), best.turnPass ? "✓ Pass" : "✗ Fail");
  safeText(getElementById("compTestEndurance"), best.endurancePass ? "✓ Pass" : "✗ Fail");
  safeText(getElementById("computePipeline"), "Complete");
  safeText(getElementById("computeIterations"), String(data.records.length));
  safeText(getElementById("computeConverged"), data.converged ? "Yes" : "No");
  safeText(getElementById("compComponentCount"), String(DRONE_COMPONENTS.length));

  const list = getElementById("computeComponentList");
  if (list) {
    list.innerHTML = "";
    DRONE_COMPONENTS.forEach((comp) => {
      const row = document.createElement("div");
      row.className = "param-row";
      const nameSpan = document.createElement("span");
      nameSpan.textContent = comp.name;
      nameSpan.title = comp.desc;
      const descSpan = document.createElement("span");
      descSpan.textContent = comp.desc.length > 28 ? comp.desc.slice(0, 26) + "…" : comp.desc;
      descSpan.style.color = "var(--text-soft)";
      descSpan.style.fontSize = "11px";
      row.appendChild(nameSpan);
      row.appendChild(descSpan);
      list.appendChild(row);
    });
  }
}

let computeRunning = false;

function runComputeGenerate() {
  if (computeRunning) {
    showNotice("Compute busy", "Generation is already running. Please wait.");
    return;
  }
  computeRunning = true;
  setStatus("COMPUTING", STATUS_COLORS.loading, "warn");
  showNotice("Generating drone…", "Running Design Loop AI + Energy Maneuverability + Aerospace pipeline.");

  const placeholder = getElementById("computePlaceholder");
  const progress = getElementById("computeProgress");
  const progressFill = getElementById("computeProgressFill");
  const progressLabel = getElementById("computeProgressLabel");
  const modelSvg = getElementById("computeModelSvg");

  if (placeholder) { placeholder.hidden = true; }
  if (modelSvg) { modelSvg.hidden = true; }
  if (progress) { progress.hidden = false; }

  const steps = [
    { pct: 10, label: "Initializing vehicle parameters…" },
    { pct: 25, label: "Running Design Loop AI (build → fly → learn)…" },
    { pct: 40, label: "Computing Energy Maneuverability envelope…" },
    { pct: 55, label: "Evaluating aerospace coefficients (lift, drag, T/W)…" },
    { pct: 70, label: "Running flight simulation tests…" },
    { pct: 85, label: "Generating high-fidelity CAD components…" },
    { pct: 95, label: "Assembling drone model…" },
    { pct: 100, label: "Complete" },
  ];

  let stepIdx = 0;

  function advanceStep() {
    if (stepIdx >= steps.length) {
      const data = _simDesignLoop(5);
      _renderDroneModel(data);
      _updateComputeResults(data);
      if (progress) { progress.hidden = true; }
      computeRunning = false;
      setStatus("GENERATED", STATUS_COLORS.ok, "ok");
      showNotice(
        "Drone generated",
        `Design loop converged=${data.converged}, score=${data.bestScore}/100, ${DRONE_COMPONENTS.length} components assembled.`
      );
      return;
    }
    const step = steps[stepIdx];
    if (progressFill) { progressFill.style.width = `${step.pct}%`; }
    if (progressLabel) { progressLabel.textContent = step.label; }
    stepIdx++;
    setTimeout(advanceStep, 400 + Math.random() * 300);
  }

  setTimeout(advanceStep, 200);
}

function clearComputeResults() {
  const placeholder = getElementById("computePlaceholder");
  const progress = getElementById("computeProgress");
  const modelSvg = getElementById("computeModelSvg");
  const group = getElementById("computeModelGroup");
  const list = getElementById("computeComponentList");

  if (placeholder) { placeholder.hidden = false; }
  if (progress) { progress.hidden = true; }
  if (modelSvg) { modelSvg.hidden = true; }
  if (group) { group.innerHTML = ""; }
  if (list) { list.innerHTML = ""; }

  const clearIds = [
    "compScore", "compBestIter", "compPs", "compLoadFactor", "compTurnRate",
    "compSpecEnergy", "compMass", "compWingArea", "compThrust", "compMaxSpeed",
    "compTWRatio", "compWingLoad", "compLDRatio", "compTestClimb", "compTestSpeed",
    "compTestTurn", "compTestEndurance", "computePipeline", "computeIterations",
    "computeConverged", "compComponentCount",
  ];
  clearIds.forEach((id) => safeText(getElementById(id), "—"));
  safeText(getElementById("computePipeline"), "Idle");
  safeText(getElementById("compComponentCount"), "0");

  computeRunning = false;
  setStatus("READY", STATUS_COLORS.ready, "ok");
  showNotice("Compute cleared", "Computation results have been reset.");
}

function init() {
  try {
    notice = document.getElementById("notice");
    statusPill = document.getElementById("statusPill");
    selfTestPill = document.getElementById("selfTestPill");
    clockPill = document.getElementById("clockPill");
    modePill = document.getElementById("modePill");
    schemaPill = document.getElementById("schemaPill");
    payloadPill = document.getElementById("payloadPill");
    tripwireBanner = document.getElementById("tripwireBanner");
    jsonFileInput = document.getElementById("jsonFileInput");
    if (jsonFileInput) {
      jsonFileInput.addEventListener("change", () => {
        const file = jsonFileInput.files?.[0];
        if (!file) {
          return;
        }
        const reader = new FileReader();
        reader.onload = () => {
          try {
            const parsed = JSON.parse(String(reader.result || ""));
            currentPayload = parsed;
            safeText(payloadPill, `PAYLOAD: ${file.name}`);
            const schemaLabel = parsed?.schema ? String(parsed.schema) : "(unknown)";
            safeText(schemaPill, `SCHEMA: ${schemaLabel}`);
            updateCadInspector(parsed);
            showNotice("JSON loaded", `Loaded ${file.name}`);
            setStatus("LOADED", STATUS_COLORS.ok, "ok");
          } catch (error) {
            showNotice("JSON parse failed", "Unable to parse the selected file as JSON.");
            setStatus("FAIL", STATUS_COLORS.fail, "fail");
          }
        };
        reader.onerror = () => {
          showNotice("JSON load failed", "Unable to read file.");
          setStatus("FAIL", STATUS_COLORS.fail, "fail");
        };
        reader.readAsText(file);
      });
    }
    const workspaceState = loadWorkspaceState();
    activeWorkspaceId = workspaceState.activeId || workspaceState.tabs[0]?.id || "ws-1";
    renderWorkspaces(workspaceState.tabs);
    const initialTab = getInitialTab();
    setActiveTab(initialTab, false);
    updateClock();
    clockIntervalId = setInterval(updateClock, 1000);
    attachHandlers();
    initCadViewport();
    updateCadInspector(currentPayload);
    setStatus("READY", STATUS_COLORS.ready, "ok");
    renderSelfTest();
    runTripwires();
  } catch (error) {
    console.error("Dashboard init failed", error);
    handleGlobalError(error.message || error);
  }
}

window.addEventListener("DOMContentLoaded", init);

window.addEventListener("beforeunload", () => {
  if (clockIntervalId) {
    clearInterval(clockIntervalId);
  }
});
