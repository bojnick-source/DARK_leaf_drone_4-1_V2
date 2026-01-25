const notice = document.getElementById("notice");
const statusPill = document.getElementById("statusPill");
const clockPill = document.getElementById("clockPill");
const modePill = document.getElementById("modePill");
const schemaPill = document.getElementById("schemaPill");
const payloadPill = document.getElementById("payloadPill");
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

function setStatus(label, tone) {
  if (!statusPill) {
    return;
  }
  statusPill.textContent = `STATUS: ${label}`;
  statusPill.style.background = tone;
}

function showNotice(title, message) {
  if (!notice) {
    return;
  }
  const titleEl = document.createElement("div");
  titleEl.className = "title";
  titleEl.textContent = title;
  const hintEl = document.createElement("div");
  hintEl.className = "hint";
  hintEl.textContent = message;
  notice.replaceChildren(titleEl, hintEl);
}

function updateClock() {
  if (!clockPill) {
    return;
  }
  const now = new Date();
  const time = now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  clockPill.textContent = `TIME: ${time}`;
}

function attachHandlers() {
  const btnLoadSample = document.getElementById("btnLoadSample");
  const btnValidate = document.getElementById("btnValidate");
  const btnHelp = document.getElementById("btnHelp");
  const btnHome = document.getElementById("btnHome");

  if (btnLoadSample) {
    btnLoadSample.addEventListener("click", async () => {
      setStatus("LOADING", STATUS_COLORS.loading);
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
        if (payloadPill) {
          payloadPill.textContent = "PAYLOAD: SAMPLE";
        }
        if (schemaPill) {
          const schemaLabel = payload.schema ? String(payload.schema) : "(unknown)";
          schemaPill.textContent = `SCHEMA: ${schemaLabel}`;
        }
        showNotice("Sample loaded", "Sample payload retrieved successfully.");
        setStatus("OK", STATUS_COLORS.ok);
      } catch (error) {
        setStatus("FAIL", STATUS_COLORS.fail);
        showNotice("Sample load failed", `${error.message}`);
      } finally {
        clearTimeout(timeoutId);
      }
    });
  }

  if (btnValidate) {
    btnValidate.addEventListener("click", () => {
      if (window.validateDashboardPayload) {
        try {
          const result = window.validateDashboardPayload(currentPayload);
          showNotice("Validation complete", result || "Validation executed.");
          setStatus("OK", STATUS_COLORS.ok);
        } catch (error) {
          setStatus("FAIL", STATUS_COLORS.fail);
          showNotice("Validation error", `${error.message}`);
        }
      } else {
        setStatus("WARN", STATUS_COLORS.warn);
        showNotice("Validator not wired yet", "Hook up validateDashboardPayload() to enable validation.");
      }
    });
  }

  if (btnHelp) {
    btnHelp.addEventListener("click", () => {
      setStatus("INFO", STATUS_COLORS.info);
      showNotice(
        "Local run tips",
        "Serve the ui folder with a simple HTTP server (e.g. 'python -m http.server') and open /dashboard.html."
      );
    });
  }

  if (btnHome) {
    btnHome.addEventListener("click", () => {
      setStatus("READY", STATUS_COLORS.ready);
      showNotice(
        "Dashboard Shell Loaded",
        "If you see this but no data, open Console logs or run via local server."
      );
    });
  }
}

function handleGlobalError(message) {
  setStatus("FAIL", STATUS_COLORS.fail);
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

window.addEventListener("DOMContentLoaded", () => {
  if (modePill) {
    modePill.textContent = "MODE: SHELL";
  }
  updateClock();
  clockIntervalId = setInterval(updateClock, 1000);
  attachHandlers();
  setStatus("READY", STATUS_COLORS.ready);
});

window.addEventListener("beforeunload", () => {
  if (clockIntervalId) {
    clearInterval(clockIntervalId);
  }
});
