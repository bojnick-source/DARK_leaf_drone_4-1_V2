/* desktop_only.js — gate UI to desktop-class viewports for now */
(function () {
  "use strict";

  function isDesktopClass() {
    const minWidth = 1100;
    const coarsePointer = window.matchMedia("(pointer: coarse)").matches;
    const canHover = window.matchMedia("(hover: hover)").matches;
    return window.innerWidth >= minWidth && (!coarsePointer || canHover);
  }

  function renderDesktopOnlyNotice() {
    const style = document.createElement("style");
    style.textContent = [
      "body{margin:0;background:#0a0b0e;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}",
      ".desktop-only-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;}",
      ".desktop-only-card{max-width:620px;background:rgba(14,17,24,.88);border:1px solid rgba(255,255,255,.14);",
      "border-radius:14px;padding:22px 20px;box-shadow:0 18px 40px rgba(0,0,0,.45)}",
      ".desktop-only-card h1{margin:0 0 8px;font-size:22px}",
      ".desktop-only-card p{margin:0;color:#8b949e;line-height:1.5}",
    ].join("");
    document.head.appendChild(style);
    document.body.innerHTML =
      '<div class="desktop-only-wrap"><div class="desktop-only-card">' +
      "<h1>Desktop access only</h1>" +
      "<p>This UI is currently desktop-only. Please open it on a desktop/laptop viewport.</p>" +
      "</div></div>";
  }

  if (isDesktopClass()) {
    return;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderDesktopOnlyNotice, { once: true });
  } else {
    renderDesktopOnlyNotice();
  }
})();
