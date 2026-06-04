/* DevBareun v1.3.7 — A4/A3 print controller */
(function () {
  "use strict";
  const KEY = "devbareun_print_size";
  const SETTINGS_KEY = "devbareun_saas_settings";

  function qs(sel, root = document) { return root.querySelector(sel); }
  function qsa(sel, root = document) { return Array.from(root.querySelectorAll(sel)); }
  function cleanSize(value) {
    const v = String(value || "").toUpperCase();
    return v === "A3" ? "A3" : "A4";
  }
  function defaultSize() {
    try {
      const settings = JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}");
      return cleanSize(settings.print || localStorage.getItem(KEY) || "A4");
    } catch (_) {
      return cleanSize(localStorage.getItem(KEY) || "A4");
    }
  }
  function pageCss(size) {
    if (size === "A3") {
      return "@page{size:A3 landscape;margin:10mm;}@media print{body{min-width:400mm!important;}}";
    }
    return "@page{size:A4 portrait;margin:12mm;}@media print{body{min-width:186mm!important;}}";
  }
  function injectPageStyle(size) {
    let style = qs("#devbareunPrintPageSize");
    if (!style) {
      style = document.createElement("style");
      style.id = "devbareunPrintPageSize";
      document.head.appendChild(style);
    }
    style.textContent = pageCss(size);
  }
  function setSize(size) {
    const chosen = cleanSize(size);
    try { localStorage.setItem(KEY, chosen); } catch (_) {}
    document.documentElement.classList.toggle("db-print-a3", chosen === "A3");
    document.documentElement.classList.toggle("db-print-a4", chosen !== "A3");
    document.body?.classList.toggle("db-print-a3", chosen === "A3");
    document.body?.classList.toggle("db-print-a4", chosen !== "A3");
    qsa(".db-print-size-select").forEach(sel => { sel.value = chosen; });
    injectPageStyle(chosen);
    return chosen;
  }
  function print(size) {
    const chosen = setSize(size || defaultSize());
    document.body?.classList.add("db-is-printing");
    setTimeout(() => window.print(), 60);
    return chosen;
  }
  function bind() {
    setSize(defaultSize());
    qsa(".db-print-size-select").forEach(sel => {
      if (sel.dataset.printBound) return;
      sel.dataset.printBound = "true";
      sel.value = defaultSize();
      sel.addEventListener("change", () => setSize(sel.value));
    });
    qsa("[data-print-size], .db-print-btn").forEach(btn => {
      if (btn.dataset.printClickBound) return;
      btn.dataset.printClickBound = "true";
      btn.addEventListener("click", event => {
        const requested = btn.getAttribute("data-print-size");
        if (!requested && btn.id !== "printDashboardBtn" && !btn.classList.contains("db-print-btn")) return;
        event.preventDefault();
        print(requested && requested !== "auto" ? requested : defaultSize());
      }, true);
    });
    const params = new URLSearchParams(location.search);
    const requested = params.get("print");
    if (requested) setSize(requested);
    if (params.get("auto") === "print" || params.get("autoprint") === "1") {
      setTimeout(() => print(requested || defaultSize()), 700);
    }
  }
  window.addEventListener("afterprint", () => document.body?.classList.remove("db-is-printing"));
  document.addEventListener("DOMContentLoaded", bind);
  document.addEventListener("devbareun:reports-rendered", bind);
  window.DevBareunPrint = { setSize, print, defaultSize, bind };
})();
