(function () {
  "use strict";

  function esc(value) {
    return String(value ?? "").replace(/[&<>\"]/g, function (ch) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;" }[ch] || ch);
    });
  }

  async function loadGuestResult() {
    var isProductionHost = location.hostname === "devbareun.com" || location.hostname === "www.devbareun.com";
    var apiBase = (!isProductionHost ? localStorage.getItem("devbareun_api_base") : "") ||
      window.DEVBAREUN_API_URL ||
      "https://devbareun-production.up.railway.app";
    var token = new URLSearchParams(location.search).get("token");
    var mount = document.getElementById("guestResultMount");
    if (!mount) return;
    if (!token) {
      mount.innerHTML = "<h1>Missing token</h1>";
      return;
    }
    try {
      var res = await fetch(apiBase + "/api/workspace/guest-results/" + encodeURIComponent(token));
      var data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Result not found");
      var row = data.guest_result || {};
      mount.innerHTML = `
        <div class="report-action-toolbar db-screen-only">
          <a class="btn btn-ghost" href="/reports.html">Back to reports</a>
          <div class="report-archive-filters">
            <select class="db-print-size-select" aria-label="Print size"><option value="A4">A4</option><option value="A3">A3</option></select>
            <button class="btn btn-primary db-print-btn" data-print-size="auto">Print result</button>
          </div>
        </div>
        <article class="report-print-preview">
          <div class="report-print-cover">
            <div>
              <p class="eyebrow">Secure guest result</p>
              <h1>${esc(row.project_name || "Project result")}</h1>
              <p>Temporary report access is active. Use A4 for formal memo-style print and A3 for wide dashboard review.</p>
            </div>
            <span class="report-chip">Guest link</span>
          </div>
          <details class="report-json-details" open>
            <summary>Raw result payload</summary>
            <pre>${esc(JSON.stringify(row.dashboard || {}, null, 2))}</pre>
          </details>
        </article>`;
      document.dispatchEvent(new CustomEvent("devbareun:reports-rendered"));
    } catch (err) {
      mount.innerHTML = "<h1>Result unavailable</h1><p>" + esc(err.message) + "</p>";
    }
  }

  loadGuestResult();
})();
