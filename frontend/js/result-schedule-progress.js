(function () {
  function n(value, fallback = 0) {
    const v = Number(value);
    return Number.isFinite(v) ? v : fallback;
  }
  function clamp(value, min = 0, max = 100) { return Math.max(min, Math.min(max, n(value))); }
  function hasValue(v) { return v !== undefined && v !== null && v !== ""; }
  function riskClass(levelOrValue) {
    const s = String(levelOrValue || "").toLowerCase();
    const v = Number(levelOrValue);
    if (s.includes("critical") || s.includes("high") || v >= 70) return "danger";
    if (s.includes("medium") || s.includes("watch") || v >= 40) return "warn";
    return "good";
  }
  function statusChipClass(level) {
    const c = riskClass(level);
    if (c === "danger") return "spd-status-chip";
    if (c === "warn") return "spd-status-chip watch";
    return "spd-status-chip ok";
  }
  function fmtPct(value) { return hasValue(value) ? `${Number(value).toFixed(Number(value) % 1 ? 1 : 0)}%` : "—"; }
  function fmtDays(value) { return hasValue(value) ? (window.DevBareunI18n ? window.DevBareunI18n.days(value) : `${Number(value) > 0 ? "+" : ""}${Number(value).toFixed(0)} days`) : "—"; }
  function escapeHtml(value) { return String(value ?? "").replace(/[&<>\"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[ch])); }
  function isAz() { return !!(window.DevBareunI18n && window.DevBareunI18n.isAz()); }
  function Ltext(value) { return window.DevBareunI18n ? window.DevBareunI18n.text(value) : value; }
  function Llabel(value) { return window.DevBareunI18n ? window.DevBareunI18n.label(value) : value; }

  function getMode(d) {
    const p = d.project || {};
    const s = d.dashboard_sections || {};
    return String(s.mode || p.analysis_type || p.dashboard_type || "").toLowerCase();
  }
  function shouldRender(d) {
    const mode = getMode(d);
    const title = String((d.project || {}).dashboard_title || (d.dashboard_sections || {}).title || "").toLowerCase();
    return ["schedule", "delay", "progress", "full", "executive"].some(k => mode.includes(k) || title.includes(k));
  }

  function extractTrend(d) {
    const k = d.kpis || {};
    const series = d.plan_actual_series || d.progress_series || d.schedule_series || (d.dashboard_sections || {}).plan_actual_series;
    if (Array.isArray(series) && series.length) {
      return series.slice(0, 6).map((row, i) => ({
        label: row.label || row.month || row.period || `P${i + 1}`,
        planned: clamp(row.planned ?? row.plan ?? row.planned_progress ?? k.planned_execution),
        actual: clamp(row.actual ?? row.fact ?? row.actual_progress ?? k.actual_execution)
      }));
    }
    const p = hasValue(k.planned_execution) ? clamp(k.planned_execution) : 0;
    const a = hasValue(k.actual_execution) ? clamp(k.actual_execution) : 0;
    const labels = ["P1","P2","P3","P4","P5","P6"];
    return labels.map((label, i) => ({ label, planned: Math.round(p * (i + 1) / 6), actual: Math.round(a * (i + 1) / 6) }));
  }

  function extractActivities(d) {
    const keys = ["buildings", "blocks", "activities", "schedule_activities", "activity_status", "work_packages"];
    for (const key of keys) {
      if (Array.isArray(d[key]) && d[key].length) return d[key];
    }
    const panels = ((d.dashboard_sections || {}).panels || []);
    const rows = [];
    panels.forEach(panel => (panel.rows || []).forEach(row => {
      if (row.label || row.activity || row.name) rows.push(row);
    }));
    return rows.slice(0, 10);
  }

  function normalizeActivity(row, index) {
    const planned = row.planned ?? row.plan ?? row.planned_progress ?? row.planned_execution ?? row.target;
    const actual = row.actual ?? row.fact ?? row.actual_progress ?? row.actual_execution ?? row.value;
    const delay = row.delay_days ?? row.delay ?? row.variance_days;
    const name = Ltext(row.name || row.activity || row.activity_name || row.building || row.block || row.label || `Activity ${index + 1}`);
    const status = Ltext(row.status || row.risk || row.level || (hasValue(delay) && Number(delay) > 0 ? "Delayed" : "Review"));
    const note = Ltext(row.note || row.comment || row.action || row.description || row.reason || "Plan/fact comparison is based on detected or confirmed uploaded data.");
    return { name, planned, actual, delay, status, note };
  }

  function renderBuildings(rows) {
    if (!rows.length) return `<div class="spd-empty">${escapeHtml(Ltext("No building/activity-level rows were detected. Upload plan and actual status by building, block, WBS or activity to populate this section."))}</div>`;
    return `<div class="spd-building-grid">${rows.slice(0, 10).map((row, i) => {
      const r = normalizeActivity(row, i);
      const cls = riskClass(r.status || r.delay);
      const color = cls === "danger" ? "#fb7185" : cls === "warn" ? "#f59e0b" : "#22d3ee";
      return `<article class="spd-building" style="--accent:${color}">
        <div class="spd-building-head"><h3>${escapeHtml(r.name)}</h3><span class="spd-badge">${escapeHtml(Ltext(r.status || "Review"))}</span></div>
        <small>${escapeHtml(Llabel("Plan vs Actual"))}</small>
        <div class="spd-small-progress">
          <div class="spd-small-line"><span>${escapeHtml(Llabel("Plan"))}</span><b class="spd-small-track"><i style="--w:${clamp(r.planned)}%"></i></b><em>${fmtPct(r.planned)}</em></div>
          <div class="spd-small-line"><span>${escapeHtml(Llabel("Actual"))}</span><b class="spd-small-track actual"><i style="--w:${clamp(r.actual)}%"></i></b><em>${fmtPct(r.actual)}</em></div>
        </div>
        <p>${escapeHtml(r.note)}</p>
        ${hasValue(r.delay) ? `<p><strong>${fmtDays(r.delay)}</strong> ${escapeHtml(Llabel("delay impact"))}</p>` : ""}
      </article>`;
    }).join("")}</div>`;
  }

  function renderActivityTable(rows) {
    if (!rows.length) return `<div class="spd-empty">${escapeHtml(Ltext("No detailed activity table is available for this result."))}</div>`;
    return `<div class="spd-table-wrap"><table class="spd-table"><thead><tr>
      <th>${escapeHtml(Llabel("Activity / Building"))}</th><th>${escapeHtml(Llabel("Planned"))}</th><th>${escapeHtml(Llabel("Actual"))}</th><th>${escapeHtml(Llabel("Gap"))}</th><th>${escapeHtml(Llabel("Delay"))}</th><th>${escapeHtml(Llabel("Status"))}</th><th>${escapeHtml(Llabel("Management note"))}</th>
    </tr></thead><tbody>${rows.slice(0, 18).map((row, i) => {
      const r = normalizeActivity(row, i);
      const gap = hasValue(r.planned) && hasValue(r.actual) ? Number(r.actual) - Number(r.planned) : null;
      return `<tr>
        <td>${escapeHtml(r.name)}</td>
        <td>${fmtPct(r.planned)}</td>
        <td>${fmtPct(r.actual)}</td>
        <td>${hasValue(gap) ? fmtPct(gap) : "—"}</td>
        <td>${fmtDays(r.delay)}</td>
        <td>${escapeHtml(Ltext(r.status || "Review"))}</td>
        <td>${escapeHtml(r.note)}</td>
      </tr>`;
    }).join("")}</tbody></table></div>`;
  }

  window.renderScheduleProgressDashboard = function (mount, d) {
    if (!mount || !shouldRender(d)) return false;
    const p = d.project || {};
    const k = d.kpis || {};
    const f = d.forecast || {};
    const components = d.risk_components || {};
    const actions = d.recommended_actions || [];
    const trend = extractTrend(d);
    const activities = extractActivities(d);
    const riskLevel = k.risk_level || p.status || "Review";
    const planned = clamp(k.planned_execution);
    const actual = clamp(k.actual_execution);
    const gap = hasValue(k.schedule_gap_percent) ? -Math.abs(Number(k.schedule_gap_percent)) : (hasValue(k.actual_execution) && hasValue(k.planned_execution) ? Number(k.actual_execution) - Number(k.planned_execution) : null);
    const mode = getMode(d) || "schedule / progress";

    const actionHtml = actions.length
      ? actions.slice(0, 6).map((a, i) => `<div class="spd-action"><strong>${String(i + 1).padStart(2, "0")}</strong><br>${escapeHtml(Ltext(a))}</div>`).join("")
      : `<div class="spd-empty">${escapeHtml(Ltext("Recommended management actions will appear after confirmed plan and actual data is available."))}</div>`;

    mount.innerHTML = `<div class="schedule-progress-dashboard">
      <section class="spd-top">
        <article class="spd-panel spd-project-card">
          <div class="spd-eyebrow"><i></i><span>${escapeHtml(Ltext(String(mode).toUpperCase()))} ${escapeHtml(Llabel("DASHBOARD"))}</span></div>
          <h2 class="spd-project-title">${escapeHtml(p.name || Ltext(p.dashboard_title || "Plan vs Actual Project Dashboard"))}</h2>
          <p class="spd-summary">${escapeHtml(Ltext(d.executive_summary || p.dashboard_description || "Plan, actual progress, delay exposure, activity status and recommended actions are shown from confirmed uploaded project-control data."))}</p>
          <div class="spd-meta-grid">
            <div class="spd-meta"><span>${escapeHtml(Llabel("Report ID"))}</span><strong>${escapeHtml(p.report_id || "—")}</strong></div>
            <div class="spd-meta"><span>${escapeHtml(Llabel("Status"))}</span><strong>${escapeHtml(Ltext(p.status || "Review"))}</strong></div>
            <div class="spd-meta"><span>${escapeHtml(Llabel("Baseline finish"))}</span><strong>${escapeHtml(f.baseline_finish || "—")}</strong></div>
            <div class="spd-meta"><span>${escapeHtml(Llabel("Estimated finish"))}</span><strong>${escapeHtml(f.estimated_finish || "—")}</strong></div>
          </div>
        </article>
        <article class="spd-panel spd-status-card">
          <span class="${statusChipClass(riskLevel)}">${escapeHtml(Ltext(riskLevel))}</span>
          <div>
            <div class="spd-status-value">${hasValue(k.risk_score) ? `${k.risk_score}/100` : "—"}</div>
            <p class="spd-status-note">${escapeHtml(Ltext("Risk score reflects plan/fact gap, delay, workforce, cost and procurement signals where available."))}</p>
          </div>
        </article>
      </section>

      <section class="spd-kpi-grid">
        <article class="spd-panel spd-kpi info"><span>${escapeHtml(Llabel("Planned execution"))}</span><strong>${fmtPct(k.planned_execution)}</strong><p>${escapeHtml(Ltext("Baseline target from plan data."))}</p></article>
        <article class="spd-panel spd-kpi ${hasValue(gap) && gap < 0 ? "danger" : "good"}"><span>${escapeHtml(Llabel("Actual execution"))}</span><strong>${fmtPct(k.actual_execution)}</strong><p>${hasValue(gap) ? `${escapeHtml(Llabel("Gap"))}: ${fmtPct(gap)}` : escapeHtml(Ltext("Actual data required for comparison."))}</p></article>
        <article class="spd-panel spd-kpi ${riskClass(k.delay_days)}"><span>${escapeHtml(Llabel("Delay impact"))}</span><strong>${fmtDays(k.delay_days ?? f.delay_impact_days)}</strong><p>${escapeHtml(Ltext("Against baseline or planned finish."))}</p></article>
        <article class="spd-panel spd-kpi warn"><span>${escapeHtml(Llabel("Activities checked"))}</span><strong>${activities.length || "—"}</strong><p>${escapeHtml(Ltext("Building, block, WBS or activity rows."))}</p></article>
        <article class="spd-panel spd-kpi info"><span>${escapeHtml(Llabel("Workforce"))}</span><strong>${hasValue(k.workforce_current) ? k.workforce_current : "—"}</strong><p>${hasValue(k.workforce_required) ? (isAz() ? `Tələb olunan: ${k.workforce_required}` : `Required: ${k.workforce_required}`) : escapeHtml(Ltext("Required workforce not detected."))}</p></article>
        <article class="spd-panel spd-kpi ${riskClass(riskLevel)}"><span>${escapeHtml(Llabel("Risk level"))}</span><strong>${escapeHtml(Ltext(k.risk_level || "—"))}</strong><p>${escapeHtml(Ltext("Management attention level."))}</p></article>
      </section>

      <section class="spd-panel spd-timeline">
        <div class="spd-timeline-head"><div><div class="spd-mini-title">${escapeHtml(Llabel("Project timeline"))}</div><div class="spd-title">${escapeHtml(Llabel("Plan progress vs actual progress"))}</div></div><div class="spd-timeline-meta"><span>${escapeHtml(Llabel("Plan"))} ${fmtPct(planned)}</span><span>${escapeHtml(Llabel("Actual"))} ${fmtPct(actual)}</span><span>${escapeHtml(Llabel("Gap"))} ${hasValue(gap) ? fmtPct(gap) : "—"}</span></div></div>
        <div class="spd-progress-track" style="--planned:${planned}%;--actual:${actual}%;--today:${Math.max(5, Math.min(95, planned || 50))}%"><i class="spd-progress-plan"></i><i class="spd-progress-actual"></i><i class="spd-progress-today"></i></div>
        <div class="spd-timeline-scale">${[10,20,30,40,50,60,70,80,90,100].map(x => `<span>${x}%</span>`).join("")}</div>
      </section>

      <section class="spd-two-col">
        <article class="spd-panel spd-chart">
          <div class="spd-panel-head"><div><div class="spd-mini-title">${escapeHtml(Llabel("Trend"))}</div><div class="spd-title">${escapeHtml(Llabel("Plan and actual progress"))}</div></div><div class="spd-legend"><span><i class="plan"></i>${escapeHtml(Llabel("Plan"))}</span><span><i class="actual"></i>${escapeHtml(Llabel("Actual"))}</span></div></div>
          <div class="spd-bars">${trend.map(r => `<div class="spd-bar-group"><i class="spd-bar plan" style="height:${clamp(r.planned)}%"></i><i class="spd-bar actual" style="height:${clamp(r.actual)}%"></i><div class="spd-bar-label">${escapeHtml(r.label)}</div></div>`).join("")}</div>
        </article>
        <article class="spd-panel spd-risk-panel">
          <div class="spd-panel-head"><div><div class="spd-mini-title">${escapeHtml(Llabel("Risk"))}</div><div class="spd-title">${escapeHtml(Llabel("Risk pressure"))}</div></div></div>
          <div class="spd-risk-list">${["schedule","cost","labor","procurement","quality"].map(key => {
            const value = clamp(components[key]);
            return `<div class="spd-risk-row ${riskClass(value)}"><span class="spd-risk-label">${escapeHtml(Llabel(key))}</span><b class="spd-risk-track"><i class="spd-risk-fill" style="--v:${value}%"></i></b><em>${value || "—"}</em></div>`;
          }).join("")}</div>
        </article>
      </section>

      <section class="spd-panel spd-building-panel">
        <div class="spd-panel-head"><div><div class="spd-mini-title">${escapeHtml(Llabel("Execution status"))}</div><div class="spd-title">${escapeHtml(Llabel("Building / block / activity cards"))}</div></div></div>
        ${renderBuildings(activities)}
      </section>

      <section class="spd-panel spd-table-panel">
        <div class="spd-panel-head"><div><div class="spd-mini-title">${escapeHtml(Llabel("Detailed control table"))}</div><div class="spd-title">${escapeHtml(Llabel("Plan vs actual comparison"))}</div></div></div>
        ${renderActivityTable(activities)}
      </section>

      <section class="spd-panel spd-actions-panel">
        <div class="spd-panel-head"><div><div class="spd-mini-title">${escapeHtml(Llabel("Management actions"))}</div><div class="spd-title">${escapeHtml(Llabel("Recommended recovery actions"))}</div></div></div>
        <div class="spd-action-grid">${actionHtml}</div>
      </section>
    </div>`;
    return true;
  };
})();
