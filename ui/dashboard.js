const $ = (id) => document.getElementById(id);
const safeText = (el, value) => {
  if (!el) {
    return;
  }
  el.textContent = String(value);
};
const notice = $("notice");
const statusPill = $("statusPill");
const selfTestPill = $("selfTestPill");
const clockPill = $("clockPill");
const modePill = $("modePill");
const schemaPill = $("schemaPill");
const payloadPill = $("payloadPill");
const SAMPLE_FETCH_TIMEOUT_MS = 5000;
const STATUS_COLORS = {
  ready: "#1f2937",
  info: "#1e3a8a",
  warn: "#7c2d12",
  ok: "#14532d",
  fail: "#7f1d1d",
  loading: "#92400e"
};
let currentPayload = null;

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
  const btnLoadSample = $("btnLoadSample");
  const btnValidate = $("btnValidate");
  const btnHelp = $("btnHelp");
  const btnHome = $("btnHome");

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

  if (btnHome) {
    btnHome.addEventListener("click", () => {
      setStatus("READY", STATUS_COLORS.ready, "ok");
      showNotice(
        "Dashboard Shell Loaded",
        "If you see this but no data, open Console logs or run via local server."
      );
    });
  }
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
  const hasMenu = Boolean($("menuBar"));
  const hasTask = Boolean($("taskBar"));
  const now = new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const message = `UI loaded · ${now} · Menu: ${hasMenu ? "YES" : "NO"} · Task: ${hasTask ? "YES" : "NO"}`;
  safeText(selfTestPill, `SELF-TEST: ${message}`);
}

function init() {
  try {
    safeText(modePill, "MODE: SHELL");
    updateClock();
    clockIntervalId = setInterval(updateClock, 1000);
    attachHandlers();
    setStatus("READY", STATUS_COLORS.ready, "ok");
    renderSelfTest();
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
