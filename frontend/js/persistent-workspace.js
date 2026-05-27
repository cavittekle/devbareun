/*
DevBareun Persistent Workspace
v1.3.8 — Report Archive + saved dashboards + authenticated exports + A4/A3 print bridge.
*/
(function () {
  "use strict";

  const DEFAULT_REMOTE_API = (location.protocol === "file:" || location.hostname === "localhost" || location.hostname === "127.0.0.1")
    ? `http://${location.hostname === "localhost" ? "127.0.0.1" : location.hostname}:8000`
    : "https://devbareun-production.up.railway.app";
  const API_BASE = (localStorage.getItem("devbareun_api_base") || window.DEVBAREUN_API_URL || DEFAULT_REMOTE_API).replace(/\/$/, "");
  const API = () => window.DevBareunAuth?.api;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  function formatDate(ts) {
    if (!ts) return "—";
    if (typeof ts === "string" && /\d{4}-\d{2}-\d{2}/.test(ts)) return new Date(ts).toLocaleString();
    return new Date(Number(ts) * 1000).toLocaleString();
  }

  function safeText(value) {
    return value === null || value === undefined || value === "" ? "—" : String(value);
  }

  function esc(value) {
    return String(value ?? "").replace(/[&<>\"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[ch]));
  }

  async function downloadWithAuth(url, fallbackName) {
    const session = window.DevBareunAuth?.getSession?.();
    const headers = session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {};
    const response = await fetch(url, { headers });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || `Export failed (${response.status})`);
    }
    const blob = await response.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = fallbackName || "DevBareun_Report";
    document.body.appendChild(a);
    a.click();
    URL.revokeObjectURL(a.href);
    a.remove();
  }

  function firstDefined(...values) {
    return values.find(v => v !== undefined && v !== null && v !== "") ?? null;
  }

  function normalizeAnalysisType(value) {
    const v = String(value || "all").toLowerCase();
    if (v.includes("schedule")) return "schedule";
    if (v.includes("cost")) return "cost";
    if (v.includes("material")) return "material";
    if (v.includes("risk")) return "risk";
    return "all";
  }

  function packageLabel(value) {
    const map = {
      all: "Full Project Control",
      schedule: "Schedule Recovery",
      cost: "Cost & Payment Control",
      material: "Material Continuity",
      risk: "Risk & Decisions",
    };
    return map[normalizeAnalysisType(value)] || safeText(value);
  }

  function dashboardRoot(record) {
    const payload = record?.dashboard || record?.report_payload || record?.result_json || {};
    if (payload.dashboard?.project || payload.dashboard?.kpis) return payload.dashboard;
    if (payload.project || payload.kpis) return payload;
    if (record?.report_payload?.dashboard?.project) return record.report_payload.dashboard;
    return payload;
  }

  function reportTitle(record) {
    const d = dashboardRoot(record);
    return firstDefined(record.title, record.project_name, d.project?.name, record.project_id, "Project report");
  }

  function reportId(record) {
    const d = dashboardRoot(record);
    return firstDefined(record.report_id, d.project?.report_id, d.project?.result_id, record.analysis_id, "—");
  }

  function recordToArchiveRow(record) {
    const d = dashboardRoot(record);
    const p = d.project || {};
    const k = d.kpis || record.kpis || {};
    return {
      report_id: reportId(record),
      analysis_id: record.analysis_id || p.analysis_id || "—",
      project_id: record.project_id || p.project_id || "—",
      project_name: reportTitle(record),
      analysis_type: record.analysis_type || p.analysis_type || p.dashboard_type || "all",
      status: record.status || p.status || "archived",
      risk_level: k.risk_level || p.status || "—",
      confidence: p.confidence || record.confidence_score || "—",
      print_size: record.print_size || "A4",
      language: record.language || "en",
      created_at_ts: record.created_at_ts || record.created_at || record.completed_at,
      source: record.source || "analysis",
    };
  }

  async function loadProjects() {
    const mount = $("#workspaceProjectsList");
    if (!mount || !API()) return;
    mount.innerHTML = `<p class="muted">Loading projects...</p>`;
    try {
      const data = await API()("/api/workspace/projects");
      const projects = data.projects || [];
      if (!projects.length) {
        mount.innerHTML = `<div class="empty-state">No saved projects yet. Create your first project to start persistent analysis history.</div>`;
        return;
      }
      mount.innerHTML = projects.map((p) => `
        <article class="workspace-row-card">
          <div>
            <strong>${esc(safeText(p.project_name))}</strong>
            <small>${esc(safeText(p.project_id))} · ${esc(safeText(p.location))} · ${esc(formatDate(p.created_at_ts))}</small>
          </div>
          <a class="btn btn-ghost btn-small" href="/upload.html?project_id=${encodeURIComponent(p.project_id)}">Upload files</a>
        </article>
      `).join("");
    } catch (err) {
      mount.innerHTML = `<div class="empty-state error">${esc(err.message)}</div>`;
    }
  }

  async function fetchAnalyses() {
    if (!API()) return [];
    const data = await API()("/api/workspace/analysis");
    return data.analyses || [];
  }

  async function fetchReportArchive() {
    if (!API()) return [];
    try {
      const data = await API()("/api/workspace/reports");
      const reports = data.reports || [];
      if (reports.length) return reports;
    } catch (err) {
      console.warn("Report archive endpoint unavailable, falling back to analysis history.", err);
    }
    return fetchAnalyses();
  }

  function renderArchiveStats(rows) {
    const mount = $("#reportArchiveStats");
    if (!mount) return;
    const total = rows.length;
    const a3 = rows.filter(r => String(r.print_size || "").toUpperCase() === "A3").length;
    const highRisk = rows.filter(r => /high|critical|risk/i.test(String(r.risk_level || r.status || ""))).length;
    const projects = new Set(rows.map(r => r.project_id).filter(Boolean)).size;
    mount.innerHTML = [
      ["Reports", total],
      ["Projects", projects],
      ["High attention", highRisk],
      ["A3-ready", a3 || total],
    ].map(([label, value]) => `<article class="report-stat-card"><span>${esc(label)}</span><strong>${esc(value)}</strong></article>`).join("");
  }

  function renderReportArchiveRows(records) {
    const mount = $("#workspaceReportArchive") || $("#workspaceAnalysisList");
    if (!mount) return;
    const rows = records.map(recordToArchiveRow);
    renderArchiveStats(rows);
    const search = $("#reportArchiveSearch");
    const type = $("#reportArchiveType");

    function filteredRows() {
      const q = String(search?.value || "").toLowerCase().trim();
      const t = String(type?.value || "all");
      return rows.filter(row => {
        const matchesQ = !q || [row.report_id, row.analysis_id, row.project_id, row.project_name, row.status].join(" ").toLowerCase().includes(q);
        const rowType = normalizeAnalysisType(row.analysis_type);
        const matchesT = t === "all" || (t === "all-project-control" ? rowType === "all" : rowType === t);
        return matchesQ && matchesT;
      });
    }

    function render() {
      const list = filteredRows();
      if (!list.length) {
        mount.innerHTML = `<div class="empty-state">No reports match the selected archive filters.</div>`;
        return;
      }
      mount.innerHTML = `<div class="report-archive-list">${list.map(row => {
        const analysisParam = row.analysis_id && row.analysis_id !== "—" ? `id=${encodeURIComponent(row.analysis_id)}` : `report_id=${encodeURIComponent(row.report_id)}`;
        const projectId = row.project_id && row.project_id !== "—" ? row.project_id : "";
        const pdf = projectId ? `${API_BASE}/api/projects/${encodeURIComponent(projectId)}/report/pdf?lang=${encodeURIComponent(row.language || "en")}` : "#";
        const xlsx = projectId ? `${API_BASE}/api/projects/${encodeURIComponent(projectId)}/report/excel?lang=${encodeURIComponent(row.language || "en")}` : "#";
        return `
          <article class="report-archive-card">
            <div>
              <h3>${esc(row.project_name)}</h3>
              <small>Report: ${esc(row.report_id)} · Analysis: ${esc(row.analysis_id)}<br>Project: ${esc(row.project_id)} · ${esc(formatDate(row.created_at_ts))}</small>
            </div>
            <div><span class="report-chip">${esc(packageLabel(row.analysis_type))}</span></div>
            <div><small>Status</small><strong>${esc(row.status)}</strong><br><small>Confidence: ${esc(row.confidence)}</small></div>
            <div class="report-archive-actions">
              <a class="report-mini-btn primary" href="/analysis-view.html?${analysisParam}">Open</a>
              <a class="report-mini-btn" href="/analysis-view.html?${analysisParam}&print=A4&auto=print">A4 print</a>
              <a class="report-mini-btn" href="/analysis-view.html?${analysisParam}&print=A3&auto=print">A3 print</a>
              ${projectId ? `<button class="report-mini-btn" data-auth-download="${esc(pdf)}&paper=a4" data-download-name="${esc(row.report_id)}_A4.pdf">PDF</button><button class="report-mini-btn" data-auth-download="${esc(xlsx)}" data-download-name="${esc(row.report_id)}.xlsx">Excel</button>` : ""}
            </div>
          </article>`;
      }).join("")}</div>`;
      document.dispatchEvent(new CustomEvent("devbareun:reports-rendered"));
    }

    search?.addEventListener("input", render);
    type?.addEventListener("change", render);
    render();
  }

  async function loadReportArchive() {
    const mount = $("#workspaceReportArchive") || $("#workspaceAnalysisList");
    if (!mount || !API()) return;
    mount.innerHTML = `<p class="muted">Loading report archive...</p>`;
    try {
      const records = await fetchReportArchive();
      if (!records.length) {
        renderArchiveStats([]);
        mount.innerHTML = `<div class="empty-state">No saved reports yet. Generated dashboards and report exports will appear here.</div>`;
        return;
      }
      renderReportArchiveRows(records);
    } catch (err) {
      mount.innerHTML = `<div class="empty-state error">${esc(err.message)}</div>`;
    }
  }

  async function loadAnalyses() {
    const mount = $("#workspaceAnalysisList");
    if (!mount || $("#workspaceReportArchive") || !API()) return;
    return loadReportArchive();
  }

  function bindProjectCreate() {
    const form = $("#workspaceProjectForm");
    if (!form || !API()) return;
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const status = $("#workspaceProjectStatus");
      const payload = Object.fromEntries(new FormData(form).entries());
      if (payload.contract_value) payload.contract_value = Number(payload.contract_value);
      try {
        if (status) status.textContent = "Saving project...";
        await API()("/api/workspace/projects", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        if (status) status.textContent = "Project saved.";
        form.reset();
        await loadProjects();
      } catch (err) {
        if (status) status.textContent = err.message;
      }
    });
  }

  function kpiItems(d) {
    const k = d.kpis || {};
    return [
      ["Planned", k.planned_execution != null ? `${k.planned_execution}%` : "—"],
      ["Actual", k.actual_execution != null ? `${k.actual_execution}%` : "—"],
      ["Delay", k.delay_days != null ? `+${k.delay_days} days` : "—"],
      ["Cost variance", k.cost_variance_percent != null ? `${k.cost_variance_percent}%` : "—"],
      ["Workforce", firstDefined(k.workforce_current, "—")],
      ["Risk", firstDefined(k.risk_level, k.risk_score != null ? `${k.risk_score}/100` : "—")],
    ];
  }

  function renderRiskRows(d) {
    const risks = Array.isArray(d.risk_register) ? d.risk_register : [];
    if (!risks.length) return `<tr><td colspan="4">No risk register rows are available in this saved report.</td></tr>`;
    return risks.slice(0, 10).map(r => `<tr><td>${esc(r.risk || r.title || "—")}</td><td>${esc(r.level || r.status || "—")}</td><td>${esc(r.reason || r.cause || "—")}</td><td>${esc(r.action || r.recommendation || "—")}</td></tr>`).join("");
  }

  function renderActions(d) {
    const actions = Array.isArray(d.recommended_actions) ? d.recommended_actions : [];
    if (!actions.length) return `<li>No recommended action was saved with this report.</li>`;
    return actions.slice(0, 8).map((a, i) => `<li><b>${String(i + 1).padStart(2, "0")}</b>${esc(a)}</li>`).join("");
  }

  function renderPrintableReport(record) {
    const d = dashboardRoot(record);
    const p = d.project || {};
    const title = reportTitle(record);
    const report = reportId(record);
    const analysisId = record.analysis_id || p.analysis_id || "—";
    const projectId = record.project_id || p.project_id || "—";
    const lang = record.language || localStorage.getItem("devbareun_report_lang") || localStorage.getItem("devbareun_lang") || "en";
    const projectForExport = projectId !== "—" ? projectId : "";
    const pdf = projectForExport ? `${API_BASE}/api/projects/${encodeURIComponent(projectForExport)}/report/pdf?lang=${encodeURIComponent(lang)}` : "#";
    const xlsx = projectForExport ? `${API_BASE}/api/projects/${encodeURIComponent(projectForExport)}/report/excel?lang=${encodeURIComponent(lang)}` : "#";

    return `
      <div class="report-action-toolbar db-screen-only">
        <a class="btn btn-ghost" href="/reports.html">Back to archive</a>
        <div class="report-archive-filters">
          <select class="db-print-size-select" aria-label="Print size"><option value="A4">A4</option><option value="A3">A3</option></select>
          <button class="btn btn-primary db-print-btn" data-print-size="auto">Print</button>
          <button class="btn btn-ghost" data-print-size="A4">Print A4</button>
          <button class="btn btn-ghost" data-print-size="A3">Print A3</button>
          ${projectForExport ? `<button class="btn btn-ghost" data-auth-download="${esc(pdf)}&paper=a4" data-download-name="${esc(report)}_A4.pdf">PDF A4</button><button class="btn btn-ghost" data-auth-download="${esc(pdf)}&paper=a3" data-download-name="${esc(report)}_A3.pdf">PDF A3</button><button class="btn btn-ghost" data-auth-download="${esc(xlsx)}" data-download-name="${esc(report)}.xlsx">Excel</button>` : ""}
        </div>
      </div>
      <article class="report-print-preview">
        <div class="report-print-cover">
          <div>
            <p class="eyebrow">Saved DevBareun report</p>
            <h1>${esc(title)}</h1>
            <p>${esc(d.executive_summary || p.dashboard_description || "Saved project-control report generated from uploaded construction project data.")}</p>
          </div>
          <span class="report-chip">${esc(packageLabel(record.analysis_type || p.analysis_type))}</span>
        </div>
        <div class="report-meta-grid">
          <div class="report-meta-item"><span>Report ID</span><strong>${esc(report)}</strong></div>
          <div class="report-meta-item"><span>Analysis ID</span><strong>${esc(analysisId)}</strong></div>
          <div class="report-meta-item"><span>Project ID</span><strong>${esc(projectId)}</strong></div>
          <div class="report-meta-item"><span>Date</span><strong>${esc(formatDate(record.created_at_ts || record.created_at || p.report_date))}</strong></div>
        </div>
        <div class="report-kpi-grid">
          ${kpiItems(d).map(([label, value]) => `<div class="report-kpi-card"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`).join("")}
        </div>
        <h2 class="report-section-title">Risk register</h2>
        <table class="report-print-table">
          <thead><tr><th>Risk</th><th>Level</th><th>Reason</th><th>Action</th></tr></thead>
          <tbody>${renderRiskRows(d)}</tbody>
        </table>
        <h2 class="report-section-title">Recommended actions</h2>
        <ol class="report-action-list">${renderActions(d)}</ol>
        <details class="report-json-details">
          <summary>Technical payload</summary>
          <pre>${esc(JSON.stringify(record.dashboard || record.report_payload || record.result_json || {}, null, 2))}</pre>
        </details>
      </article>`;
  }

  async function loadAnalysisView() {
    const mount = $("#savedAnalysisView");
    if (!mount || !API()) return;
    const params = new URLSearchParams(location.search);
    const analysisId = params.get("id");
    const rid = params.get("report_id");
    if (!analysisId && !rid) {
      mount.innerHTML = `<div class="empty-state error">Missing analysis or report ID.</div>`;
      return;
    }
    try {
      let record;
      if (rid) {
        const data = await API()(`/api/workspace/reports/${encodeURIComponent(rid)}`);
        record = data.report;
      } else {
        const data = await API()(`/api/workspace/analysis/${encodeURIComponent(analysisId)}`);
        record = data.analysis;
      }
      mount.innerHTML = renderPrintableReport(record);
      document.dispatchEvent(new CustomEvent("devbareun:reports-rendered"));
    } catch (err) {
      mount.innerHTML = `<div class="empty-state error">${esc(err.message)}</div>`;
    }
  }

  document.addEventListener("click", async (event) => {
    const btn = event.target.closest("[data-auth-download]");
    if (!btn) return;
    event.preventDefault();
    const original = btn.textContent;
    try {
      btn.disabled = true;
      btn.textContent = "Preparing...";
      await downloadWithAuth(btn.getAttribute("data-auth-download"), btn.getAttribute("data-download-name"));
    } catch (err) {
      alert(err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = original;
    }
  });

  document.addEventListener("DOMContentLoaded", () => {
    bindProjectCreate();
    loadProjects();
    loadReportArchive();
    loadAnalyses();
    loadAnalysisView();
  });

  window.DevBareunWorkspace = {
    loadProjects,
    loadAnalyses,
    loadReportArchive,
  };
})();
