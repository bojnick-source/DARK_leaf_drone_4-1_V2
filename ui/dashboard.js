const notice = document.getElementById("notice");
const statusPill = document.getElementById("statusPill");
const clockPill = document.getElementById("clockPill");
const modePill = document.getElementById("modePill");
const schemaPill = document.getElementById("schemaPill");
const payloadPill = document.getElementById("payloadPill");

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
  const time = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  clockPill.textContent = `TIME: ${time}`;
}

function attachHandlers() {
  const btnLoadSample = document.getElementById("btnLoadSample");
  const btnValidate = document.getElementById("btnValidate");
  const btnHelp = document.getElementById("btnHelp");

  if (btnLoadSample) {
    btnLoadSample.addEventListener("click", async () => {
      setStatus("LOADING", "#92400e");
      showNotice("Loading sample...", "Attempting to fetch sample payload.");
      try {
        const response = await fetch("./sample_payload.json", { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`Sample payload request failed (${response.status})`);
        }
        const payload = await response.json();
        if (payloadPill) {
          payloadPill.textContent = "PAYLOAD: SAMPLE";
        }
        if (schemaPill) {
          schemaPill.textContent = payload.schema ? `SCHEMA: ${payload.schema}` : "SCHEMA: (unknown)";
        }
        showNotice("Sample loaded", "Sample payload retrieved successfully.");
        setStatus("OK", "#14532d");
      } catch (error) {
        setStatus("FAIL", "#7f1d1d");
        showNotice("Sample load failed", `${error.message}`);
      }
    });
  }

  if (btnValidate) {
    btnValidate.addEventListener("click", () => {
      if (window.validateDashboardPayload) {
        try {
          const result = window.validateDashboardPayload();
          showNotice("Validation complete", result || "Validation executed.");
          setStatus("OK", "#14532d");
        } catch (error) {
          setStatus("FAIL", "#7f1d1d");
          showNotice("Validation error", `${error.message}`);
        }
      } else {
        setStatus("WARN", "#7c2d12");
        showNotice("Validator not wired yet", "Hook up validateDashboardPayload() to enable validation.");
      }
    });
  }

  if (btnHelp) {
    btnHelp.addEventListener("click", () => {
      setStatus("INFO", "#1e3a8a");
      showNotice(
        "Local run tips",
        "Serve the ui folder with a simple HTTP server (e.g. 'python -m http.server') and open /ui/dashboard.html."
      );
    });
  }
}

function handleGlobalError(message) {
  setStatus("FAIL", "#7f1d1d");
  showNotice("Dashboard error", String(message));
}

window.addEventListener("error", (event) => {
  handleGlobalError(event.error ? event.error.message : event.message);
});

window.addEventListener("unhandledrejection", (event) => {
  handleGlobalError(event.reason ? event.reason.message || event.reason : "Unhandled promise rejection");
});

window.addEventListener("DOMContentLoaded", () => {
  if (modePill) {
    modePill.textContent = "MODE: SHELL";
  }
  updateClock();
  setInterval(updateClock, 1000);
  attachHandlers();
  setStatus("READY", "#1f2937");
});
