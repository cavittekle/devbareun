import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  Building2,
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  Clock3,
  Download,
  FileText,
  Fingerprint,
  Gauge,
  MapPin,
  Printer,
  ShieldAlert,
  TrendingUp,
  UsersRound
} from "lucide-react";
import { workspaceApi } from "../api/client";
import { EmptyState, PageHeader } from "../components/Shell";
import { PackageSegmentedControl } from "../components/PackageSegmentedControl";
import { analysisPackages } from "../data/packages";
import { demoWorkspace } from "../data/demoWorkspace";

const EMPTY = "-";

function compactJson(value) {
  if (!value || typeof value !== "object") return null;
  return JSON.stringify(value, null, 2);
}

function asArray(value) {
  if (Array.isArray(value)) return value;
  if (!value) return [];
  return [value];
}

function numberValue(value) {
  if (value === null || value === undefined || value === "") return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function pickMetric(rows, names) {
  const wanted = new Set(asArray(names));
  for (const row of asArray(rows)) {
    if (wanted.has(row?.name) || wanted.has(row?.metric) || wanted.has(row?.key)) return row?.value ?? row?.amount ?? null;
  }
  return null;
}

function formatNumber(value, options = {}) {
  const numeric = numberValue(value);
  if (numeric === null) return EMPTY;
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 1, ...options }).format(numeric);
}

function formatMoney(value, currency = "USD") {
  const numeric = numberValue(value);
  if (numeric === null) return EMPTY;
  const safeCurrency = typeof currency === "string" && /^[A-Z]{3}$/.test(currency) ? currency : "USD";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: safeCurrency,
    notation: Math.abs(numeric) >= 1000000 ? "compact" : "standard",
    maximumFractionDigits: Math.abs(numeric) >= 1000000 ? 1 : 0
  }).format(numeric);
}

function formatPercent(value) {
  const numeric = numberValue(value);
  if (numeric === null) return EMPTY;
  return `${formatNumber(numeric)}%`;
}

function formatDate(value) {
  if (!value) return EMPTY;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 16);
  return date.toLocaleDateString("en-GB", { year: "numeric", month: "short", day: "2-digit" });
}

function statusClass(value) {
  const text = String(value || "").toLowerCase();
  if (text.includes("critical") || text.includes("high") || text.includes("delayed") || text.includes("fail")) return "danger";
  if (text.includes("watch") || text.includes("medium") || text.includes("warning") || text.includes("missing")) return "warning";
  if (text.includes("track") || text.includes("low") || text.includes("complete") || text.includes("approved") || text.includes("verified") || text.includes("clean") || text.includes("released")) return "success";
  return "neutral";
}

function normalizePayload(payload) {
  const analysisRows = asArray(payload?.analysis_results).sort((left, right) => String(right?.created_at || "").localeCompare(String(left?.created_at || "")));
  const latestAnalysis = payload?.analysis_result || analysisRows[0] || null;
  const executive = payload?.dashboard || payload?.executive_dashboard || null;
  const rawDashboard = latestAnalysis?.dashboard_data || latestAnalysis?.result_json || payload?.guest_result || payload || {};
  const analyzerDashboard = rawDashboard?.dashboard || rawDashboard;
  const normalized = latestAnalysis?.normalized_data || rawDashboard?.normalized_data || {};
  const project = {
    ...(normalized?.project_info || {}),
    ...(payload?.project || {}),
    ...(rawDashboard?.project || {}),
    ...(analyzerDashboard?.project || {}),
    ...(executive?.project || {})
  };
  const kpis = executive?.kpis || analyzerDashboard?.kpis || rawDashboard?.metrics || {};
  const metrics = rawDashboard?.metrics || analyzerDashboard?.metrics || {};
  const schedule = executive?.schedule_performance || analyzerDashboard?.schedule_performance || rawDashboard?.schedule_performance || {};
  const scheduleRows = asArray(
    executive?.schedule_buildings ||
    analyzerDashboard?.schedule_buildings ||
    analyzerDashboard?.building_statuses ||
    analyzerDashboard?.buildings ||
    schedule?.buildings ||
    rawDashboard?.schedule_buildings
  );
  const costControl = executive?.cost_control || analyzerDashboard?.cost_control || rawDashboard?.cost_control || {};
  const costRows = asArray(
    costControl?.packages ||
    costControl?.cost_packages ||
    analyzerDashboard?.cost_packages ||
    rawDashboard?.cost_packages
  );
  const materialContinuity = executive?.material_continuity || analyzerDashboard?.material_continuity || rawDashboard?.material_continuity || {};
  const materialRows = asArray(
    materialContinuity?.inventory ||
    materialContinuity?.materials ||
    analyzerDashboard?.material_items ||
    rawDashboard?.material_items
  );
  const riskDecisions = executive?.risk_decisions || analyzerDashboard?.risk_decisions || rawDashboard?.risk_decisions || {};
  const riskDecisionRows = asArray(
    riskDecisions?.risks ||
    riskDecisions?.risk_items ||
    analyzerDashboard?.decision_risks ||
    rawDashboard?.decision_risks
  );
  const dataQuality = analyzerDashboard?.data_quality || {
    confidence: latestAnalysis?.confidence_score || rawDashboard?.confidence_score || executive?.management_summary?.confidence_score,
    warnings: rawDashboard?.warnings || normalized?.warnings || [],
    sheet_profiles: normalized?.evidence?.sheet_profiles || []
  };
  const primaryKpis = analyzerDashboard?.dashboard_sections?.primary_kpis || [];
  const risks = executive?.top_risks || analyzerDashboard?.top_risks || analyzerDashboard?.risk_register || latestAnalysis?.risk_data || [];
  const actions = analyzerDashboard?.recommended_actions || executive?.management_summary?.immediate_action || analyzerDashboard?.management_summary?.immediate_action || [];
  const currency = project?.currency || analyzerDashboard?.project?.currency || kpis?.currency || rawDashboard?.project?.currency || "USD";
  const provenance = executive?.analysis_provenance || latestAnalysis?.input_manifest || rawDashboard?.analysis_provenance || normalized?.analysis_provenance || {};

  return {
    project,
    kpis,
    metrics,
    normalized,
    schedule,
    scheduleRows,
    costControl,
    costRows,
    materialContinuity,
    materialRows,
    riskDecisions,
    riskDecisionRows,
    dataQuality,
    primaryKpis,
    risks: asArray(risks),
    actions: asArray(actions),
    reports: executive?.reports || payload?.reports || [],
    documentControl: executive?.document_control || rawDashboard?.document_control || normalized?.document_control || {},
    provenance,
    managementSummary: executive?.management_summary || analyzerDashboard?.management_summary || analyzerDashboard?.executive_summary || "",
    milestones: executive?.upcoming_milestones || analyzerDashboard?.upcoming_milestones || schedule?.milestones || rawDashboard?.milestones || [],
    title: project?.name || project?.project_name || project?.projectName || normalized?.project_info?.project_name || "Project result",
    status: project?.status || project?.current_status || analyzerDashboard?.project?.status || "Generated",
    packageId: analyzerDashboard?.package_id || rawDashboard?.package_id || latestAnalysis?.analysis_type || payload?.analysis_type || "",
    currency,
    lastUpdated: executive?.last_updated || latestAnalysis?.created_at || rawDashboard?.calculated_at || analyzerDashboard?.project?.report_date,
    rawForDebug: executive || analyzerDashboard || rawDashboard
  };
}

function kpiValue(model, key) {
  const { kpis, metrics, normalized, primaryKpis } = model;
  if (kpis?.[key] !== undefined) return kpis[key];
  if (metrics?.[key] !== undefined) return metrics[key];
  if (key === "total_budget") return pickMetric(normalized?.cost_data, ["total_budget", "total_cost", "contract_value"]);
  if (key === "actual_cost") return pickMetric(normalized?.cost_data, ["actual_cost", "approved_payment"]);
  if (key === "forecast_cost") return metrics?.forecast_cost || kpis?.forecast_cost;
  if (key === "planned_progress") return pickMetric(normalized?.progress_data, ["planned_progress_percent"]);
  if (key === "actual_progress") return pickMetric(normalized?.progress_data, ["actual_progress_percent"]);
  if (key === "delay_days") return model.schedule?.delay_days || pickMetric(primaryKpis, ["delay_days"]);
  if (key === "risk_score") return kpis?.risk_score || pickMetric(primaryKpis, ["risk_score"]);
  return null;
}

function KpiCard({ label, value, note, status = "neutral", icon: Icon = TrendingUp }) {
  return (
    <article className={`result-kpi-card ${status}`}>
      <div className="result-kpi-icon"><Icon size={18} /></div>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </article>
  );
}

function ProgressBar({ label, value, note }) {
  const numeric = Math.max(0, Math.min(100, numberValue(value) ?? 0));
  return (
    <div className="result-progress-row">
      <div>
        <strong>{label}</strong>
        <span>{note}</span>
      </div>
      <div className="result-progress-bar" aria-label={`${label}: ${numeric}%`}>
        <i style={{ width: `${numeric}%` }} />
      </div>
      <b>{formatPercent(value)}</b>
    </div>
  );
}

function SummaryPanel({ summary }) {
  if (!summary) return null;
  if (typeof summary === "string") {
    return <p className="result-summary-text">{summary}</p>;
  }
  const rows = [
    ["Overall status", summary.overall_status || summary.overall_project_status],
    ["Delay issue", summary.main_delay_reason || summary.main_delay_issue],
    ["Cost pressure", summary.cost_pressure || summary.main_cost_issue],
    ["Immediate action", summary.immediate_action || summary.recommended_next_decision]
  ].filter(([, value]) => value);
  if (!rows.length) return null;
  return (
    <div className="result-summary-list">
      {rows.map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

function RiskList({ risks }) {
  if (!risks.length) {
    return <div className="status-box info">No high-confidence risk register rows were returned.</div>;
  }
  return (
    <div className="result-risk-list">
      {risks.slice(0, 8).map((risk, index) => {
        const level = risk.level || risk.severity || risk.status || "Review";
        const title = risk.risk || risk.title || risk.risk_title || risk.category || `Risk ${index + 1}`;
        return (
          <article key={`${title}-${index}`}>
            <div>
              <strong>{title}</strong>
              <p>{risk.reason || risk.description || risk.explanation || risk.impact || "Review the uploaded source data for this item."}</p>
              {(risk.action || risk.recommended_action) && <small>Action: {risk.action || risk.recommended_action}</small>}
            </div>
            <span className={`status-pill ${statusClass(level)}`}>{level}</span>
          </article>
        );
      })}
    </div>
  );
}

function compactHash(value) {
  const text = String(value || "");
  if (!text) return EMPTY;
  return text.length > 18 ? `${text.slice(0, 10)}...${text.slice(-6)}` : text;
}

function InputProvenance({ provenance }) {
  const files = asArray(provenance?.files);
  if (!files.length) {
    return <div className="status-box info">This result predates source-provenance snapshots or did not retain any readable input files.</div>;
  }
  return (
    <div className="result-provenance">
      <div className="result-provenance-summary">
        <div><span>Source files</span><strong>{formatNumber(provenance?.file_count ?? files.length)}</strong></div>
        <div><span>Input fingerprint</span><strong title={provenance?.source_fingerprint || ""}>{compactHash(provenance?.source_fingerprint)}</strong></div>
        <div><span>Engine version</span><strong>{provenance?.analysis_engine_version || EMPTY}</strong></div>
      </div>
      <div className="result-provenance-files">
        {files.slice(0, 12).map((file, index) => {
          const integrity = file?.checksum_status || "not_provided";
          const screening = file?.security_scan_status || "pending";
          return (
            <article key={`${file?.file_id || file?.filename || "file"}-${index}`}>
              <div>
                <strong>{file?.filename || `Source file ${index + 1}`}</strong>
                <small>{file?.extension || "file"} - {formatNumber(file?.size_bytes)} bytes - hash: {file?.content_hash_source || "unavailable"}</small>
              </div>
              <div className="result-provenance-statuses">
                <span className={`status-pill ${statusClass(integrity)}`}>{integrity}</span>
                <span className={`status-pill ${statusClass(screening === "clean" ? "complete" : screening)}`}>{screening}</span>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function DataQuality({ dataQuality, documentControl }) {
  const warnings = asArray(dataQuality?.warnings);
  const confidence = dataQuality?.confidence ?? dataQuality?.readiness?.score ?? dataQuality?.premium?.overall_score;
  const sheetProfiles = asArray(dataQuality?.sheet_profiles || dataQuality?.readiness?.sheet_profiles);
  return (
    <div className="result-quality-grid">
      <article>
        <span>Confidence</span>
        <strong>{formatPercent(confidence)}</strong>
        <small>Parser and evidence confidence</small>
      </article>
      <article>
        <span>Uploaded files</span>
        <strong>{formatNumber(documentControl?.uploaded_files)}</strong>
        <small>{formatNumber(documentControl?.missing_documents)} missing document slots</small>
      </article>
      <article>
        <span>Detected sheets</span>
        <strong>{formatNumber(sheetProfiles.length)}</strong>
        <small>Sheet profiles used as evidence</small>
      </article>
      <article>
        <span>Warnings</span>
        <strong>{formatNumber(warnings.length)}</strong>
        <small>Data-quality issues requiring review</small>
      </article>
      {warnings.length > 0 && (
        <div className="result-warning-list">
          {warnings.slice(0, 6).map((warning, index) => <p key={`${warning}-${index}`}><AlertTriangle size={15} /> {warning}</p>)}
        </div>
      )}
    </div>
  );
}

function ResultSupportSections({ model, json, showRaw, onToggleRaw }) {
  return (
    <>
      <section className="panel result-provenance-panel">
        <div className="result-section-title"><Fingerprint size={20} /><h2>Analysis source traceability</h2></div>
        <p className="result-provenance-intro">This immutable snapshot identifies the uploaded source files and integrity checks used to create this analysis. It never exposes storage links or private provider metadata.</p>
        <InputProvenance provenance={model.provenance} />
      </section>

      <section className="panel result-viewer">
        <div className="result-viewer-head">
          <FileText size={24} />
          <div>
            <h2>Technical payload</h2>
            <p>Use this only for audit/debug review. The management view above hides empty or unsupported fields.</p>
          </div>
          <button className="secondary-button" type="button" onClick={onToggleRaw}>{showRaw ? "Hide JSON" : "Show JSON"}</button>
        </div>
        {showRaw ? (json ? <pre>{json}</pre> : <div className="status-box warning">No dashboard data was returned for this result.</div>) : null}
      </section>
    </>
  );
}

function clampPercent(value) {
  return Math.max(0, Math.min(100, numberValue(value) ?? 0));
}

function averageOf(rows, selector) {
  const values = rows.map(selector).map(numberValue).filter((value) => value !== null);
  if (!values.length) return null;
  return values.reduce((total, value) => total + value, 0) / values.length;
}

function scheduleRowName(row, index) {
  return row?.name || row?.building || row?.building_name || row?.block_name || row?.id || `Building ${index + 1}`;
}

function scheduleRiskBucket(row) {
  const text = String(row?.risk_level || row?.risk_status || row?.status || "").toLowerCase();
  const delay = numberValue(row?.delay_days ?? row?.delay) ?? 0;
  if (text.includes("critical") || delay >= 25) return "Critical";
  if (text.includes("high") || delay >= 14) return "High";
  if (text.includes("medium") || delay >= 5) return "Medium";
  return "Watch";
}

function scheduleRiskTone(bucket) {
  if (bucket === "Critical") return "critical";
  if (bucket === "High") return "high";
  if (bucket === "Medium") return "medium";
  return "watch";
}

function statusFromRiskBucket(bucket) {
  if (bucket === "Critical") return "danger";
  if (bucket === "High" || bucket === "Medium") return "warning";
  return "success";
}

function formatDelay(value) {
  const numeric = numberValue(value);
  if (numeric === null) return EMPTY;
  if (numeric < 0) return `${formatNumber(Math.abs(numeric))} days ahead`;
  if (numeric === 0) return "On plan";
  return `${formatNumber(numeric)} days delay`;
}

function progressGap(row) {
  const planned = numberValue(row?.planned_progress ?? row?.planned_percent);
  const actual = numberValue(row?.actual_progress ?? row?.actual_percent);
  if (planned === null || actual === null) return null;
  return planned - actual;
}

function formatGap(value) {
  const numeric = numberValue(value);
  if (numeric === null) return EMPTY;
  if (numeric === 0) return "0 pp";
  return `${numeric > 0 ? "+" : ""}${formatNumber(numeric)} pp`;
}

function scheduleStats(model) {
  const rows = asArray(model.scheduleRows);
  const planned = numberValue(model.schedule?.planned_progress ?? kpiValue(model, "planned_progress")) ?? averageOf(rows, (row) => row?.planned_progress ?? row?.planned_percent);
  const actual = numberValue(model.schedule?.actual_progress ?? kpiValue(model, "actual_progress")) ?? averageOf(rows, (row) => row?.actual_progress ?? row?.actual_percent);
  const delayedRows = rows.filter((row) => (numberValue(row?.delay_days ?? row?.delay) ?? 0) > 0);
  const maxDelay = rows.reduce((max, row) => Math.max(max, numberValue(row?.delay_days ?? row?.delay) ?? 0), 0);
  const distribution = rows.reduce((accumulator, row) => {
    const bucket = scheduleRiskBucket(row);
    accumulator[bucket] = (accumulator[bucket] || 0) + 1;
    return accumulator;
  }, {});

  return {
    planned,
    actual,
    gap: planned !== null && actual !== null ? planned - actual : null,
    delayedCount: delayedRows.length,
    totalCount: rows.length,
    maxDelay,
    averageDelay: averageOf(delayedRows, (row) => row?.delay_days ?? row?.delay),
    averageGap: averageOf(rows, progressGap),
    criticalCount: distribution.Critical || 0,
    highCount: distribution.High || 0,
    distribution
  };
}

function ScheduleMetricCard({ label, value, note, tone = "neutral", icon: Icon = TrendingUp }) {
  return (
    <article className={`schedule-kpi-card ${tone}`}>
      <div className="schedule-kpi-icon"><Icon size={18} /></div>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </article>
  );
}

function ScheduleMetaCard({ label, value, note, icon: Icon = FileText }) {
  return (
    <article className="schedule-meta-card">
      <div className="schedule-meta-icon"><Icon size={17} /></div>
      <span>{label}</span>
      <strong>{value || EMPTY}</strong>
      {note ? <small>{note}</small> : null}
    </article>
  );
}

function ScheduleTimeline({ rows }) {
  const priorityRows = [...rows]
    .sort((left, right) => (numberValue(right?.delay_days ?? right?.delay) ?? -999) - (numberValue(left?.delay_days ?? left?.delay) ?? -999))
    .slice(0, 7);

  return (
    <div className="schedule-timeline">
      {priorityRows.map((row, index) => {
        const planned = clampPercent(row?.planned_progress ?? row?.planned_percent);
        const actual = clampPercent(row?.actual_progress ?? row?.actual_percent);
        const bucket = scheduleRiskBucket(row);
        return (
          <article key={`${scheduleRowName(row, index)}-${index}`} className="schedule-timeline-row">
            <div className="schedule-timeline-copy">
              <strong>{scheduleRowName(row, index)}</strong>
              <span>{row?.current_stage || row?.stage || "Current stage requires review"}</span>
            </div>
            <div className="schedule-timeline-track" aria-label={`${scheduleRowName(row, index)} planned ${planned}% actual ${actual}%`}>
              <span className="schedule-plan" style={{ width: `${planned}%` }} />
              <i className="schedule-actual" style={{ width: `${actual}%` }} />
            </div>
            <div className="schedule-timeline-status">
              <span className={`status-pill ${statusFromRiskBucket(bucket)}`}>{bucket}</span>
              <strong>{formatDelay(row?.delay_days ?? row?.delay)}</strong>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function RiskDonutModern({ rows }) {
  const order = [
    { bucket: "Critical", color: "#EF4444" },
    { bucket: "High", color: "#F08A1E" },
    { bucket: "Medium", color: "#D4A24C" },
    { bucket: "Watch", color: "#22C55E" }
  ];
  const distribution = rows.reduce((accumulator, row) => {
    const bucket = scheduleRiskBucket(row);
    accumulator[bucket] = (accumulator[bucket] || 0) + 1;
    return accumulator;
  }, {});
  const total = rows.length || 1;
  let cursor = 0;
  const gradientParts = order
    .map((item) => {
      const count = distribution[item.bucket] || 0;
      if (!count) return null;
      const start = cursor;
      cursor += (count / total) * 100;
      return `${item.color} ${start}% ${cursor}%`;
    })
    .filter(Boolean);
  const gradient = gradientParts.length ? `conic-gradient(${gradientParts.join(", ")})` : "conic-gradient(rgba(255,255,255,0.12) 0% 100%)";

  return (
    <div className="schedule-risk-modern">
      <div className="schedule-risk-donut-chart" style={{ background: gradient }}>
        <div>
          <strong>{distribution.Critical || 0}</strong>
          <span>critical</span>
        </div>
      </div>
      <div className="schedule-risk-legend">
        {order.map((item) => (
          <div key={item.bucket}>
            <i style={{ background: item.color }} />
            <span>{item.bucket}</span>
            <strong>{formatNumber(distribution[item.bucket] || 0)}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function ScheduleBuildingGrid({ rows }) {
  return (
    <div className="schedule-building-grid">
      {rows.map((row, index) => {
        const planned = clampPercent(row?.planned_progress ?? row?.planned_percent);
        const actual = clampPercent(row?.actual_progress ?? row?.actual_percent);
        const bucket = scheduleRiskBucket(row);
        const tone = scheduleRiskTone(bucket);
        return (
          <article key={`${scheduleRowName(row, index)}-${index}`} className={`schedule-building-card ${tone}`}>
            <div className="schedule-building-head">
              <strong>{scheduleRowName(row, index)}</strong>
              <span className={`status-pill ${statusFromRiskBucket(bucket)}`}>{bucket}</span>
            </div>
            <p>{row?.issue || row?.current_stage || row?.stage || "No issue text returned for this building."}</p>
            <div className="schedule-building-bars">
              <div><span>Plan</span><i style={{ width: `${planned}%` }} /></div>
              <div><span>Fact</span><i style={{ width: `${actual}%` }} /></div>
            </div>
            <div className="schedule-building-footer">
              <span>{formatDelay(row?.delay_days ?? row?.delay)}</span>
              <span>{formatDate(row?.deadline || row?.target_date)}</span>
            </div>
            {row?.next_action ? <small>Action: {row.next_action}</small> : null}
          </article>
        );
      })}
    </div>
  );
}

function DelayPriorityPanel({ rows, actions }) {
  const priorityRows = [...rows]
    .filter((row) => (numberValue(row?.delay_days ?? row?.delay) ?? 0) > 0)
    .sort((left, right) => (numberValue(right?.delay_days ?? right?.delay) ?? 0) - (numberValue(left?.delay_days ?? left?.delay) ?? 0))
    .slice(0, 5);
  const actionRows = asArray(actions).slice(0, 5);

  return (
    <section className="schedule-delay-grid">
      <article className="panel schedule-priority-panel">
        <div className="schedule-panel-head">
          <div>
            <span>Delayed projects</span>
            <h2>Priority recovery list</h2>
          </div>
          <Clock3 size={21} />
        </div>
        <div className="schedule-priority-list">
          {priorityRows.map((row, index) => {
            const bucket = scheduleRiskBucket(row);
            return (
              <article key={`${scheduleRowName(row, index)}-${index}`}>
                <b>{String(index + 1).padStart(2, "0")}</b>
                <div>
                  <strong>{scheduleRowName(row, index)}</strong>
                  <span>{row?.issue || row?.current_stage || "Review schedule variance."}</span>
                </div>
                <em>{formatDelay(row?.delay_days ?? row?.delay)}</em>
                <span className={`status-pill ${statusFromRiskBucket(bucket)}`}>{bucket}</span>
              </article>
            );
          })}
        </div>
      </article>

      <article className="panel schedule-decision-panel">
        <div className="schedule-panel-head">
          <div>
            <span>Decision grid</span>
            <h2>Next recovery actions</h2>
          </div>
          <CheckCircle2 size={21} />
        </div>
        {actionRows.length ? (
          <ol className="schedule-decision-list">
            {actionRows.map((action, index) => (
              <li key={`${index}-${typeof action === "string" ? action : action?.action || action?.title}`}>
                {typeof action === "string" ? action : action?.action || action?.title || action?.description}
              </li>
            ))}
          </ol>
        ) : (
          <div className="status-box info">No recovery action list was returned for this result.</div>
        )}
      </article>
    </section>
  );
}

function ExecutionTable({ rows }) {
  return (
    <div className="schedule-execution-table">
      <table>
        <thead>
          <tr>
            <th>Building</th>
            <th>Current stage</th>
            <th>Planned</th>
            <th>Actual</th>
            <th>Gap</th>
            <th>Delay</th>
            <th>Deadline</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${scheduleRowName(row, index)}-${index}`}>
              <td><strong>{scheduleRowName(row, index)}</strong></td>
              <td>{row?.current_stage || row?.stage || EMPTY}</td>
              <td>{formatPercent(row?.planned_progress ?? row?.planned_percent)}</td>
              <td>{formatPercent(row?.actual_progress ?? row?.actual_percent)}</td>
              <td>{formatGap(progressGap(row))}</td>
              <td>{formatDelay(row?.delay_days ?? row?.delay)}</td>
              <td>{formatDate(row?.deadline || row?.target_date)}</td>
              <td>{row?.next_action || EMPTY}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ScheduleAnalysisDashboard({ model, headerAction, demoSwitcher = null }) {
  const rows = asArray(model.scheduleRows);
  const stats = scheduleStats(model);
  const totalBudget = kpiValue(model, "total_budget");
  const forecastCost = kpiValue(model, "forecast_cost");
  const confidence = model.dataQuality?.confidence ?? model.dataQuality?.readiness?.score ?? model.dataQuality?.premium?.overall_score;
  const summary = typeof model.managementSummary === "string"
    ? model.managementSummary
    : model.managementSummary?.overall_status || model.managementSummary?.overall_project_status || "Building-level schedule control view generated from the uploaded project files.";
  const project = model.project || {};
  const clientName = project.client_name || project.customer_name || project.owner_name;
  const contractorName = project.contractor_name || project.company_name;
  const periodStart = formatDate(project.start_date);
  const periodEnd = formatDate(project.contract_end);
  const contractPeriod = periodStart === EMPTY && periodEnd === EMPTY ? EMPTY : `${periodStart} - ${periodEnd}`;

  return (
    <>
      <PageHeader
        eyebrow="Schedule analysis dashboard"
        title={model.title}
        description={`Status: ${model.status}. Last updated: ${formatDate(model.lastUpdated)}.`}
        action={headerAction}
      />
      {demoSwitcher}

      <div className="schedule-analysis-dashboard">
        <section className="schedule-overview panel featured">
          <div className="schedule-overview-copy">
            <span className={`status-pill ${statusClass(model.status)}`}>{model.status}</span>
            <h2>Schedule recovery control board</h2>
            <p>{summary}</p>
            <div className="schedule-overview-metrics">
              <div><span>Planned</span><strong>{formatPercent(stats.planned)}</strong></div>
              <div><span>Actual</span><strong>{formatPercent(stats.actual)}</strong></div>
              <div><span>Gap</span><strong>{formatGap(stats.gap)}</strong></div>
            </div>
          </div>

          <aside className="schedule-overview-rail">
            <span>Critical path focus</span>
            <strong>{formatNumber(stats.criticalCount)} buildings</strong>
            <p>Largest delay: {formatDelay(stats.maxDelay)}. Average delayed-building impact: {formatDelay(stats.averageDelay)}.</p>
          </aside>
        </section>

        <section className="schedule-meta-grid">
          <ScheduleMetaCard label="Client" value={clientName} note={clientName ? "Customer / owner" : "Not returned"} icon={UsersRound} />
          <ScheduleMetaCard label="Contractor" value={contractorName} note={contractorName ? "Workspace owner" : "Not returned"} icon={Building2} />
          <ScheduleMetaCard label="Location" value={project.location || EMPTY} note={project.total_area_m2 ? `${formatNumber(project.total_area_m2)} m2 planned area` : ""} icon={MapPin} />
          <ScheduleMetaCard label="Contract period" value={contractPeriod} note={project.duration_label || ""} icon={CalendarDays} />
        </section>

        <section className="schedule-kpi-grid">
          <ScheduleMetricCard label="Delayed buildings" value={`${formatNumber(stats.delayedCount)} / ${formatNumber(stats.totalCount)}`} note="Buildings currently behind plan" tone="critical" icon={Clock3} />
          <ScheduleMetricCard label="Progress gap" value={formatGap(stats.gap)} note="Planned minus actual progress" tone={stats.gap > 6 ? "high" : "medium"} icon={Gauge} />
          <ScheduleMetricCard label="Forecast cost" value={formatMoney(forecastCost, model.currency)} note={`Contract baseline: ${formatMoney(totalBudget, model.currency)}`} tone="medium" icon={BarChart3} />
          <ScheduleMetricCard label="Data confidence" value={formatPercent(confidence)} note={`${formatNumber(model.provenance?.file_count || asArray(model.provenance?.files).length)} source files retained`} tone="watch" icon={Fingerprint} />
        </section>

        <section className="schedule-analysis-grid">
          <article className="panel schedule-timeline-panel">
            <div className="schedule-panel-head">
              <div>
                <span>Plan vs fact timeline</span>
                <h2>Building schedule performance</h2>
              </div>
              <BarChart3 size={21} />
            </div>
            <ScheduleTimeline rows={rows} />
          </article>

          <article className="panel schedule-risk-panel">
            <div className="schedule-panel-head">
              <div>
                <span>Risk distribution</span>
                <h2>Schedule risk by building</h2>
              </div>
              <ShieldAlert size={21} />
            </div>
            <RiskDonutModern rows={rows} />
          </article>
        </section>

        <DelayPriorityPanel rows={rows} actions={model.actions} />

        <section className="panel schedule-building-panel">
          <div className="schedule-panel-head">
            <div>
              <span>Building grid</span>
              <h2>Block-by-block status</h2>
            </div>
            <Building2 size={21} />
          </div>
          <ScheduleBuildingGrid rows={rows} />
        </section>

        <section className="panel schedule-execution-panel">
          <div className="schedule-panel-head">
            <div>
              <span>Execution grid</span>
              <h2>Detailed execution table</h2>
            </div>
            <ClipboardList size={21} />
          </div>
          <ExecutionTable rows={rows} />
        </section>
      </div>
    </>
  );
}

function formatSignedMoney(value, currency) {
  const numeric = numberValue(value);
  if (numeric === null) return EMPTY;
  const absolute = formatMoney(Math.abs(numeric), currency);
  if (numeric === 0) return absolute;
  return `${numeric > 0 ? "+" : "-"}${absolute}`;
}

function percentOf(value, total) {
  const numeric = numberValue(value);
  const totalNumeric = numberValue(total);
  if (numeric === null || !totalNumeric) return 0;
  return Math.max(0, Math.min(100, (numeric / totalNumeric) * 100));
}

function rowTone(value) {
  const text = String(value || "").toLowerCase();
  if (text.includes("critical") || text.includes("overdue")) return "critical";
  if (text.includes("high") || text.includes("decision")) return "high";
  if (text.includes("watch") || text.includes("medium") || text.includes("review")) return "medium";
  return "watch";
}

function statusFromTone(tone) {
  if (tone === "critical") return "danger";
  if (tone === "high" || tone === "medium") return "warning";
  return "success";
}

function MiniTrendBars({ rows, plannedKey = "planned", actualKey = "actual", valueFormatter = formatNumber }) {
  const maxValue = Math.max(1, ...rows.flatMap((row) => [numberValue(row?.[plannedKey]) || 0, numberValue(row?.[actualKey]) || 0]));
  return (
    <div className="control-trend-bars">
      {rows.map((row, index) => {
        const planned = numberValue(row?.[plannedKey]) || 0;
        const actual = numberValue(row?.[actualKey]) || 0;
        return (
          <article key={`${row?.period || index}-${index}`}>
            <span>{row?.period || `P${index + 1}`}</span>
            <div>
              <i className="planned" style={{ height: `${Math.max(8, percentOf(planned, maxValue))}%` }} title={`Plan: ${valueFormatter(planned)}`} />
              <i className="actual" style={{ height: `${Math.max(8, percentOf(actual, maxValue))}%` }} title={`Actual: ${valueFormatter(actual)}`} />
            </div>
          </article>
        );
      })}
    </div>
  );
}

function CostPackageGrid({ rows, currency }) {
  return (
    <div className="control-card-grid cost-package-grid">
      {rows.map((row, index) => {
        const tone = rowTone(row?.status);
        const budget = numberValue(row?.budget);
        const forecast = numberValue(row?.forecast);
        const variance = row?.variance ?? (budget !== null && forecast !== null ? forecast - budget : null);
        return (
          <article key={`${row?.code || row?.name || index}-${index}`} className={`control-card ${tone}`}>
            <div className="control-card-head">
              <span>{row?.code || `C-${index + 1}`}</span>
              <b className={`status-pill ${statusFromTone(tone)}`}>{row?.status || "Review"}</b>
            </div>
            <h3>{row?.name || `Cost package ${index + 1}`}</h3>
            <p>{row?.issue || "Review cost movement against the baseline."}</p>
            <div className="control-value-stack">
              <div><span>Budget</span><strong>{formatMoney(budget, currency)}</strong></div>
              <div><span>Forecast</span><strong>{formatMoney(forecast, currency)}</strong></div>
              <div><span>Variance</span><strong>{formatSignedMoney(variance, currency)}</strong></div>
            </div>
            <div className="control-progress-line">
              <span>Progress</span>
              <i style={{ width: `${clampPercent(row?.progress)}%` }} />
              <b>{formatPercent(row?.progress)}</b>
            </div>
            {row?.action ? <small>Action: {row.action}</small> : null}
          </article>
        );
      })}
    </div>
  );
}

function ChangeOrderList({ rows, currency }) {
  if (!rows.length) return <div className="status-box info">No change-order rows were returned for this cost result.</div>;
  return (
    <div className="control-decision-list">
      {rows.map((row, index) => {
        const tone = rowTone(row?.status);
        return (
          <article key={`${row?.id || index}-${index}`}>
            <b>{row?.id || String(index + 1).padStart(2, "0")}</b>
            <div>
              <strong>{row?.title || "Change order"}</strong>
              <span>{row?.owner || "Owner not returned"} - due {formatDate(row?.due_date)}</span>
            </div>
            <em>{formatMoney(row?.value, currency)}</em>
            <span className={`status-pill ${statusFromTone(tone)}`}>{row?.status || "Review"}</span>
          </article>
        );
      })}
    </div>
  );
}

function CostControlDashboard({ model, headerAction, demoSwitcher = null }) {
  const rows = asArray(model.costRows);
  const control = model.costControl || {};
  const totalBudget = kpiValue(model, "total_budget");
  const actualCost = kpiValue(model, "actual_cost");
  const forecastCost = kpiValue(model, "forecast_cost");
  const committedCost = model.kpis?.committed_cost;
  const variance = model.kpis?.cost_variance ?? (numberValue(forecastCost) !== null && numberValue(totalBudget) !== null ? numberValue(forecastCost) - numberValue(totalBudget) : null);
  const variancePercent = model.kpis?.variance_percent;
  const trendRows = asArray(control?.payment_trend);
  const changeOrders = asArray(control?.change_orders);
  const decisions = asArray(control?.decisions || model.actions);

  return (
    <>
      <PageHeader
        eyebrow="Cost control dashboard"
        title={model.title}
        description={`Status: ${model.status}. Last updated: ${formatDate(model.lastUpdated)}.`}
        action={headerAction}
      />
      {demoSwitcher}

      <div className="control-dashboard cost-control-dashboard">
        <section className="control-hero panel featured">
          <div>
            <span className={`status-pill ${statusClass(model.status)}`}>{model.status}</span>
            <h2>Commercial control board</h2>
            <p>{control?.summary || "Cost packages, payment trend and commercial decisions returned by the uploaded project files."}</p>
            <div className="control-hero-metrics">
              <div><span>Contract</span><strong>{formatMoney(totalBudget, model.currency)}</strong></div>
              <div><span>Forecast</span><strong>{formatMoney(forecastCost, model.currency)}</strong></div>
              <div><span>Variance</span><strong>{formatSignedMoney(variance, model.currency)}</strong></div>
            </div>
          </div>
          <aside className="control-hero-rail cost">
            <span>Cost exposure</span>
            <strong>{formatPercent(variancePercent)}</strong>
            <p>Committed cost: {formatMoney(committedCost, model.currency)}. Certified payment: {formatMoney(model.kpis?.payment_certified, model.currency)}.</p>
          </aside>
        </section>

        <section className="schedule-kpi-grid">
          <ScheduleMetricCard label="Actual cost" value={formatMoney(actualCost, model.currency)} note="Posted cost evidence" tone="medium" icon={TrendingUp} />
          <ScheduleMetricCard label="Committed cost" value={formatMoney(committedCost, model.currency)} note="POs and committed packages" tone="high" icon={ClipboardList} />
          <ScheduleMetricCard label="Forecast variance" value={formatSignedMoney(variance, model.currency)} note="Forecast minus baseline" tone={numberValue(variance) > 0 ? "critical" : "watch"} icon={Gauge} />
          <ScheduleMetricCard label="Cost packages" value={formatNumber(rows.length)} note="Commercial rows returned" tone="watch" icon={FileText} />
        </section>

        <section className="control-split-grid">
          <article className="panel">
            <div className="schedule-panel-head">
              <div><span>Payment trend</span><h2>Planned vs certified</h2></div>
              <BarChart3 size={21} />
            </div>
            <MiniTrendBars rows={trendRows} valueFormatter={(value) => formatMoney(value, model.currency)} />
          </article>

          <article className="panel">
            <div className="schedule-panel-head">
              <div><span>Change orders</span><h2>Decision queue</h2></div>
              <CheckCircle2 size={21} />
            </div>
            <ChangeOrderList rows={changeOrders} currency={model.currency} />
          </article>
        </section>

        <section className="panel">
          <div className="schedule-panel-head">
            <div><span>Cost package grid</span><h2>Budget, forecast and action status</h2></div>
            <FileText size={21} />
          </div>
          <CostPackageGrid rows={rows} currency={model.currency} />
        </section>

        <section className="panel control-action-panel">
          <div className="schedule-panel-head">
            <div><span>Commercial actions</span><h2>Cost recovery decisions</h2></div>
            <ClipboardList size={21} />
          </div>
          <ol className="schedule-decision-list">
            {decisions.slice(0, 6).map((item, index) => <li key={`${item}-${index}`}>{typeof item === "string" ? item : item?.action || item?.title || item?.description}</li>)}
          </ol>
        </section>
      </div>
    </>
  );
}

function MaterialItemGrid({ rows }) {
  return (
    <div className="material-flow-grid">
      {rows.map((row, index) => {
        const tone = rowTone(row?.status);
        const required = numberValue(row?.required_qty);
        const stock = numberValue(row?.stock_qty);
        const inbound = numberValue(row?.inbound_qty);
        const availablePercent = percentOf((stock || 0) + (inbound || 0), required || 1);
        return (
          <article key={`${row?.code || row?.name || index}-${index}`} className={`material-flow-card ${tone}`}>
            <div className="control-card-head">
              <span>{row?.code || row?.category || `M-${index + 1}`}</span>
              <b className={`status-pill ${statusFromTone(tone)}`}>{row?.status || "Review"}</b>
            </div>
            <h3>{row?.name || `Material ${index + 1}`}</h3>
            <p>{row?.issue || "Review stock, inbound quantity and consumption rate."}</p>
            <div className="material-gauge">
              <i style={{ width: `${availablePercent}%` }} />
            </div>
            <div className="control-value-stack">
              <div><span>Stock</span><strong>{formatNumber(stock)} {row?.unit || ""}</strong></div>
              <div><span>Inbound</span><strong>{formatNumber(inbound)} {row?.unit || ""}</strong></div>
              <div><span>Coverage</span><strong>{formatNumber(row?.coverage_days)} days</strong></div>
            </div>
            <small>Supplier: {row?.supplier || "Not returned"}</small>
            {row?.action ? <small>Action: {row.action}</small> : null}
          </article>
        );
      })}
    </div>
  );
}

function SupplierLaneList({ rows }) {
  if (!rows.length) return <div className="status-box info">No supplier lane rows were returned for this material result.</div>;
  return (
    <div className="supplier-lane-list">
      {rows.map((row, index) => {
        const tone = rowTone(row?.status);
        return (
          <article key={`${row?.supplier || index}-${index}`}>
            <div>
              <strong>{row?.supplier || `Supplier ${index + 1}`}</strong>
              <span>{row?.lane || "Supply lane"} - next: {row?.next_delivery || EMPTY}</span>
            </div>
            <div className="supplier-reliability">
              <i style={{ width: `${clampPercent(row?.reliability)}%` }} />
            </div>
            <b>{formatPercent(row?.reliability)}</b>
            <span className={`status-pill ${statusFromTone(tone)}`}>{row?.status || "Review"}</span>
          </article>
        );
      })}
    </div>
  );
}

function MaterialContinuityDashboard({ model, headerAction, demoSwitcher = null }) {
  const rows = asArray(model.materialRows);
  const material = model.materialContinuity || {};
  const criticalCount = rows.filter((row) => rowTone(row?.status) === "critical").length;
  const lowCoverage = rows.reduce((minimum, row) => Math.min(minimum, numberValue(row?.coverage_days) ?? minimum), 999);
  const trendRows = asArray(material?.consumption_trend);
  const supplierRows = asArray(material?.supplier_lanes);
  const actions = asArray(material?.procurement_actions || model.actions);

  return (
    <>
      <PageHeader
        eyebrow="Material continuity dashboard"
        title={model.title}
        description={`Status: ${model.status}. Last updated: ${formatDate(model.lastUpdated)}.`}
        action={headerAction}
      />
      {demoSwitcher}

      <div className="control-dashboard material-dashboard">
        <section className="control-hero panel featured material-hero">
          <div>
            <span className={`status-pill ${statusClass(model.status)}`}>{model.status}</span>
            <h2>Supply continuity board</h2>
            <p>{material?.summary || "Material stock, inbound supply and procurement actions returned by the uploaded project files."}</p>
            <div className="control-hero-metrics">
              <div><span>Critical shortages</span><strong>{formatNumber(criticalCount)}</strong></div>
              <div><span>Lowest coverage</span><strong>{lowCoverage === 999 ? EMPTY : `${formatNumber(lowCoverage)} days`}</strong></div>
              <div><span>Open POs</span><strong>{formatNumber(model.kpis?.open_purchase_orders)}</strong></div>
            </div>
          </div>
          <aside className="control-hero-rail material">
            <span>Continuity score</span>
            <strong>{formatNumber(model.kpis?.material_risk_score)}/100</strong>
            <p>{formatNumber(model.kpis?.delayed_deliveries)} delayed deliveries. Average coverage: {formatNumber(model.kpis?.average_coverage_days)} days.</p>
          </aside>
        </section>

        <section className="schedule-kpi-grid">
          <ScheduleMetricCard label="Critical shortages" value={formatNumber(criticalCount)} note="Materials below safe coverage" tone="critical" icon={AlertTriangle} />
          <ScheduleMetricCard label="Average coverage" value={`${formatNumber(model.kpis?.average_coverage_days)} days`} note="Across returned material rows" tone="medium" icon={Clock3} />
          <ScheduleMetricCard label="Delayed deliveries" value={formatNumber(model.kpis?.delayed_deliveries)} note="Supplier lane delays" tone="high" icon={TrendingUp} />
          <ScheduleMetricCard label="Material rows" value={formatNumber(rows.length)} note="Stock lines returned" tone="watch" icon={ClipboardList} />
        </section>

        <section className="control-split-grid">
          <article className="panel">
            <div className="schedule-panel-head">
              <div><span>Consumption pulse</span><h2>Planned vs actual usage</h2></div>
              <BarChart3 size={21} />
            </div>
            <MiniTrendBars rows={trendRows} valueFormatter={(value) => `${formatNumber(value)}%`} />
          </article>

          <article className="panel">
            <div className="schedule-panel-head">
              <div><span>Supplier lanes</span><h2>Delivery reliability</h2></div>
              <Building2 size={21} />
            </div>
            <SupplierLaneList rows={supplierRows} />
          </article>
        </section>

        <section className="panel">
          <div className="schedule-panel-head">
            <div><span>Material grid</span><h2>Stock, inbound and coverage</h2></div>
            <ClipboardList size={21} />
          </div>
          <MaterialItemGrid rows={rows} />
        </section>

        <section className="panel control-action-panel">
          <div className="schedule-panel-head">
            <div><span>Procurement actions</span><h2>Next continuity moves</h2></div>
            <CheckCircle2 size={21} />
          </div>
          <ol className="schedule-decision-list">
            {actions.slice(0, 6).map((item, index) => <li key={`${item}-${index}`}>{typeof item === "string" ? item : item?.action || item?.title || item?.description}</li>)}
          </ol>
        </section>
      </div>
    </>
  );
}

function RiskMatrixTiles({ rows }) {
  return (
    <div className="risk-matrix-tiles">
      {rows.map((row, index) => (
        <article key={`${row?.level || index}-${index}`} style={{ "--risk-color": row?.color || "#D4A24C" }}>
          <span>{row?.level || `Level ${index + 1}`}</span>
          <strong>{formatNumber(row?.count)}</strong>
        </article>
      ))}
    </div>
  );
}

function RiskCommandList({ rows }) {
  return (
    <div className="risk-command-list">
      {rows.map((row, index) => {
        const tone = rowTone(row?.severity || row?.status);
        return (
          <article key={`${row?.id || row?.title || index}-${index}`} className={tone}>
            <div className="risk-command-main">
              <span>{row?.id || `R-${index + 1}`}</span>
              <h3>{row?.title || `Risk ${index + 1}`}</h3>
              <p>{row?.decision_needed || row?.action || "Decision or mitigation action required."}</p>
            </div>
            <div className="risk-command-scores">
              <div><span>Prob.</span><strong>{formatPercent(row?.probability)}</strong></div>
              <div><span>Impact</span><strong>{formatPercent(row?.impact)}</strong></div>
            </div>
            <div className="risk-command-meta">
              <span className={`status-pill ${statusFromTone(tone)}`}>{row?.severity || row?.status || "Review"}</span>
              <small>{row?.owner || "Owner not returned"} - {formatDate(row?.due_date)}</small>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function DecisionBoard({ rows }) {
  if (!rows.length) return <div className="status-box info">No decision log rows were returned for this risk result.</div>;
  return (
    <div className="decision-board-grid">
      {rows.map((row, index) => {
        const tone = rowTone(row?.status);
        return (
          <article key={`${row?.id || index}-${index}`} className={tone}>
            <div className="control-card-head">
              <span>{row?.id || `D-${index + 1}`}</span>
              <b className={`status-pill ${statusFromTone(tone)}`}>{row?.status || "Open"}</b>
            </div>
            <h3>{row?.title || `Decision ${index + 1}`}</h3>
            <p>{row?.impact || "Impact not returned."}</p>
            <small>Owner: {row?.owner || "Not returned"}</small>
            <small>Due: {formatDate(row?.due_date)}</small>
            {row?.next_step ? <strong>{row.next_step}</strong> : null}
          </article>
        );
      })}
    </div>
  );
}

function RiskDecisionDashboard({ model, headerAction, demoSwitcher = null }) {
  const rows = asArray(model.riskDecisionRows);
  const risk = model.riskDecisions || {};
  const decisions = asArray(risk?.decisions);
  const matrix = asArray(risk?.matrix);
  const actions = asArray(risk?.actions || model.actions);

  return (
    <>
      <PageHeader
        eyebrow="Risk and decisions dashboard"
        title={model.title}
        description={`Status: ${model.status}. Last updated: ${formatDate(model.lastUpdated)}.`}
        action={headerAction}
      />
      {demoSwitcher}

      <div className="control-dashboard risk-dashboard">
        <section className="control-hero panel featured risk-hero">
          <div>
            <span className={`status-pill ${statusClass(model.status)}`}>{model.status}</span>
            <h2>Decision command board</h2>
            <p>{risk?.summary || "Risk register, decision log and management actions returned by the uploaded project files."}</p>
            <div className="control-hero-metrics">
              <div><span>Open risks</span><strong>{formatNumber(model.kpis?.open_risks || rows.length)}</strong></div>
              <div><span>Critical</span><strong>{formatNumber(model.kpis?.critical_risks)}</strong></div>
              <div><span>Overdue decisions</span><strong>{formatNumber(model.kpis?.overdue_decisions)}</strong></div>
            </div>
          </div>
          <aside className="control-hero-rail risk">
            <span>Decision cycle</span>
            <strong>{formatNumber(model.kpis?.decision_cycle_days)} days</strong>
            <p>Risk score: {formatNumber(model.kpis?.risk_score)}/100. Keep high-impact decisions owner-visible.</p>
          </aside>
        </section>

        <section className="control-split-grid risk-top-grid">
          <article className="panel">
            <div className="schedule-panel-head">
              <div><span>Risk matrix</span><h2>Severity distribution</h2></div>
              <ShieldAlert size={21} />
            </div>
            <RiskMatrixTiles rows={matrix} />
          </article>

          <article className="panel">
            <div className="schedule-panel-head">
              <div><span>Management moves</span><h2>Immediate actions</h2></div>
              <CheckCircle2 size={21} />
            </div>
            <ol className="schedule-decision-list">
              {actions.slice(0, 6).map((item, index) => <li key={`${item}-${index}`}>{typeof item === "string" ? item : item?.action || item?.title || item?.description}</li>)}
            </ol>
          </article>
        </section>

        <section className="panel">
          <div className="schedule-panel-head">
            <div><span>Risk command list</span><h2>Owner, probability and impact</h2></div>
            <AlertTriangle size={21} />
          </div>
          <RiskCommandList rows={rows} />
        </section>

        <section className="panel">
          <div className="schedule-panel-head">
            <div><span>Decision board</span><h2>Approvals blocking recovery</h2></div>
            <ClipboardList size={21} />
          </div>
          <DecisionBoard rows={decisions} />
        </section>
      </div>
    </>
  );
}

function packageDashboardIcon(packageId) {
  if (packageId === "cost-control") return Gauge;
  if (packageId === "material-continuity") return ClipboardList;
  if (packageId === "risk-decisions") return ShieldAlert;
  return BarChart3;
}

function DemoDashboardSwitcher({ activePackage, onPackageChange }) {
  const active = analysisPackages.find((item) => item.id === activePackage) || analysisPackages[0];
  const insight = demoWorkspace.packageInsights?.[active.id];
  const ActiveIcon = packageDashboardIcon(active.id);

  return (
    <section className="demo-dashboard-switcher panel">
      <div className="demo-dashboard-switcher-copy">
        <span className="workspace-eyebrow">Dashboard package</span>
        <h2><ActiveIcon size={22} /> {active.name}</h2>
        <p>{insight?.nextStep || active.label}</p>
      </div>
      <PackageSegmentedControl
        activePackage={active.id}
        onPackageChange={onPackageChange}
        showMetric
        ariaLabel="Switch dashboard package"
      />
    </section>
  );
}

export function ResultViewer({
  mode = "result",
  demoPayload = null,
  demoMode = false,
  activeDemoPackage = "schedule-recovery",
  onDemoPackageChange
}) {
  const params = useMemo(() => new URLSearchParams(location.search), []);
  const token = params.get("token");
  const projectId = params.get("project_id");
  const [state, setState] = useState({ loading: !demoPayload, error: null, payload: demoPayload });
  const [showRaw, setShowRaw] = useState(false);

  useEffect(() => {
    if (demoPayload) {
      setState({ loading: false, error: null, payload: demoPayload });
      return undefined;
    }
    let active = true;
    async function load() {
      setState({ loading: true, error: null, payload: null });
      try {
        let payload = null;
        if (token) {
          payload = await workspaceApi.guestResult(token);
        } else if (projectId) {
          payload = await workspaceApi.executiveDashboard(projectId);
        }
        if (!active) return;
        setState({ loading: false, error: payload ? null : "No result token or project id was provided.", payload });
      } catch (error) {
        if (!active) return;
        setState({ loading: false, error: error.message || "Result could not be loaded.", payload: null });
      }
    }
    load();
    return () => {
      active = false;
    };
  }, [token, projectId, demoPayload]);

  const model = useMemo(() => normalizePayload(state.payload || {}), [state.payload]);
  const json = compactJson(model.rawForDebug);
  const plannedProgress = model.schedule?.planned_progress ?? kpiValue(model, "planned_progress");
  const actualProgress = model.schedule?.actual_progress ?? kpiValue(model, "actual_progress");
  const delayDays = model.schedule?.delay_days ?? kpiValue(model, "delay_days");
  const variance = model.schedule?.variance ?? kpiValue(model, "schedule_variance");
  const totalBudget = kpiValue(model, "total_budget");
  const actualCost = kpiValue(model, "actual_cost");
  const forecastCost = kpiValue(model, "forecast_cost");
  const riskScore = kpiValue(model, "risk_score");
  const headerAction = (
    <div className="result-header-actions">
      {!demoPayload && (model.reports?.[0]?.id || model.reports?.[0]?.report_id) ? (
        <a className="secondary-button" href={workspaceApi.reportDownloadUrl(model.reports[0].id || model.reports[0].report_id)}><Download size={17} /> Report</a>
      ) : null}
      <button className="secondary-button" type="button" onClick={() => window.print()}><Printer size={17} /> Print</button>
    </div>
  );
  const demoSwitcher = demoMode ? (
    <DemoDashboardSwitcher activePackage={activeDemoPackage} onPackageChange={onDemoPackageChange} />
  ) : null;

  if (state.loading) {
    return (
      <>
        <PageHeader eyebrow="Result viewer" title="Loading project result." description="DevBareun is reading the generated dashboard package." />
        <div className="status-box info">Loading result...</div>
      </>
    );
  }

  if (state.error) {
    return (
      <>
        <PageHeader eyebrow="Result viewer" title="Result unavailable." description="The link may be expired, missing, or unavailable for this workspace." />
        <EmptyState title="No result loaded." description={state.error} action={<a className="secondary-button" href="/workspace/?view=reports">Open Reports</a>} />
      </>
    );
  }

  if (model.costRows.length > 0 && (model.packageId === "cost-control" || model.scheduleRows.length === 0)) {
    return (
      <>
        <CostControlDashboard model={model} headerAction={headerAction} demoSwitcher={demoSwitcher} />
        <ResultSupportSections model={model} json={json} showRaw={showRaw} onToggleRaw={() => setShowRaw((value) => !value)} />
      </>
    );
  }

  if (model.materialRows.length > 0 && (model.packageId === "material-continuity" || model.scheduleRows.length === 0)) {
    return (
      <>
        <MaterialContinuityDashboard model={model} headerAction={headerAction} demoSwitcher={demoSwitcher} />
        <ResultSupportSections model={model} json={json} showRaw={showRaw} onToggleRaw={() => setShowRaw((value) => !value)} />
      </>
    );
  }

  if (model.riskDecisionRows.length > 0 && (model.packageId === "risk-decisions" || model.scheduleRows.length === 0)) {
    return (
      <>
        <RiskDecisionDashboard model={model} headerAction={headerAction} demoSwitcher={demoSwitcher} />
        <ResultSupportSections model={model} json={json} showRaw={showRaw} onToggleRaw={() => setShowRaw((value) => !value)} />
      </>
    );
  }

  if (model.scheduleRows.length > 0) {
    return (
      <>
        <ScheduleAnalysisDashboard model={model} headerAction={headerAction} demoSwitcher={demoSwitcher} />
        <ResultSupportSections model={model} json={json} showRaw={showRaw} onToggleRaw={() => setShowRaw((value) => !value)} />
      </>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow={mode === "guest" ? "Secure guest result" : "Project dashboard result"}
        title={model.title}
        description={`Status: ${model.status}. Last updated: ${formatDate(model.lastUpdated)}.`}
        action={headerAction}
      />
      {demoSwitcher}

      <section className="result-hero panel featured">
        <div>
          <span className={`status-pill ${statusClass(model.status)}`}>{model.status}</span>
          <h2>Executive result overview</h2>
          <SummaryPanel summary={model.managementSummary} />
        </div>
        <div className="result-hero-meta">
          <div><span>Project</span><strong>{model.title}</strong></div>
          <div><span>Currency</span><strong>{model.currency || EMPTY}</strong></div>
          <div><span>Updated</span><strong>{formatDate(model.lastUpdated)}</strong></div>
        </div>
      </section>

      <section className="result-kpi-grid">
        <KpiCard label="Total budget" value={formatMoney(totalBudget, model.currency)} note="Contract / baseline value" icon={FileText} />
        <KpiCard label="Actual cost" value={formatMoney(actualCost, model.currency)} note="Shown only when actual/payment data exists" icon={TrendingUp} />
        <KpiCard label="Forecast cost" value={formatMoney(forecastCost, model.currency)} note="Forecast from latest analysis" icon={BarChart3} />
        <KpiCard label="Risk score" value={riskScore === null ? EMPTY : `${formatNumber(riskScore)}/100`} note="Composite risk indicator" status={statusClass(model.kpis?.risk_level || model.status)} icon={ShieldAlert} />
      </section>

      <section className="card-grid result-section-grid">
        <article className="panel">
          <div className="result-section-title"><BarChart3 size={20} /><h2>Schedule and progress</h2></div>
          <ProgressBar label="Planned progress" value={plannedProgress} note="Baseline or planned execution" />
          <ProgressBar label="Actual progress" value={actualProgress} note="Confirmed progress evidence" />
          <div className="result-metric-row">
            <span>Variance</span><strong>{formatPercent(variance)}</strong>
          </div>
          <div className="result-metric-row">
            <span>Delay impact</span><strong>{delayDays === null ? EMPTY : `${formatNumber(delayDays)} days`}</strong>
          </div>
        </article>

        <article className="panel">
          <div className="result-section-title"><ClipboardList size={20} /><h2>Data quality</h2></div>
          <DataQuality dataQuality={model.dataQuality} documentControl={model.documentControl} />
        </article>
      </section>

      <section className="panel result-provenance-panel">
        <div className="result-section-title"><Fingerprint size={20} /><h2>Analysis source traceability</h2></div>
        <p className="result-provenance-intro">This immutable snapshot identifies the uploaded source files and integrity checks used to create this analysis. It never exposes storage links or private provider metadata.</p>
        <InputProvenance provenance={model.provenance} />
      </section>

      <section className="card-grid result-section-grid">
        <article className="panel">
          <div className="result-section-title"><ShieldAlert size={20} /><h2>Risk register</h2></div>
          <RiskList risks={model.risks} />
        </article>

        <article className="panel">
          <div className="result-section-title"><CheckCircle2 size={20} /><h2>Recommended actions</h2></div>
          {model.actions.length ? (
            <ol className="result-action-list">
              {model.actions.slice(0, 7).map((action, index) => <li key={`${action}-${index}`}>{typeof action === "string" ? action : action.action || action.title || action.description}</li>)}
            </ol>
          ) : (
            <div className="status-box info">No action list was returned for this result.</div>
          )}
        </article>
      </section>

      <section className="panel result-viewer">
        <div className="result-viewer-head">
          <FileText size={24} />
          <div>
            <h2>Technical payload</h2>
            <p>Use this only for audit/debug review. The management view above hides empty or unsupported fields.</p>
          </div>
          <button className="secondary-button" type="button" onClick={() => setShowRaw((value) => !value)}>{showRaw ? "Hide JSON" : "Show JSON"}</button>
        </div>
        {showRaw ? (json ? <pre>{json}</pre> : <div className="status-box warning">No dashboard data was returned for this result.</div>) : null}
      </section>
    </>
  );
}
