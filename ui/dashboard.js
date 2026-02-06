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
const TAB_OPTIONS = ["cad", "sim", "insights"];
const TAB_MODE_LABELS = {
  cad: "CAD",
  sim: "SIM",
  insights: "INSIGHTS"
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
  const time = now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
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
        showNotice("Validator not wired yet", "Hook up validateDashboardPayload() to enable validation.");
      }
    });
  }

  if (btnHelp) {
    btnHelp.addEventListener("click", () => {
      setStatus("INFO", STATUS_COLORS.info, "info");
      showNotice(
        "Local run tips",
        "Serve the ui folder with a simple HTTP server (e.g. 'python -m http.server') and open /dashboard.html."
      );
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
  const now = new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const message = `UI loaded · ${now} · Menu: ${hasMenu ? "YES" : "NO"} · Task: ${hasTask ? "YES" : "NO"}`;
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
  const currentTab = document.querySelector("[data-tab].active")?.dataset.tab || getInitialTab();
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
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
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
