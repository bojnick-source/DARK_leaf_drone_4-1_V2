// ui/dashboard.js — PRIME-GRADE V4 (OVER-100 / HARDENED / WATCHDOG + PERSISTENCE + PERF + MENU KEYBOARD)
// Works with: ui/dashboard.html V9 + ui/dashboard.css V2
//
// V4 adds (best-in-class polish):
// ✅ Render Watchdog Tripwire: detects “blank/zero-size/collapsed” UI regions + explains likely cause
// ✅ State Persistence: workspace list, active workspace, mode, and UI version stamp in localStorage; safe restore
// ✅ Performance Marks: boot/schema/validation timers exported in diagnostics
// ✅ Menu Keyboard Nav: ArrowLeft/Right moves top menus; Up/Down cycles menuitems; Enter activates; Esc closes
// ✅ Maintains V3: popup edge flip/shift + schema fetch + practical validation + fail-loud + proof export

(() => {
  "use strict";

  /* =========================
     0) Utilities + Diagnostics
     ========================= */
  const STORAGE_KEY = "darkleaf.ui.daily_dashboard.state.v1";
  const SCHEMA_URL = "./schemas/engine_output.schema.json";
  const VALIDATION_MAX_DEPTH = 4;
  const VALIDATION_MAX_ARRAY = 50;

  const DIAG = {
    startedAt: isoNow(),
    errors: /** @type {Array<{time:string,type:string,message:string,stack?:string}>} */ ([]),
    selfTest: /** @type {null | { ok:boolean, checks:Array<{name:string, ok:boolean, detail?:string}> }} */ (null),
    schema: /** @type {null | { loaded:boolean, source:string, id?:string, title?:string, versionHint?:string, raw?:any, error?:string }} */ (null),
    lastValidation: /** @type {null | { ok:boolean, summary:string, missing:string[], typeErrors:Array<{path:string, expected:string, actual:string}> }} */ (null),
    perf: /** @type {Record<string, number>} */ ({}),
    watchdog: /** @type {null | { ok:boolean, checks:Array<{name:string, ok:boolean, detail?:string}> }} */ (null),
    env: /** @type {Record<string,string>} */ ({}),
    version: "dashboard.js@V4",
  };

  function isoNow() {
    try { return new Date().toISOString(); } catch { return "unknown-time"; }
  }

  function perfMark(name) {
    try { performance.mark(name); } catch {}
  }
  function perfMeasure(name, start, end) {
    try {
      performance.measure(name, start, end);
      const entries = performance.getEntriesByName(name);
      const last = entries[entries.length - 1];
      if (last && typeof last.duration === "number") DIAG.perf[name] = Number(last.duration.toFixed(2));
    } catch {}
  }

  /** @param {unknown} x */
  function isEl(x) { return x instanceof HTMLElement; }

  /** @param {string} msg */
  function invariant(msg) {
    const err = new Error(msg);
    err.name = "InvariantViolation";
    return err;
  }

  /** @param {unknown} s */
  function safeText(s) {
    return String(s ?? "").replace(/\s+/g, " ").trim();
  }

  /** @param {string} id @returns {HTMLElement} */
  function mustId(id) {
    const el = document.getElementById(id);
    if (!isEl(el)) throw invariant(`Missing required element #${id}`);
    return el;
  }

  /** @param {string} type @param {unknown} err */
  function recordError(type, err) {
    const e = err instanceof Error ? err : new Error(String(err));
    DIAG.errors.push({
      time: isoNow(),
      type,
      message: e.message || String(err),
      stack: e.stack || "",
    });
  }

  function setHidden(el, on) {
    if (on) el.setAttribute("hidden", "");
    else el.removeAttribute("hidden");
  }

  function setText(el, txt) { el.textContent = String(txt ?? ""); }

  function toggleClass(el, cls, on) {
    if (on) el.classList.add(cls);
    else el.classList.remove(cls);
  }

  function isPlainObject(v) {
    return typeof v === "object" && v !== null && !Array.isArray(v);
  }

  function tryJsonParse(s) {
    try { return JSON.parse(String(s)); } catch { return null; }
  }

  function storeState(state) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
      recordError("storage.write", e);
    }
  }

  function loadState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      return tryJsonParse(raw);
    } catch (e) {
      recordError("storage.read", e);
      return null;
    }
  }

  function clearState() {
    try { localStorage.removeItem(STORAGE_KEY); } catch {}
  }

  /* =========================
     1) Required elements
     ========================= */
  const fatalBanner = mustId("fatalBanner");
  const srAnnounce = mustId("srAnnounce");
  const toastRegion = mustId("toastRegion");
  const bootStatus = mustId("bootStatus");
  const bootBody =
    /** @type {HTMLElement} */ (bootStatus.querySelector(".bootBody")) || bootStatus;

  const chromeTabs = mustId("chromeTabs");
  const tplWorkspaceTab = /** @type {HTMLTemplateElement} */ (mustId("tplWorkspaceTab"));

  const menuBar = mustId("menuBar");
  const filePicker = /** @type {HTMLInputElement} */ (mustId("filePicker"));

  const btnNewWorkspace = /** @type {HTMLButtonElement} */ (mustId("btnNewWorkspace"));
  const btnResetLayout = /** @type {HTMLButtonElement} */ (mustId("btnResetLayout"));

  const btnSelfTest = /** @type {HTMLButtonElement} */ (mustId("btnSelfTest"));
  const btnExportDiag = /** @type {HTMLButtonElement} */ (mustId("btnExportDiag"));

  const diagnosticsDump = mustId("diagnosticsDump");
  const insights3d = /** @type {HTMLElement} */ (mustId("insights3d"));
  const appShell = mustId("appShell");

  // Taskbar pills
  const modePill = mustId("modePill");
  const schemaPill = mustId("schemaPill");
  const validationPill = mustId("validationPill");
  const runStatePill = mustId("runStatePill");
  const healthPill = mustId("healthPill");
  const statusPill = mustId("statusPill");
  const clockPill = mustId("clockPill");
  const menuContextChip = mustId("menuContextChip");

  // Watchdog critical regions
  const chromeStrip = mustId("chromeStrip");
  const cadToolbar = mustId("cadToolbar");
  const subTabStrip = mustId("subTabStrip");
  const taskBar = mustId("taskBar");
  const plotIds = ["plotScatter3d", "plotSurface3d", "plotTrajectory3d"];
  const plots = Object.fromEntries(plotIds.map((id) => [id, mustId(id)]));

  /* =========================
     2) Fail-loud + announcements
     ========================= */
  function showFatal(title, details) {
    try {
      setHidden(fatalBanner, false);
      fatalBanner.innerHTML = "";

      const h = document.createElement("div");
      h.className = "fatalTitle";
      h.textContent = safeText(title) || "Fatal UI Error";

      const p = document.createElement("pre");
      p.className = "fatalDetail";
      p.textContent = String(details ?? "");

      fatalBanner.appendChild(h);
      fatalBanner.appendChild(p);

      srAnnounce.textContent = `Error: ${safeText(title)}`;
      toastRegion.textContent = `Error: ${safeText(title)}`;

      writeDiagnosticsDump();
    } catch {
      // last resort: no-op
    }
  }

  function announce(msg) { srAnnounce.textContent = safeText(msg); }
  function toast(msg) { toastRegion.textContent = safeText(msg); }

  /* =========================
     3) Boot status helper
     ========================= */
  function setBootLine(label, value) {
    const key = `boot-${label.toLowerCase()}`;
    let line = bootBody.querySelector(`[data-boot="${CSS.escape(key)}"]`);
    if (!(line instanceof HTMLElement)) {
      line = document.createElement("div");
      line.setAttribute("data-boot", key);
      bootBody.appendChild(line);
    }
    line.innerHTML = `<strong>${label}:</strong> ${safeText(value)}`;
  }

  function detectCssLoaded() {
    try {
      const sheets = Array.from(document.styleSheets);
      const found = sheets.some((s) => {
        const href = /** @type {any} */ (s).href;
        return typeof href === "string" && href.includes("dashboard.css");
      });
      return found ? "loaded" : "unknown";
    } catch {
      return "unknown";
    }
  }

  /* =========================
     4) Progressive enhancement + quality lock
     ========================= */
  function markJsEnabled() {
    const html = document.documentElement;
    html.classList.remove("no-js");
    html.classList.add("js");
    document.body.dataset.uiState = "running";
  }

  /* =========================
     5) Menu system (robust + edge flip + keyboard nav)
     ========================= */
  const menuGroups = /** @type {HTMLElement[]} */ (
    Array.from(menuBar.querySelectorAll(".menuGroup"))
  );

  /** @type {null | { index:number, btn: HTMLButtonElement, popup: HTMLElement }} */
  let openMenu = null;

  function resetPopupPlacement(popup) {
    popup.style.left = "";
    popup.style.right = "";
    popup.style.maxHeight = "";
  }

  function placePopupWithinViewport(btn, popup) {
    try {
      resetPopupPlacement(popup);

      const pr = popup.getBoundingClientRect();
      const br = btn.getBoundingClientRect();
      const vw = Math.max(document.documentElement.clientWidth, window.innerWidth || 0);
      const vh = Math.max(document.documentElement.clientHeight, window.innerHeight || 0);
      const pad = 10;

      if (pr.right > vw - pad) {
        popup.style.left = "auto";
        popup.style.right = "0";
      }

      const pr2 = popup.getBoundingClientRect();

      if (pr2.bottom > vh - pad) {
        const available = Math.max(120, (vh - pad) - pr2.top);
        popup.style.maxHeight = `${available}px`;
      }

      if (pr2.top < pad) {
        popup.style.maxHeight = `${Math.max(120, vh - pad - (br.bottom + 6))}px`;
      }
    } catch {}
  }

  function closeMenu(reason = "") {
    if (!openMenu) return;
    const { btn, popup } = openMenu;
    btn.setAttribute("aria-expanded", "false");
    popup.classList.remove("open");
    resetPopupPlacement(popup);
    openMenu = null;
    if (reason) toast(reason);
    try { btn.focus(); } catch {}
  }

  function openMenuFor(index, btn, popup) {
    if (openMenu) closeMenu();
    btn.setAttribute("aria-expanded", "true");
    popup.classList.add("open");
    openMenu = { index, btn, popup };
    requestAnimationFrame(() => placePopupWithinViewport(btn, popup));
  }

  function getMenuTripletAt(index) {
    const g = menuGroups[index];
    if (!g) return null;
    const btn = g.querySelector(".menuBtn");
    const popup = g.querySelector(".menuPopup");
    if (!(btn instanceof HTMLButtonElement)) return null;
    if (!(popup instanceof HTMLElement)) return null;
    return { index, btn, popup };
  }

  function menuItems(popup) {
    return /** @type {HTMLElement[]} */ (
      Array.from(popup.querySelectorAll('[role="menuitem"]')).filter((x) => x instanceof HTMLElement)
    );
  }

  function focusMenuItem(popup, idx) {
    const items = menuItems(popup);
    const clamped = Math.max(0, Math.min(items.length - 1, idx));
    const it = items[clamped];
    if (it) {
      it.tabIndex = 0;
      try { it.focus(); } catch {}
    }
  }

  function wireMenus() {
    for (let i = 0; i < menuGroups.length; i++) {
      const trip = getMenuTripletAt(i);
      if (!trip) continue;
      const { btn, popup } = trip;

      btn.addEventListener("click", (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        const expanded = btn.getAttribute("aria-expanded") === "true";
        if (expanded) closeMenu();
        else openMenuFor(i, btn, popup);
      });

      popup.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const t = ev.target;
        if (!(t instanceof HTMLElement)) return;
        const item = t.closest('[role="menuitem"]');
        if (!(item instanceof HTMLElement)) return;
        const action = item.getAttribute("data-action") || "";
        if (action) dispatchAction(action);
        closeMenu();
      });

      popup.addEventListener("keydown", (ev) => {
        if (!openMenu) return;
        const items = menuItems(openMenu.popup);
        if (items.length === 0) return;

        const focusedIdx = items.findIndex((x) => x === document.activeElement);
        if (ev.key === "ArrowDown") {
          ev.preventDefault();
          focusMenuItem(openMenu.popup, (focusedIdx < 0 ? 0 : focusedIdx + 1));
        } else if (ev.key === "ArrowUp") {
          ev.preventDefault();
          focusMenuItem(openMenu.popup, (focusedIdx < 0 ? items.length - 1 : focusedIdx - 1));
        } else if (ev.key === "Enter") {
          ev.preventDefault();
          const el = document.activeElement;
          if (el instanceof HTMLElement) {
            const action = el.getAttribute("data-action") || "";
            if (action) dispatchAction(action);
            closeMenu();
          }
        } else if (ev.key === "Escape") {
          ev.preventDefault();
          closeMenu("Menu closed");
        }
      });
    }

    window.addEventListener("resize", () => {
      if (openMenu) placePopupWithinViewport(openMenu.btn, openMenu.popup);
    });

    document.addEventListener("click", () => closeMenu());
  }

  function wireMenuKeyboardNav() {
    // When a menu is open, ArrowLeft/Right changes the top menu
    document.addEventListener("keydown", (ev) => {
      if (!openMenu) return;

      if (ev.key === "ArrowRight" || ev.key === "ArrowLeft") {
        ev.preventDefault();
        const dir = ev.key === "ArrowRight" ? 1 : -1;
        const nextIdx = (openMenu.index + dir + menuGroups.length) % menuGroups.length;
        const next = getMenuTripletAt(nextIdx);
        if (!next) return;
        openMenuFor(next.index, next.btn, next.popup);
        // focus first item
        requestAnimationFrame(() => focusMenuItem(next.popup, 0));
      } else if (ev.key === "Escape") {
        ev.preventDefault();
        closeMenu("Menu closed");
      }
    });
  }

  /* =========================
     6) Global action dispatcher
     ========================= */
  function wireActionDelegation() {
    document.addEventListener("click", (ev) => {
      const t = ev.target;
      if (!(t instanceof HTMLElement)) return;
      const el = t.closest("[data-action]");
      if (!(el instanceof HTMLElement)) return;
      const action = el.getAttribute("data-action");
      if (!action) return;
      ev.preventDefault();
      dispatchAction(action);
    });

    document.addEventListener("keydown", (ev) => {
      const ae = document.activeElement;
      if (ae && (ae.tagName === "INPUT" || ae.tagName === "TEXTAREA")) return;

      const isMeta = ev.metaKey || ev.ctrlKey;
      if (!isMeta) return;

      const k = ev.key.toLowerCase();
      if (k === "o") {
        ev.preventDefault();
        dispatchAction("json.open");
      } else if (k === "d") {
        ev.preventDefault();
        dispatchAction("export.diag");
      } else if (k === "w") {
        ev.preventDefault();
        dispatchAction("workspace.close");
      } else if (k === "r") {
        ev.preventDefault();
        dispatchAction("layout.reset");
      }
    });
  }

  /* =========================
     7) Workspace tabs + persistence
     ========================= */
  /** @type {{id:string,title:string}[]} */
  let workspaces = [{ id: "ws-0", title: "Daily Dashboard" }];
  let activeWorkspaceId = "ws-0";

  function genId() {
    return `ws-${Math.random().toString(16).slice(2)}-${Date.now().toString(16)}`;
  }

  function clearFallbackNodes() {
    const fallbacks = chromeTabs.querySelectorAll('[data-fallback="true"]');
    for (const n of fallbacks) n.remove();
  }

  function getActiveWorkspaceTitle() {
    return workspaces.find((w) => w.id === activeWorkspaceId)?.title || "—";
  }

  function updateMenuContextChip() {
    setText(menuContextChip, `Workspace: ${getActiveWorkspaceTitle()}`);
  }

  function persistState() {
    storeState({
      version: document.documentElement.dataset.uiVersion || "",
      savedAt: isoNow(),
      activeMode,
      activeWorkspaceId,
      workspaces,
    });
  }

  function restoreState() {
    const s = loadState();
    if (!s || !isPlainObject(s)) return false;

    // Safe restore: only accept sane shapes
    const ws = Array.isArray(s.workspaces) ? s.workspaces : null;
    const am = typeof s.activeMode === "string" ? s.activeMode : null;
    const aw = typeof s.activeWorkspaceId === "string" ? s.activeWorkspaceId : null;

    if (ws && ws.length >= 1 && ws.every((x) => isPlainObject(x) && typeof x.id === "string" && typeof x.title === "string")) {
      workspaces = ws.slice(0, 20).map((x) => ({ id: x.id, title: x.title }));
      if (aw && workspaces.some((w) => w.id === aw)) activeWorkspaceId = aw;
      else activeWorkspaceId = workspaces[0].id;
    }

    if (am) setMode(am);

    return true;
  }

  function setActiveWorkspace(id, msg = "") {
    if (!workspaces.some((w) => w.id === id)) return;
    activeWorkspaceId = id;
    renderWorkspaceTabs();
    updateMenuContextChip();
    persistState();
    if (msg) toast(msg);
    announce(`Workspace: ${getActiveWorkspaceTitle()}`);
  }

  function closeWorkspace(id) {
    if (workspaces.length <= 1) {
      toast("Cannot close last workspace");
      return;
    }
    const idx = workspaces.findIndex((w) => w.id === id);
    if (idx < 0) return;
    workspaces.splice(idx, 1);

    if (activeWorkspaceId === id) {
      const next = workspaces[Math.min(idx, workspaces.length - 1)];
      activeWorkspaceId = next.id;
    }
    renderWorkspaceTabs();
    updateMenuContextChip();
    persistState();
    toast("Workspace closed");
  }

  function newWorkspace() {
    const ws = { id: genId(), title: `Workspace ${workspaces.length + 1}` };
    workspaces.push(ws);
    setActiveWorkspace(ws.id, "Workspace created");
  }

  function focusActiveTab() {
    const active = chromeTabs.querySelector(`.wsTab[data-wsid="${CSS.escape(activeWorkspaceId)}"]`);
    if (active instanceof HTMLElement) {
      try { active.focus(); } catch {}
    }
  }

  function renderWorkspaceTabs() {
    clearFallbackNodes();

    const existing = chromeTabs.querySelectorAll(".wsTab");
    for (const e of existing) e.remove();

    const base = 1000;

    workspaces.forEach((ws, index) => {
      const frag = tplWorkspaceTab.content.cloneNode(true);
      const tab = /** @type {HTMLElement} */ (frag.querySelector(".wsTab"));
      if (!tab) throw invariant("tplWorkspaceTab missing .wsTab root");

      tab.setAttribute("data-wsid", ws.id);
      tab.setAttribute("data-index", String(index));
      tab.setAttribute("title", ws.title);

      const title = tab.querySelector(".wsTitle");
      if (!(title instanceof HTMLElement)) throw invariant("tplWorkspaceTab missing .wsTitle");
      title.textContent = ws.title;

      const closeBtn = tab.querySelector(".wsClose");
      if (!(closeBtn instanceof HTMLElement)) throw invariant("tplWorkspaceTab missing .wsClose");

      const isActive = ws.id === activeWorkspaceId;
      tab.setAttribute("aria-selected", isActive ? "true" : "false");
      tab.tabIndex = isActive ? 0 : -1;
      toggleClass(tab, "active", isActive);

      tab.style.zIndex = String(isActive ? base + 50 : base - index);

      tab.addEventListener("click", (ev) => {
        const t = ev.target;
        if (t instanceof HTMLElement && t.closest(".wsClose")) return;
        setActiveWorkspace(ws.id, "Workspace switched");
      });

      closeBtn.addEventListener("click", (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        closeWorkspace(ws.id);
      });

      chromeTabs.appendChild(frag);
    });
  }

  function wireWorkspaceShortcuts() {
    document.addEventListener("keydown", (ev) => {
      const ae = document.activeElement;
      if (ae && (ae.tagName === "INPUT" || ae.tagName === "TEXTAREA")) return;

      const isMeta = ev.metaKey || ev.ctrlKey;
      if (!isMeta) return;

      if (ev.key === "Tab") {
        ev.preventDefault();
        const dir = ev.shiftKey ? -1 : 1;
        const idx = workspaces.findIndex((w) => w.id === activeWorkspaceId);
        const nextIdx = (idx + dir + workspaces.length) % workspaces.length;
        setActiveWorkspace(workspaces[nextIdx].id, "Workspace cycled");
      }

      if ((ev.key === "n" || ev.key === "N") && !ev.shiftKey && !ev.altKey) {
        ev.preventDefault();
        newWorkspace();
      }
    });

    chromeTabs.addEventListener("keydown", (ev) => {
      const focused = document.activeElement;
      if (!(focused instanceof HTMLElement)) return;
      const currentTab = focused.closest(".wsTab");
      if (!(currentTab instanceof HTMLElement)) return;

      const idx = Number(currentTab.getAttribute("data-index") || "0");
      if (ev.key === "ArrowRight") {
        ev.preventDefault();
        const next = workspaces[Math.min(idx + 1, workspaces.length - 1)];
        setActiveWorkspace(next.id);
        focusActiveTab();
      } else if (ev.key === "ArrowLeft") {
        ev.preventDefault();
        const prev = workspaces[Math.max(idx - 1, 0)];
        setActiveWorkspace(prev.id);
        focusActiveTab();
      } else if (ev.key === "Home") {
        ev.preventDefault();
        setActiveWorkspace(workspaces[0].id);
        focusActiveTab();
      } else if (ev.key === "End") {
        ev.preventDefault();
        setActiveWorkspace(workspaces[workspaces.length - 1].id);
        focusActiveTab();
      }
    });
  }

  /* =========================
     8) Status pills + mode
     ========================= */
  const MODE_INSIGHTS = "INSIGHTS";
  let activeMode = "CAD";

  function setMode(mode) {
    activeMode = String(mode || "CAD").toUpperCase();
    setText(modePill, `MODE: ${activeMode}`);
    persistState();
    updateInsightsVisibility();
  }

  function setSchemaVersion(v) {
    setText(schemaPill, `SCHEMA: ${safeText(v) || "—"}`);
  }

  function setValidation(ok, detail = "") {
    setText(validationPill, ok ? "VALIDATION: PASS" : "VALIDATION: FAIL");
    setText(healthPill, ok ? "HEALTH: HIGH" : "HEALTH: LOW");
    if (detail) toast(detail);
  }

  function setRunState(s) {
    setText(runStatePill, `RUN STATE: ${safeText(s) || "IDLE"}`);
  }

  function setStatus(s) {
    setText(statusPill, `STATUS: ${safeText(s) || "READY"}`);
  }

  function startClock() {
    const tick = () => {
      try {
        const d = new Date();
        const hh = String(d.getHours()).padStart(2, "0");
        const mm = String(d.getMinutes()).padStart(2, "0");
        setText(clockPill, `TIME: ${hh}:${mm}`);
      } catch {}
    };
    tick();
    setInterval(tick, 10_000);
  }

  /* =========================
     9) Subtabs
     ========================= */
  const subTabs = /** @type {HTMLButtonElement[]} */ (
    Array.from(subTabStrip.querySelectorAll(".subTab")).filter((b) => b instanceof HTMLButtonElement)
  );

  function wireSubTabs() {
    subTabs.forEach((btn) => {
      btn.addEventListener("click", () => {
        const mode = btn.getAttribute("data-subtab") || "cad";
        setMode(mode);
        subTabs.forEach((x) => x.classList.toggle("active", x === btn));
        toast(`Mode: ${mode.toUpperCase()}`);
      });
    });

    // initial active state aligns with current activeMode
    const first = subTabs[0];
    if (first) first.classList.add("active");
    if (!activeMode) setMode("CAD");
    updateInsightsVisibility();
  }

  /* =========================
     9.5) INSIGHTS 3D (Plotly)
     ========================= */
  let insightsRendered = false;
  let sampleLoaded = false;
  let engineDataLoaded = false;
  let insightsResizeWired = false;

  function updateInsightsVisibility() {
    const show = activeMode === MODE_INSIGHTS;
    insights3d.hidden = !show;
    toggleClass(appShell, "mode-insights", show);
    const appGrid = document.getElementById("app");
    if (appGrid instanceof HTMLElement) appGrid.hidden = show;
    if (show) renderInsights3d();
  }

  function renderInsights3d() {
    if (!window.Plotly) {
      showInsightsFallback("Plotly unavailable");
      return;
    }
    hideInsightsFallbacks();
    if (insightsRendered) {
      resizeInsights();
      return;
    }
    const data = sampleLoaded ? sampleData() : emptyData();
    requestAnimationFrame(() => {
      Plotly.react(plots.plotScatter3d, data.scatter, plotLayout("Scatter 3D"), plotConfig());
      Plotly.react(plots.plotSurface3d, data.surface, plotLayout("Surface 3D"), plotConfig());
      Plotly.react(plots.plotTrajectory3d, data.trajectory, plotLayout("Trajectory 3D"), plotConfig());
      insightsRendered = true;
      wirePlotResizes();
      resizeInsights();
    });
  }

  function showInsightsFallback(reason) {
    plotIds.forEach((id) => {
      const fallback = document.querySelector(`[data-fallback="${id}"]`);
      if (fallback instanceof HTMLElement) {
        fallback.textContent = `3D unavailable: ${reason} (CDN blocked)`;
        fallback.hidden = false;
      }
    });
  }

  function hideInsightsFallbacks() {
    plotIds.forEach((id) => {
      const fallback = document.querySelector(`[data-fallback="${id}"]`);
      if (fallback instanceof HTMLElement) {
        fallback.hidden = true;
      }
    });
  }

  function plotLayout(title) {
    return {
      title: { text: title, font: { size: 14 } },
      margin: { l: 0, r: 0, t: 36, b: 0 },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      showlegend: true,
      scene: {
        xaxis: { title: "X", showgrid: true, zeroline: false },
        yaxis: { title: "Y", showgrid: true, zeroline: false },
        zaxis: { title: "Z", showgrid: true, zeroline: false },
      },
    };
  }

  function plotConfig() {
    return { responsive: true, displaylogo: false, modeBarButtonsToRemove: ["toImage"] };
  }

  function emptyData() {
    return {
      scatter: [{ type: "scatter3d", mode: "markers", name: "Points", x: [0], y: [0], z: [0], marker: { size: 3 } }],
      surface: [{ type: "surface", name: "Surface", z: [[0, 0], [0, 0]], showscale: false, showlegend: true }],
      trajectory: [{ type: "scatter3d", mode: "lines", name: "Path", x: [0], y: [0], z: [0], line: { width: 3 } }],
    };
  }

  function sampleData() {
    const pts = [];
    for (let i = 0; i < 60; i++) {
      pts.push([Math.sin(i / 6) * 5, Math.cos(i / 8) * 5, Math.sin(i / 4) * 3]);
    }
    const grid = [];
    for (let y = -5; y <= 5; y++) {
      const row = [];
      for (let x = -5; x <= 5; x++) {
        row.push(Math.sin(x / 2) * Math.cos(y / 2));
      }
      grid.push(row);
    }
    return {
      scatter: [{
        type: "scatter3d",
        mode: "markers",
        name: "Points",
        x: pts.map((p) => p[0]),
        y: pts.map((p) => p[1]),
        z: pts.map((p) => p[2]),
        marker: { size: 3, color: pts.map((p) => p[2]), colorscale: "Viridis" },
      }],
      surface: [{ type: "surface", name: "Surface", z: grid, colorscale: "Ice", showscale: false, showlegend: true }],
      trajectory: [{
        type: "scatter3d",
        mode: "lines",
        name: "Path",
        x: pts.map((p) => p[0]),
        y: pts.map((p) => p[1]),
        z: pts.map((p) => p[2]),
        line: { width: 4, color: "rgba(80,140,255,0.9)" },
      }],
    };
  }

  function resizeInsights() {
    if (!window.Plotly) return;
    plotIds.forEach((id) => Plotly.relayout(plots[id], {}));
  }

  function wirePlotResizes() {
    if (insightsResizeWired) return;
    insightsResizeWired = true;
    let resizeHandle = null;
    window.addEventListener("resize", () => {
      if (resizeHandle) cancelAnimationFrame(resizeHandle);
      resizeHandle = requestAnimationFrame(() => {
        resizeInsights();
        resizeHandle = null;
      });
    });
  }

  function wirePlotExports() {
    document.querySelectorAll("[data-export]").forEach((btn) => {
      if (!(btn instanceof HTMLButtonElement)) return;
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-export") || "";
        if (!window.Plotly || !plots[id]) return;
        Plotly.downloadImage(plots[id], { format: "png", filename: id });
      });
    });
  }

  function applyInsightsSample() {
    if (engineDataLoaded) {
      toast("Engine data loaded; sample not applied");
      return;
    }
    sampleLoaded = true;
    insightsRendered = false;
    renderInsights3d();
    toast("Loaded sample insights");
  }

  function wireInsightsSample() {
    document.querySelectorAll("[data-action=\"insights.sample\"]").forEach((btn) => {
      if (!(btn instanceof HTMLButtonElement)) return;
      btn.addEventListener("click", () => {
        applyInsightsSample();
      });
    });
  }

  function applyInsightsFromData(data) {
    if (!window.Plotly) {
      showInsightsFallback("Plotly unavailable");
      return;
    }
    hideInsightsFallbacks();
    const scatter = data?.insights?.scatter3d;
    const surface = data?.insights?.surface3d;
    const trajectory = data?.insights?.trajectory3d;
    if (!scatter && !surface && !trajectory) {
      toast("Insights data missing; using existing visuals");
      return;
    }
    const scatterTrace = scatter ? [{
      type: "scatter3d",
      mode: "markers",
      name: "Points",
      x: scatter.x || [],
      y: scatter.y || [],
      z: scatter.z || [],
      marker: { size: 3, color: scatter.z || [], colorscale: "Viridis" },
    }] : emptyData().scatter;

    const surfaceTrace = surface ? [{
      type: "surface",
      name: "Surface",
      z: surface.z || [[0]],
      colorscale: "Ice",
      showscale: false,
      showlegend: true,
    }] : emptyData().surface;

    const trajectoryTrace = trajectory ? [{
      type: "scatter3d",
      mode: "lines",
      name: "Path",
      x: trajectory.x || [],
      y: trajectory.y || [],
      z: trajectory.z || [],
      line: { width: 4, color: "rgba(80,140,255,0.9)" },
    }] : emptyData().trajectory;

    Plotly.react(plots.plotScatter3d, scatterTrace, plotLayout("Scatter 3D"), plotConfig());
    Plotly.react(plots.plotSurface3d, surfaceTrace, plotLayout("Surface 3D"), plotConfig());
    Plotly.react(plots.plotTrajectory3d, trajectoryTrace, plotLayout("Trajectory 3D"), plotConfig());
    insightsRendered = true;
    wirePlotResizes();
    resizeInsights();
  }

  /* =========================
     10) Diagnostics
     ========================= */
  function gatherEnv() {
    DIAG.env = {
      userAgent: navigator.userAgent || "",
      platform: navigator.platform || "",
      language: navigator.language || "",
      href: location.href || "",
      startedAt: DIAG.startedAt,
      now: isoNow(),
      uiVersion: document.documentElement.dataset.uiVersion || "",
      buildId: document.querySelector('meta[name="build-id"]')?.getAttribute("content") || "",
      jsVersion: DIAG.version,
      cssDetected: detectCssLoaded(),
    };
  }

  function writeDiagnosticsDump() {
    try {
      gatherEnv();
      const payload = {
        env: DIAG.env,
        perf: DIAG.perf,
        errors: DIAG.errors.slice(-50),
        schema: DIAG.schema,
        lastValidation: DIAG.lastValidation,
        watchdog: DIAG.watchdog,
        selfTest: DIAG.selfTest,
        workspace: { activeMode, activeWorkspaceId, workspaces },
      };
      diagnosticsDump.textContent = JSON.stringify(payload, null, 2);
    } catch {}
  }

  function exportDiagnostics() {
    try {
      writeDiagnosticsDump();
      const text = diagnosticsDump.textContent || "{}";
      const blob = new Blob([text], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `ui_diagnostics_${Date.now()}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      toast("Diagnostics exported");
      announce("Diagnostics exported");
      setTimeout(() => {
        try { URL.revokeObjectURL(a.href); } catch {}
      }, 2000);
    } catch (e) {
      recordError("export.diag", e);
      showFatal("Diagnostics Export Failed", e instanceof Error ? e.message : String(e));
    }
  }

  /* =========================
     11) Schema fetch + practical validator
     ========================= */
  function schemaVersionHint(schema) {
    if (!schema || typeof schema !== "object") return "";
    const id = schema.$id || schema.id || "";
    const title = schema.title || "";
    const v = schema.version || schema.schema_version || schema.schemaVersion || "";
    return safeText(v || title || id || "—");
  }

  async function loadSchema() {
    DIAG.schema = { loaded: false, source: SCHEMA_URL };
    perfMark("schema:start");
    try {
      if (location.protocol === "file:") {
        const msg =
          "Schema fetch blocked on file://. Run a local server (python3 -m http.server) so ./schemas/… can load.";
        DIAG.schema.error = msg;
        setBootLine("Schema", "blocked (file://)");
        setSchemaVersion("—");
        return;
      }

      const res = await fetch(SCHEMA_URL, { cache: "no-store" });
      if (!res.ok) throw new Error(`Schema fetch failed: ${res.status} ${res.statusText}`);
      const schema = await res.json();

      DIAG.schema = {
        loaded: true,
        source: SCHEMA_URL,
        id: safeText(schema?.$id || schema?.id || ""),
        title: safeText(schema?.title || ""),
        versionHint: schemaVersionHint(schema),
        raw: schema,
      };

      setBootLine("Schema", "loaded");
      setSchemaVersion(DIAG.schema.versionHint || "loaded");
    } catch (e) {
      recordError("schema.load", e);
      DIAG.schema = {
        loaded: false,
        source: SCHEMA_URL,
        error: e instanceof Error ? e.message : String(e),
      };
      setBootLine("Schema", "failed");
      setSchemaVersion("—");
    } finally {
      perfMark("schema:end");
      perfMeasure("schema.load.ms", "schema:start", "schema:end");
      writeDiagnosticsDump();
    }
  }

  function typeOfJson(v) {
    if (v === null) return "null";
    if (Array.isArray(v)) return "array";
    return typeof v;
  }

  function matchesType(expected, value) {
    const actual = typeOfJson(value);
    if (Array.isArray(expected)) return expected.some((t) => matchesType(t, value));
    switch (expected) {
      case "string": return actual === "string";
      case "number": return actual === "number" && Number.isFinite(value);
      case "integer": return actual === "number" && Number.isInteger(value);
      case "boolean": return actual === "boolean";
      case "object": return actual === "object" && isPlainObject(value);
      case "array": return actual === "array";
      case "null": return actual === "null";
      default: return true; // avoid false negatives on uncommon schema constructs
    }
  }

  function validateAgainstSchemaPractical(schema, instance) {
    /** @type {string[]} */
    const missing = [];
    /** @type {Array<{path:string, expected:string, actual:string}>} */
    const typeErrors = [];

    function visit(node, value, path, depth) {
      if (!node || typeof node !== "object") return;
      if (depth > VALIDATION_MAX_DEPTH) return;

      if (Array.isArray(node.allOf)) {
        for (const sub of node.allOf) visit(sub, value, path, depth + 1);
      }

      const any = Array.isArray(node.anyOf) ? node.anyOf : null;
      const one = Array.isArray(node.oneOf) ? node.oneOf : null;
      const union = any || one;
      if (union) {
        let okAny = false;
        for (const sub of union) {
          const m0 = missing.length;
          const t0 = typeErrors.length;
          visit(sub, value, path, depth + 1);
          const m1 = missing.length;
          const t1 = typeErrors.length;
          if (m1 === m0 && t1 === t0) okAny = true;
          if (!okAny) {
            missing.splice(m0, m1 - m0);
            typeErrors.splice(t0, t1 - t0);
          } else break;
        }
        return;
      }

      if (node.type && !matchesType(node.type, value)) {
        typeErrors.push({
          path,
          expected: Array.isArray(node.type) ? node.type.join("|") : String(node.type),
          actual: typeOfJson(value),
        });
        return;
      }

      if (Array.isArray(node.required) && isPlainObject(value)) {
        for (const k of node.required) {
          if (!(k in value)) missing.push(path ? `${path}.${k}` : k);
        }
      }

      if (node.properties && isPlainObject(node.properties) && isPlainObject(value)) {
        for (const [k, subSchema] of Object.entries(node.properties)) {
          if (!(k in value)) continue;
          visit(subSchema, value[k], path ? `${path}.${k}` : k, depth + 1);
        }
      }

      if (node.items && Array.isArray(value)) {
        const n = Math.min(value.length, VALIDATION_MAX_ARRAY);
        for (let i = 0; i < n; i++) {
          visit(node.items, value[i], `${path}[${i}]`, depth + 1);
        }
      }
    }

    visit(schema, instance, "$", 0);

    const ok = missing.length === 0 && typeErrors.length === 0;
    const summary = ok
      ? "Schema validation: PASS"
      : `Schema validation: FAIL (missing=${missing.length}, typeErrors=${typeErrors.length})`;

    return { ok, summary, missing, typeErrors };
  }

  function applyValidationResult(result) {
    DIAG.lastValidation = result;
    setValidation(result.ok, result.summary);
    setStatus(result.ok ? "Validated" : "Validation failed");
    writeDiagnosticsDump();
  }

  /* =========================
     12) Watchdog Tripwire (never-blank guarantee)
     ========================= */
  function regionOk(el) {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    const okSize = r.width >= 10 && r.height >= 10;
    const okDisplay = cs.display !== "none" && cs.visibility !== "hidden" && cs.opacity !== "0";
    return { ok: okSize && okDisplay, r, cs, okSize, okDisplay };
  }

  function runWatchdog() {
    /** @type {Array<{name:string, ok:boolean, detail?:string}>} */
    const checks = [];

    function chk(name, el) {
      try {
        const s = regionOk(el);
        if (!s.ok) {
          const detail = `display=${s.cs.display} vis=${s.cs.visibility} op=${s.cs.opacity} size=${Math.round(s.r.width)}x${Math.round(s.r.height)}`;
          checks.push({ name, ok: false, detail });
        } else {
          checks.push({ name, ok: true });
        }
      } catch (e) {
        checks.push({ name, ok: false, detail: e instanceof Error ? e.message : String(e) });
      }
    }

    chk("chromeStrip visible", chromeStrip);
    chk("menuBar visible", menuBar);
    chk("cadToolbar visible", cadToolbar);
    chk("subTabStrip visible", subTabStrip);
    chk("appShell visible", appShell);
    chk("taskBar visible", taskBar);

    const ok = checks.every((c) => c.ok);
    DIAG.watchdog = { ok, checks };
    writeDiagnosticsDump();

    if (!ok) {
      const likely =
        detectCssLoaded() !== "loaded"
          ? "Likely cause: CSS not loaded or blocked. Check dashboard.css path."
          : (location.protocol === "file:" ? "Likely cause: running file:// can block resources. Use a local server." : "Likely cause: layout collapse or injected CSS.");

      const detail = checks
        .filter((c) => !c.ok)
        .map((c) => `- ${c.name}: ${c.detail}`)
        .join("\n");

      recordError("watchdog", new Error(`${likely}\n${detail}`));
      showFatal("Render Watchdog TRIPPED (UI collapsed)", `${likely}\n\n${detail}`);
      document.body.dataset.uiState = "degraded";
      setBootLine("Watchdog", "TRIPPED");
      return;
    }

    setBootLine("Watchdog", "OK");
  }

  function startWatchdog() {
    // immediate and then periodic
    runWatchdog();
    setInterval(runWatchdog, 5000);
  }

  /* =========================
     13) Tripwire self-test
     ========================= */
  function selfTest() {
    /** @type {Array<{name:string, ok:boolean, detail?:string}>} */
    const checks = [];

    function check(name, fn) {
      try { fn(); checks.push({ name, ok: true }); }
      catch (e) { checks.push({ name, ok: false, detail: e instanceof Error ? e.message : String(e) }); }
    }

    check("Invariant nodes present (data-invariant='required')", () => {
      const req = Array.from(document.querySelectorAll('[data-invariant="required"]'));
      if (req.length < 8) throw invariant(`Expected many required invariant nodes; found ${req.length}`);
      for (const el of req) {
        if (!(el instanceof HTMLElement)) continue;
        if (!el.id) throw invariant("A required invariant node is missing an id");
      }
    });

    check("Progressive enhancement: html.js present", () => {
      const html = document.documentElement;
      if (!html.classList.contains("js")) throw invariant("Expected <html> class 'js'");
      if (html.classList.contains("no-js")) throw invariant("Expected <html> not to have 'no-js'");
    });

    check("tplWorkspaceTab integrity", () => {
      const t = tplWorkspaceTab.content;
      const root = t.querySelector(".wsTab");
      if (!(root instanceof HTMLElement)) throw invariant("tplWorkspaceTab missing .wsTab");
      const svg = root.querySelector("svg.tabSvg");
      if (!(svg instanceof SVGElement)) throw invariant("tplWorkspaceTab missing svg.tabSvg");
      const use = root.querySelector('use[href="#chromeTabPath"]');
      if (!(use instanceof SVGElement)) throw invariant('tplWorkspaceTab missing use[href="#chromeTabPath"]');
      const title = root.querySelector(".wsTitle");
      if (!(title instanceof HTMLElement)) throw invariant("tplWorkspaceTab missing .wsTitle");
      const close = root.querySelector(".wsClose");
      if (!(close instanceof HTMLElement)) throw invariant("tplWorkspaceTab missing .wsClose");
    });

    check("Workspace tabs rendered + active", () => {
      const tabs = chromeTabs.querySelectorAll(".wsTab");
      if (tabs.length < 1) throw invariant("No workspace tabs rendered");
      const active = chromeTabs.querySelector(".wsTab.active");
      if (!(active instanceof HTMLElement)) throw invariant("No active workspace tab found");
    });

    check("Schema loaded or explicitly explained (no silent unknown)", () => {
      if (!DIAG.schema) throw invariant("Schema state missing");
      if (DIAG.schema.loaded) return;
      if (!DIAG.schema.error) throw invariant("Schema not loaded and no error explanation provided");
    });

    check("Watchdog status present", () => {
      if (!DIAG.watchdog) throw invariant("Watchdog state missing");
    });

    check("Fatal banner hidden on pass", () => {
      if (!fatalBanner.hasAttribute("hidden")) throw invariant("fatalBanner should be hidden when healthy");
    });

    const ok = checks.every((c) => c.ok);
    return { ok, checks };
  }

  function runSelfTestAndReport() {
    const result = selfTest();
    DIAG.selfTest = result;
    writeDiagnosticsDump();

    if (result.ok) {
      setBootLine("Self-Test", "PASS");
      toast("Self-test: PASS");
      announce("Self-test passed");
      return;
    }

    const top = result.checks.filter((c) => !c.ok).slice(0, 12);
    const detail = top.map((c) => `- ${c.name}: ${c.detail || "failed"}`).join("\n");

    recordError("selftest", new Error(detail));
    setBootLine("Self-Test", "FAIL");
    showFatal("Self-Test FAILED", detail);
    toast("Self-test: FAIL");
    announce("Self-test failed");
  }

  /* =========================
     14) JSON load + schema validation timing
     ========================= */
  filePicker.addEventListener("change", async () => {
    const f = filePicker.files && filePicker.files[0];
    if (!f) return;
    try {
      setRunState("LOADING");
      setStatus("Loading JSON…");
      perfMark("json:load:start");

      const text = await f.text();
      const json = JSON.parse(text);
      engineDataLoaded = true;

      perfMark("json:load:end");
      perfMeasure("json.load.ms", "json:load:start", "json:load:end");

      if (DIAG.schema?.loaded && DIAG.schema.raw) {
        perfMark("json:validate:start");
        const result = validateAgainstSchemaPractical(DIAG.schema.raw, json);
        perfMark("json:validate:end");
        perfMeasure("json.validate.ms", "json:validate:start", "json:validate:end");
        applyValidationResult(result);
        applyInsightsFromData(json);
      } else {
        DIAG.lastValidation = {
          ok: true,
          summary: "Loaded (schema unavailable — see diagnostics)",
          missing: [],
          typeErrors: [],
        };
        setValidation(true, "JSON loaded (schema unavailable)");
        writeDiagnosticsDump();
        applyInsightsFromData(json);
      }

      const schemaVer = json?.schema_version || json?.schemaVersion || json?.schema || "";
      if (schemaVer) setSchemaVersion(schemaVer);

      setStatus("JSON loaded");
      setRunState("IDLE");
      announce("JSON loaded");
      writeDiagnosticsDump();
    } catch (e) {
      recordError("json.open", e);
      DIAG.lastValidation = {
        ok: false,
        summary: "Invalid JSON",
        missing: [],
        typeErrors: [{ path: "$", expected: "valid JSON", actual: "parse error" }],
      };
      setValidation(false, "Invalid JSON");
      setStatus("JSON failed");
      setRunState("IDLE");
      showFatal("JSON Load Failed", e instanceof Error ? e.message : String(e));
      writeDiagnosticsDump();
    }
  });

  /* =========================
     15) Actions
     ========================= */
  function resetLayout() {
    toast("Layout reset");
    announce("Layout reset");
  }

  function resetFactory() {
    clearState();
    toast("Factory reset (storage cleared)");
    announce("Factory reset");
    // Soft reload preserves proof; user can refresh manually if desired
    writeDiagnosticsDump();
  }

  function dispatchAction(action) {
    switch (action) {
      case "workspace.new": newWorkspace(); break;
      case "workspace.close": closeWorkspace(activeWorkspaceId); break;
      case "json.open":
        filePicker.value = "";
        filePicker.click();
        break;
      case "export.diag": exportDiagnostics(); break;
      case "layout.reset": resetLayout(); break;
      case "selftest": runSelfTestAndReport(); break;
      case "factory.reset": resetFactory(); break;
      case "view.grid":
      case "view.stats":
      case "view.compact":
        toast(`Toggled: ${action.replace("view.", "").toUpperCase()}`);
        break;
      case "help.shortcuts":
        toast("Shortcuts: ⌘N New, ⌘O Open, ⌘D Export, ⌘Tab Cycle, ⌘R Reset Layout");
        break;
      case "help.about":
        toast("Daily Dashboard UI (HTML V9 / CSS V2 / JS V4). Export diagnostics for proof.");
        break;
      case "insights.sample":
        applyInsightsSample();
        break;
      default:
        toast(`Unknown action: ${action}`);
        break;
    }
  }

  // Quality-lock: hard-wire critical buttons
  btnNewWorkspace.addEventListener("click", (ev) => { ev.preventDefault(); newWorkspace(); });
  btnResetLayout.addEventListener("click", (ev) => { ev.preventDefault(); resetLayout(); });
  btnSelfTest.addEventListener("click", (ev) => { ev.preventDefault(); runSelfTestAndReport(); });
  btnExportDiag.addEventListener("click", (ev) => { ev.preventDefault(); exportDiagnostics(); });

  /* =========================
     16) Global error tripwires
     ========================= */
  function wireGlobalErrors() {
    window.addEventListener("error", (ev) => {
      recordError("window.error", ev.error || ev.message);
      showFatal("Unhandled Error", ev.error instanceof Error ? ev.error.message : String(ev.message));
    });

    window.addEventListener("unhandledrejection", (ev) => {
      recordError("unhandledrejection", ev.reason);
      showFatal("Unhandled Promise Rejection", ev.reason instanceof Error ? ev.reason.message : String(ev.reason));
    });
  }

  /* =========================
     17) Boot
     ========================= */
  function boot() {
    perfMark("boot:start");
    try {
      wireGlobalErrors();
      markJsEnabled();

      setBootLine("HTML", "OK");
      setBootLine("CSS", detectCssLoaded());
      setBootLine("JS", "running");
      setBootLine("Schema", "pending…");
      setBootLine("Watchdog", "pending…");
      setBootLine("Self-Test", "pending…");

      setSchemaVersion("—");
      setValidation(true, "UI ready");
      setRunState("IDLE");
      setStatus("READY");

      // Restore persisted state if available
      const restored = restoreState();
      if (restored) toast("Restored previous session");

      wireMenus();
      wireMenuKeyboardNav();
      wireActionDelegation();
      wireWorkspaceShortcuts();
      wireSubTabs();
      wirePlotExports();
      wireInsightsSample();

      renderWorkspaceTabs();
      updateMenuContextChip();

      startClock();
      writeDiagnosticsDump();

      // Start watchdog early (catches collapses)
      startWatchdog();

      loadSchema()
        .finally(() => {
          writeDiagnosticsDump();
          runSelfTestAndReport();
          document.body.dataset.uiState = DIAG.selfTest?.ok ? "healthy" : "degraded";

          perfMark("boot:end");
          perfMeasure("boot.total.ms", "boot:start", "boot:end");

          setBootLine("Perf", `boot=${DIAG.perf["boot.total.ms"] ?? "—"}ms`);
          toast("Boot complete");
          announce("Dashboard ready");
        })
        .catch((e) => recordError("boot.schema", e));
    } catch (e) {
      recordError("boot", e);
      setBootLine("JS", "failed");
      setBootLine("Self-Test", "not-run");
      showFatal("Boot Failed", e instanceof Error ? e.message : String(e));
      document.body.dataset.uiState = "failed";
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
