(function () {
  const DEFAULT_REMOTE_API = "https://devbareun-production.up.railway.app";
  const PRODUCTION_HOSTS = new Set(["devbareun.com", "www.devbareun.com"]);
  const IS_PRODUCTION_HOST = PRODUCTION_HOSTS.has(location.hostname);
  const API_BASE = (window.DEVBAREUN_API_BASE ||
    ((location.protocol === "file:" || location.hostname === "localhost" || location.hostname === "127.0.0.1")
      ? ((!IS_PRODUCTION_HOST ? localStorage.getItem("devbareun_api_base") : "") || `http://${location.hostname === "localhost" ? "127.0.0.1" : location.hostname}:8000`)
      : DEFAULT_REMOTE_API)).replace(/\/$/, "");

  let latestDashboard = null;

  function qs(sel, root = document) { return root.querySelector(sel); }
  function qsa(sel, root = document) { return Array.from(root.querySelectorAll(sel)); }
  function getProjectId() { return new URLSearchParams(window.location.search).get("project_id"); }
  function getProjectToken(projectId) { try { return localStorage.getItem(`devbareun_project_token_${projectId}`) || ""; } catch (e) { return ""; } }
  function withProjectToken(url, projectId) {
    const token = getProjectToken(projectId);
    if (!token) return url;
    const u = new URL(url, location.origin);
    u.searchParams.set("project_token", token);
    return u.toString();
  }
  function na(value) { return value === undefined || value === null || value === "" ? "—" : value; }
  function pct(value) { return value === undefined || value === null ? "—" : `${value}%`; }
  function days(value) { return window.DevBareunI18n ? window.DevBareunI18n.days(value) : (value === undefined || value === null ? "—" : `${value > 0 ? "+" : ""}${value} days`); }
  function risk(value) { return value === undefined || value === null ? "—" : `${value}/100`; }
  function mark(el) { if (el) { el.dataset.dbDynamic = "true"; el.removeAttribute("data-r-i18n"); } return el; }
  function setText(el, text) { if (!el) return; mark(el); el.textContent = text; }
  function htmlEscape(value) { return String(value ?? "").replace(/[&<>\"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[ch])); }
  function isAz() { return !!(window.DevBareunI18n && window.DevBareunI18n.isAz()); }
  function Ltext(value) { return window.DevBareunI18n ? window.DevBareunI18n.text(value) : value; }
  function Llabel(value) { return window.DevBareunI18n ? window.DevBareunI18n.label(value) : value; }

  function translateRenderedDashboard(root = document.body) {
    if (isAz() && window.DevBareunI18n && typeof window.DevBareunI18n.translateNode === "function") {
      window.DevBareunI18n.translateNode(root);
    }
  }

  function badgeClass(level) {
    const v = String(level || "").toLowerCase();
    if (v.includes("critical") || v.includes("high")) return "badge red";
    if (v.includes("medium") || v.includes("watch")) return "badge amber";
    return "badge green";
  }

  function statusClass(status) {
    const v = String(status || "").toLowerCase();
    if (v.includes("critical") || v.includes("risk")) return "status-chip high";
    if (v.includes("watch") || v.includes("review")) return "status-chip watch";
    return "status-chip";
  }

  function getReportLang() {
    // v1.1.6: keep report/export language aligned with the visible UI language.
    // This prevents an AZ dashboard from exporting English labels because of stale localStorage.
    const uiLang = localStorage.getItem("devbareun_lang") === "az" ? "az" : "en";
    const select = document.getElementById("reportLangSelect");
    if (select) select.value = uiLang;
    return uiLang;
  }

  function syncReportLangControl() {
    const select = document.getElementById("reportLangSelect");
    if (!select) return;
    const uiLang = localStorage.getItem("devbareun_lang") === "az" ? "az" : "en";
    select.value = uiLang;
    localStorage.setItem("devbareun_report_lang", uiLang);
    select.onchange = () => {
      const chosen = select.value === "az" ? "az" : "en";
      localStorage.setItem("devbareun_report_lang", chosen);
    };
  }

  function setDownloadLinks(projectId) {
    syncReportLangControl();
    const printBtn = document.getElementById("printDashboardBtn");
    if (printBtn && !printBtn.dataset.printBound) {
      printBtn.dataset.printBound = "true";
      printBtn.textContent = isAz() ? "Çap et" : "Print";
      printBtn.onclick = (e) => { e.preventDefault(); window.print(); };
    }
    qsa("button, a").forEach(btn => {
      const label = (btn.textContent || "").toLowerCase();
      if (label.includes("pdf") || label.includes("yüklə")) {
        btn.onclick = () => {
          const previous = btn.textContent;
          const lang = getReportLang();
          btn.textContent = lang === "az" ? "PDF hesabat hazırlanır..." : "Preparing selected dashboard PDF...";
          btn.disabled = true;
          window.open(withProjectToken(`${API_BASE}/api/projects/${projectId}/report/pdf?lang=${encodeURIComponent(lang)}`, projectId), "_blank");
          setTimeout(() => { btn.textContent = previous || (lang === "az" ? "PDF yüklə" : "Download PDF"); btn.disabled = false; }, 1800);
        };
      }
      if (label.includes("excel")) {
        btn.onclick = () => {
          const previous = btn.textContent;
          const lang = getReportLang();
          btn.textContent = lang === "az" ? "Excel hesabat hazırlanır..." : "Preparing dashboard Excel...";
          btn.disabled = true;
          window.open(withProjectToken(`${API_BASE}/api/projects/${projectId}/report/excel?lang=${encodeURIComponent(lang)}`, projectId), "_blank");
          setTimeout(() => { btn.textContent = previous || (lang === "az" ? "Excel yüklə" : "Download Excel"); btn.disabled = false; }, 1600);
        };
      }
    });
  }

  function updateMeta(project, data) {
    const spans = qsa(".result-meta span");
    if (spans[0]) { mark(spans[0]); spans[0].innerHTML = `<b>${htmlEscape(Llabel("Project"))}</b>: ${htmlEscape(project.name || "—")}`; }
    if (spans[1]) { mark(spans[1]); spans[1].innerHTML = `<b>${htmlEscape(Llabel("Report ID"))}</b>: ${htmlEscape(project.report_id || data.project_id || "—")}`; }
    if (spans[2]) { mark(spans[2]); spans[2].innerHTML = `<b>${htmlEscape(Llabel("Date"))}</b>: ${htmlEscape(project.report_date || "—")}`; }
  }

  function updateKpis(kpis) {
    const cards = qsa(".result-kpi");
    const values = [
      pct(kpis.planned_execution),
      pct(kpis.actual_execution),
      kpis.delay_days === undefined || kpis.delay_days === null ? "—" : `+${kpis.delay_days}`,
      pct(kpis.cost_variance_percent),
      na(kpis.workforce_current),
      na(kpis.risk_level)
    ];
    cards.forEach((card, i) => {
      setText(card.querySelector("strong"), String(values[i]));
    });

    if (cards[1]) {
      const small = cards[1].querySelector("small span:last-child");
      setText(small, kpis.schedule_gap_percent === undefined || kpis.schedule_gap_percent === null ? Ltext("Gap not available") : `${isAz() ? "Planla fərq" : "Gap"}: -${kpis.schedule_gap_percent}%`);
    }
    if (cards[4]) {
      const small = cards[4].querySelector("small span:last-child");
      const req = kpis.workforce_required;
      setText(small, req === undefined || req === null ? Ltext("required: not available") : (isAz() ? `tələb olunan: ${req}` : `required: ${req}`));
    }

    setText(qs('[data-r-i18n="chartPlan"]'), `${Llabel("Plan")} ${pct(kpis.planned_execution)}`);
    setText(qs('[data-r-i18n="chartActual"]'), `${Llabel("Actual")} ${pct(kpis.actual_execution)}`);
    setText(qs('[data-r-i18n="chartGap"]'), kpis.schedule_gap_percent === undefined || kpis.schedule_gap_percent === null ? `${Llabel("Gap")} —` : `${Llabel("Gap")} -${kpis.schedule_gap_percent}%`);
  }

  function updateForecast(forecast) {
    const forecastCards = qsa(".forecast-strip strong");
    if (forecastCards[0]) setText(forecastCards[0], na(forecast.estimated_finish));
    if (forecastCards[1]) setText(forecastCards[1], na(forecast.baseline_finish));
    if (forecastCards[2]) setText(forecastCards[2], days(forecast.delay_impact_days));
    const text = qs('[data-r-i18n="forecastText"]');
    if (text) {
      const delay = forecast.delay_impact_days;
      setText(text, delay === undefined || delay === null
        ? Ltext("Completion forecast could not be calculated because baseline and estimated finish dates were not clearly detected.")
        : Ltext(`Based on detected dates, the projected completion date moves ${delay} day(s) beyond the baseline target.`));
    }
  }

  function updateRiskComponents(components) {
    const labels = qsa(".radar-legend span");
    const keys = ["schedule", "cost", "labor", "procurement", "quality"];
    labels.forEach((label, i) => {
      const key = keys[i];
      const em = label.querySelector("em");
      const name = em ? em.textContent : key;
      label.innerHTML = `<b></b><em>${htmlEscape(name)}</em> ${components && components[key] !== null && components[key] !== undefined ? components[key] : "—"}`;
      mark(label);
    });

    // Spider chart points are recalculated from component values. Missing components use zero.
    const vals = keys.map(k => Math.max(0, Math.min(100, Number((components || {})[k] || 0))));
    const center = { x: 160, y: 160 };
    const maxR = 126;
    const angles = [-90, -18, 54, 126, 198].map(a => a * Math.PI / 180);
    const points = vals.map((v, i) => {
      const r = (v / 100) * maxR;
      return [center.x + Math.cos(angles[i]) * r, center.y + Math.sin(angles[i]) * r];
    });
    const polygon = qs(".radar-area");
    if (polygon) polygon.setAttribute("points", points.map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" "));
    qsa(".radar-point").forEach((circle, i) => {
      if (points[i]) {
        circle.setAttribute("cx", points[i][0].toFixed(1));
        circle.setAttribute("cy", points[i][1].toFixed(1));
      }
    });
  }

  function updateCostAndWorkforce(dashboard) {
    const k = dashboard.kpis || {};
    const project = dashboard.project || {};
    const costStrong = qs(".cost-card strong");
    setText(costStrong, k.cost_variance_percent === undefined || k.cost_variance_percent === null ? "—" : `${k.cost_variance_percent}% ${project.currency || ""}`.trim());
    const costText = qs('[data-r-i18n="costStatusText"]');
    if (costText) {
      setText(costText, k.cost_variance_percent === undefined || k.cost_variance_percent === null
        ? Ltext("Cost variance could not be calculated from the uploaded files.")
        : Ltext("Cost pressure should be reviewed by work package and compared with approved baseline values."));
    }

    const meters = qsa(".workforce-meter strong");
    if (meters[0]) setText(meters[0], na(k.workforce_current));
    if (meters[1]) setText(meters[1], na(k.workforce_required));
    if (meters[2]) {
      const gap = (k.workforce_current !== undefined && k.workforce_current !== null && k.workforce_required)
        ? k.workforce_current - k.workforce_required
        : null;
      setText(meters[2], gap === null ? "—" : String(gap));
    }
  }

  function updateRiskRegister(rows) {
    const tbody = qs(".result-table tbody");
    if (!tbody) return;
    tbody.innerHTML = "";
    (rows || []).forEach(row => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${htmlEscape(Ltext(row.risk || "—"))}</td>
        <td><span class="${badgeClass(row.level)}">${htmlEscape(Ltext(row.level || "—"))}</span></td>
        <td>${htmlEscape(Ltext(row.reason || "—"))}</td>
        <td>${htmlEscape(Ltext(row.action || "—"))}</td>`;
      tbody.appendChild(tr);
    });
    mark(tbody);
    const count = qs('[data-r-i18n="riskCount"]');
    if (count) setText(count, isAz() ? `${(rows || []).length} risk` : `${(rows || []).length} risk${(rows || []).length === 1 ? "" : "s"}`);
  }

  function updateActions(actions) {
    const list = qs(".action-list");
    if (!list) return;
    list.innerHTML = "";
    (actions || []).forEach(action => {
      const li = document.createElement("li");
      li.textContent = Ltext(action);
      list.appendChild(li);
    });
    mark(list);
  }

  function formatMetricValue(item) {
    const value = item && item.value;
    const unit = (item && item.unit) || "";
    if (value === undefined || value === null || value === "") return "—";
    if (typeof value === "number") {
      if (["AZN", "USD", "EUR"].includes(unit.toUpperCase())) return `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${unit}`;
      if (unit === "%") return `${value}%`;
      if (unit === "/100") return `${value}/100`;
      return `${value}${unit ? " " + unit : ""}`;
    }
    return `${value}${unit ? " " + unit : ""}`;
  }

  function renderAnalysisDashboard(d) {
    let mount = qs("#analysisDashboardMount");
    if (!mount) {
      mount = document.createElement("section");
      mount.id = "analysisDashboardMount";
      mount.className = "analysis-dashboard-view";
      const status = qs(".result-status-card");
      if (status && status.parentNode) status.parentNode.insertBefore(mount, status.nextSibling);
    }

    const p = d.project || {};
    const sections = d.dashboard_sections || {};
    const cards = sections.primary_kpis || [];
    const panels = sections.panels || [];
    const mode = sections.mode || p.analysis_type || "all";

    document.body.dataset.analysisDashboard = mode;
    setText(qs('[data-r-i18n="resultTitle"]'), Ltext(p.dashboard_title || sections.title || "Your project dashboard is ready."));
    setText(qs('[data-r-i18n="resultLead"]'), Ltext(p.dashboard_description || sections.description || "Review selected project-control indicators below."));

    if (typeof window.renderScheduleProgressDashboard === "function") {
      const rendered = window.renderScheduleProgressDashboard(mount, d, {
        htmlEscape, formatMetricValue, pct, days, na
      });
      if (rendered) {
        mark(mount);
        translateRenderedDashboard(mount);
        return;
      }
    }

    if (typeof window.renderAnalysisSpecificDashboard === "function") {
      const rendered = window.renderAnalysisSpecificDashboard(mount, d, {
        htmlEscape, formatMetricValue, pct, days, na
      });
      if (rendered) {
        mark(mount);
        translateRenderedDashboard(mount);
        return;
      }
    }

    const cardHtml = cards.length ? cards.map(item => `
      <article class="analysis-kpi ${htmlEscape(item.status || "neutral")}">
        <span>${htmlEscape(Llabel(item.label || "Metric"))}</span>
        <strong>${htmlEscape(formatMetricValue(item))}</strong>
        ${item.note ? `<small>${htmlEscape(Ltext(item.note))}</small>` : `<small>${htmlEscape(Ltext(item.status || ""))}</small>`}
      </article>`).join("") : `<article class="analysis-kpi neutral"><span>${htmlEscape(Llabel("Dashboard data"))}</span><strong>—</strong><small>${htmlEscape(Ltext("No selected dashboard KPIs available"))}</small></article>`;

    const panelsHtml = panels.map(panel => `
      <article class="analysis-panel">
        <h3>${htmlEscape(Ltext(panel.title || "Dashboard panel"))}</h3>
        <div class="analysis-panel-rows">
          ${(panel.rows || []).map(item => `<div><span>${htmlEscape(Llabel(item.label || "Metric"))}</span><b>${htmlEscape(formatMetricValue(item))}</b></div>`).join("")}
        </div>
      </article>`).join("");

    mount.innerHTML = `
      <div class="analysis-dashboard-head">
        <div>
          <span class="analysis-mode-pill">${htmlEscape(Ltext(String(mode).toUpperCase()))}</span>
          <h2>${htmlEscape(Ltext(p.dashboard_title || sections.title || "Selected Analysis Dashboard"))}</h2>
          <p>${htmlEscape(Ltext(p.dashboard_description || sections.description || "The report and PDF follow this selected dashboard view."))}</p>
        </div>
        <div class="analysis-pdf-note">${htmlEscape(Ltext("PDF export uses this same dashboard logic."))}</div>
      </div>
      <div class="analysis-kpi-grid">${cardHtml}</div>
      <div class="analysis-panel-grid">${panelsHtml}</div>`;
    mark(mount);
    translateRenderedDashboard(mount);
  }

  function updateDashboard(data) {
    latestDashboard = data;
    const d = data.dashboard || {};
    const p = d.project || {};
    const k = d.kpis || {};
    const f = d.forecast || {};

    updateMeta(p, data);
    renderAnalysisDashboard(d);
    updateKpis(k);
    updateForecast(f);
    updateRiskComponents(d.risk_components || {});
    updateCostAndWorkforce(d);
    updateRiskRegister(d.risk_register || []);
    updateActions(d.recommended_actions || []);

    const statusChip = qs(".status-chip");
    if (statusChip) {
      statusChip.className = statusClass(p.status);
      setText(statusChip, Ltext(p.status || "Data review required"));
    }

    const score = qs(".status-score strong");
    if (score) setText(score, risk(k.risk_score));

    const legend = qs(".status-score small");
    if (legend) setText(legend, k.risk_level ? Ltext(`${k.risk_level} risk zone`) : Ltext("Risk score not available"));

    const summary = qs('[data-r-i18n="execSummaryText"]');
    if (summary) setText(summary, Ltext(d.executive_summary || "No executive summary could be generated from the uploaded data."));

    setDownloadLinks(data.project_id);
    translateRenderedDashboard(document.body);
  }

  function showNoData(message, type = "warning") {
    const main = qs(".result-main");
    if (!main || qs(".dashboard-data-warning")) return;
    const box = document.createElement("div");
    box.className = `backend-status-box ${type} dashboard-data-warning`;
    box.textContent = message;
    main.prepend(box);
  }

  function clearStaticSamples() {
    updateDashboard({
      project_id: "—",
      dashboard: {
        project: { name: "—", report_id: "—", report_date: "—", status: Ltext("Data not loaded"), currency: "—", confidence: 0 },
        kpis: { planned_execution: null, actual_execution: null, schedule_gap_percent: null, delay_days: null, cost_variance_percent: null, workforce_current: null, workforce_required: null, risk_score: null, risk_level: null },
        forecast: { baseline_finish: null, estimated_finish: null, delay_impact_days: null },
        risk_components: {},
        executive_summary: Ltext("Generated project data is not available yet. Open this page after a completed upload and analysis flow."),
        risk_register: [{ risk: Ltext("Data not loaded"), level: Ltext("Medium"), reason: Ltext("No generated project ID was provided or the backend result could not be loaded."), action: Ltext("Return to the upload page and generate a dashboard from project files.") }],
        recommended_actions: [Ltext("Upload project files and generate a dashboard to replace these placeholders with real project-control results.")]
      }
    });
  }

  async function load() {
    clearStaticSamples();
    const projectId = getProjectId();
    if (!projectId) {
      showNoData(Ltext("No project_id was provided. Static sample values have been removed; generated data will appear after upload."), "warning");
      return;
    }
    try {
      if (window.DevBareunAPI && window.DevBareunAPI.getDashboard) {
        updateDashboard(await window.DevBareunAPI.getDashboard(projectId));
      } else {
        const token = getProjectToken(projectId);
        const headers = token ? { "X-Project-Token": token } : {};
        const res = await fetch(`${API_BASE}/api/projects/${projectId}/dashboard`, { headers });
        if (!res.ok) throw new Error(await res.text() || "Dashboard not found");
        updateDashboard(await res.json());
      }
    } catch (err) {
      console.error(err);
      clearStaticSamples();
      showNoData(Ltext("Generated dashboard data could not be loaded. Static sample values were removed to avoid misleading results."), "error");
    }
  }

  document.addEventListener("DOMContentLoaded", load);
  document.addEventListener("devbareun:lang", () => { if (latestDashboard) setTimeout(() => updateDashboard(latestDashboard), 0); });
  load();
})();


/* DevBareun v1.2.11 — stable print/download binding and per-result export clarity */
(function(){
  function qs(sel){return document.querySelector(sel);}
  function lang(){try{return localStorage.getItem('devbareun_report_lang')||localStorage.getItem('devbareun_lang')||document.documentElement.lang||'en';}catch(e){return 'en';}}
  function updatePrintLabel(){var b=qs('#printDashboardBtn'); if(b){b.textContent=String(lang()).toLowerCase().startsWith('az')?'Çap et':'Print';}}
  document.addEventListener('DOMContentLoaded',function(){
    updatePrintLabel();
    var b=qs('#printDashboardBtn');
    if(b && !b.dataset.v1211PrintBound){
      b.dataset.v1211PrintBound='true';
      b.addEventListener('click',function(e){e.preventDefault(); setTimeout(function(){window.print();},40);},true);
    }
  });
  document.addEventListener('devbareun:lang',updatePrintLabel);
})();


/* DevBareun v1.2.12 — active share link binding */
(function(){
  function qs(sel){return document.querySelector(sel);}
  function isAz(){try{return (localStorage.getItem('devbareun_lang')||document.documentElement.lang||'en').toLowerCase().startsWith('az');}catch(e){return false;}}
  function label(key){
    var az=isAz();
    var dict={
      share: az?'Link paylaş':'Share Link',
      copied: az?'Link kopyalandı':'Link copied',
      failed: az?'Link kopyalanmadı':'Copy failed',
      unsupported: az?'Paylaşım linki hazırdır':'Share link ready'
    };
    return dict[key]||key;
  }
  function projectId(){return new URLSearchParams(location.search).get('project_id')||'';}
  function buildShareUrl(){
    var url=new URL(location.href);
    var pid=projectId();
    if(pid) url.searchParams.set('project_id',pid);
    url.searchParams.delete('token');
    url.hash='';
    return url.toString();
  }
  function showShareToast(message){
    var old=qs('.db-share-toast');
    if(old) old.remove();
    var el=document.createElement('div');
    el.className='db-share-toast';
    el.textContent=message;
    document.body.appendChild(el);
    requestAnimationFrame(function(){el.classList.add('show');});
    setTimeout(function(){el.classList.remove('show'); setTimeout(function(){el.remove();},240);},2200);
  }
  async function copyText(text){
    if(navigator.clipboard && window.isSecureContext){
      await navigator.clipboard.writeText(text);
      return true;
    }
    var ta=document.createElement('textarea');
    ta.value=text;
    ta.setAttribute('readonly','');
    ta.style.position='fixed';
    ta.style.left='-9999px';
    document.body.appendChild(ta);
    ta.select();
    var ok=document.execCommand('copy');
    ta.remove();
    return ok;
  }
  function bindShare(){
    var btn=qs('#shareDashboardBtn');
    if(!btn || btn.dataset.v1212ShareBound) return;
    btn.dataset.v1212ShareBound='true';
    btn.textContent=label('share');
    btn.addEventListener('click',async function(e){
      e.preventDefault();
      var url=buildShareUrl();
      var title=document.title||'DevBareun Project Result Dashboard';
      try{
        if(navigator.share && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)){
          await navigator.share({title:title,url:url});
          showShareToast(label('unsupported'));
          return;
        }
        var ok=await copyText(url);
        var prev=btn.textContent;
        btn.textContent=ok?label('copied'):label('failed');
        showShareToast(ok?label('copied'):label('failed'));
        setTimeout(function(){btn.textContent=label('share');},1600);
      }catch(err){
        console.warn('Share failed',err);
        try{await copyText(url); showShareToast(label('copied'));}catch(e2){showShareToast(label('failed'));}
        setTimeout(function(){btn.textContent=label('share');},1600);
      }
    });
  }
  document.addEventListener('DOMContentLoaded',bindShare);
  document.addEventListener('devbareun:lang',function(){var b=qs('#shareDashboardBtn'); if(b)b.textContent=label('share');});
})();
