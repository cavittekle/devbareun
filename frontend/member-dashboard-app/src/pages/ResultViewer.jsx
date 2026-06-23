import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ClipboardList,
  Download,
  FileText,
  Fingerprint,
  Printer,
  ShieldAlert,
  TrendingUp
} from "lucide-react";
import { workspaceApi } from "../api/client";
import { EmptyState, PageHeader } from "../components/Shell";

const EMPTY = "—";

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
  const project = executive?.project || analyzerDashboard?.project || payload?.project || normalized?.project_info || {};
  const kpis = executive?.kpis || analyzerDashboard?.kpis || rawDashboard?.metrics || {};
  const metrics = rawDashboard?.metrics || analyzerDashboard?.metrics || {};
  const schedule = executive?.schedule_performance || analyzerDashboard?.schedule_performance || rawDashboard?.schedule_performance || {};
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
  return text.length > 18 ? `${text.slice(0, 10)}…${text.slice(-6)}` : text;
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
                <small>{file?.extension || "file"} · {formatNumber(file?.size_bytes)} bytes · hash: {file?.content_hash_source || "unavailable"}</small>
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

export function ResultViewer({ mode = "result" }) {
  const params = useMemo(() => new URLSearchParams(location.search), []);
  const token = params.get("token");
  const projectId = params.get("project_id");
  const [state, setState] = useState({ loading: true, error: null, payload: null });
  const [showRaw, setShowRaw] = useState(false);

  useEffect(() => {
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
  }, [token, projectId]);

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

  return (
    <>
      <PageHeader
        eyebrow={mode === "guest" ? "Secure guest result" : "Project dashboard result"}
        title={model.title}
        description={`Status: ${model.status}. Last updated: ${formatDate(model.lastUpdated)}.`}
        action={
          <div className="result-header-actions">
            {model.reports?.[0]?.id || model.reports?.[0]?.report_id ? (
              <a className="secondary-button" href={workspaceApi.reportDownloadUrl(model.reports[0].id || model.reports[0].report_id)}><Download size={17} /> Report</a>
            ) : null}
            <button className="secondary-button" type="button" onClick={() => window.print()}><Printer size={17} /> Print</button>
          </div>
        }
      />

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
