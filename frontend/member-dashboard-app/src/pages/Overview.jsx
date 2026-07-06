import {
  Activity,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  FileText,
  UploadCloud
} from "lucide-react";
import { PageHeader, EmptyState } from "../components/Shell";
import { PackageSegmentedControl } from "../components/PackageSegmentedControl";
import { analysisPackages } from "../data/packages";
import { demoWorkspace } from "../data/demoWorkspace";
import { formatCount } from "../lib/format";

function formatMoney(value, currency = "AZN") {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "-";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    notation: Math.abs(numeric) >= 1000000 ? "compact" : "standard",
    maximumFractionDigits: Math.abs(numeric) >= 1000000 ? 1 : 0
  }).format(numeric);
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

function statusTone(value) {
  const text = String(value || "").toLowerCase();
  if (text.includes("critical") || text.includes("risk") || text.includes("pressure")) return "danger";
  if (text.includes("watch") || text.includes("required") || text.includes("delay")) return "warning";
  if (text.includes("ready") || text.includes("active") || text.includes("ok")) return "success";
  return "neutral";
}

export function Overview({
  projects,
  reports,
  credits,
  onNavigate,
  demoMode = false,
  activeDemoPackage = "schedule-recovery",
  onDemoPackageChange
}) {
  const projectCount = projects.length;
  const reportCount = reports.length;
  const remaining = credits?.remaining ?? 0;
  const project = projects[0];
  const selectedPackage = analysisPackages.find((item) => item.id === activeDemoPackage) || analysisPackages[0];
  const packageInsight = demoWorkspace.packageInsights?.[activeDemoPackage] || demoWorkspace.packageInsights?.["schedule-recovery"];

  function openPackage(packageId) {
    onDemoPackageChange?.(packageId);
    onNavigate("result");
  }

  return (
    <>
      <PageHeader
        eyebrow={demoMode ? "Workspace preview" : "Workspace dashboard"}
        title={demoMode ? "Project control center." : "Control project uploads, dashboards and reports."}
        description={demoMode ? "A preview of the customer workspace after project files are mapped." : "This is the customer workspace after login. It stays empty until the customer uploads real project files."}
        action={<button className="primary-button" onClick={() => onNavigate(demoMode ? "result" : "upload")}>{demoMode ? "Open Active Dashboard" : "Start New Analysis"}</button>}
      />

      {demoMode && project ? (
        <section className="overview-hero panel featured">
          <div className="overview-hero-copy">
            <span className={`status-pill ${statusTone(packageInsight?.status)}`}>{packageInsight?.status || "Preview active"}</span>
            <h2>{project.project_name || project.name}</h2>
            <p>
              {project.location} workspace for reviewing schedule, cost, material and decision-control dashboards before connecting real project files.
            </p>
            <div className="overview-hero-actions">
              <button className="primary-button" type="button" onClick={() => onNavigate("upload")}>
                <UploadCloud size={17} /> Review upload flow
              </button>
              <button className="secondary-button" type="button" onClick={() => onNavigate("reports")}>
                <FileText size={17} /> View reports
              </button>
            </div>
          </div>
          <aside className="overview-hero-rail">
            <div className="overview-rail-icon"><BarChart3 size={24} /></div>
            <span>Active control package</span>
            <strong>{selectedPackage.name}</strong>
            <p>{packageInsight?.signal}</p>
            <div className="overview-rail-metric">
              <b>{packageInsight?.metric}</b>
              <small>{packageInsight?.metricLabel}</small>
            </div>
          </aside>
        </section>
      ) : null}

      <section className="kpi-grid overview-kpi-grid">
        <article>
          <span>Active projects</span>
          <strong>{formatCount(projectCount)}</strong>
          <small>Projects in this workspace</small>
        </article>
        <article>
          <span>Reports ready</span>
          <strong>{formatCount(reportCount)}</strong>
          <small>PDF / Excel outputs</small>
        </article>
        <article>
          <span>Remaining credits</span>
          <strong>{formatCount(remaining)}</strong>
          <small>Available project analyses</small>
        </article>
        <article>
          <span>Current status</span>
          <strong>{projectCount ? "Active" : "Empty"}</strong>
          <small>{projectCount ? "Workspace has project data" : "No uploaded project yet"}</small>
        </article>
      </section>

      {demoMode && project ? (
        <>
          <section className="overview-package-board panel">
            <div className="schedule-panel-head">
              <div>
                <span className="workspace-eyebrow">Dashboard packages</span>
                <h2>Choose a control board</h2>
              </div>
              <Activity size={22} />
            </div>
            <PackageSegmentedControl
              activePackage={activeDemoPackage}
              onPackageOpen={openPackage}
              showMetric
              ariaLabel="Open dashboard package"
            />
          </section>

          <section className="overview-project-grid">
            <article className="panel overview-project-card">
              <div className="schedule-panel-head">
                <div>
                  <span className="workspace-eyebrow">Project record</span>
                  <h2>{project.project_name || project.name}</h2>
                </div>
                <CalendarDays size={22} />
              </div>
              <div className="overview-project-stats">
                <div><span>Client</span><strong>{project.client_name}</strong></div>
                <div><span>Contract</span><strong>{formatMoney(project.contract_value, project.currency)}</strong></div>
                <div><span>Planned</span><strong>{project.planned_progress}%</strong></div>
                <div><span>Actual</span><strong>{project.actual_progress}%</strong></div>
              </div>
              <p>{packageInsight?.nextStep}</p>
              <button className="secondary-button" type="button" onClick={() => onNavigate("result")}>Open dashboard</button>
            </article>

            <article className="panel overview-report-card">
              <div className="schedule-panel-head">
                <div>
                  <span className="workspace-eyebrow">Latest outputs</span>
                  <h2>Report snapshots</h2>
                </div>
                <FileText size={22} />
              </div>
              <div className="overview-report-list">
                {reports.slice(0, 3).map((report) => (
                  <div key={report.report_id || report.id}>
                    <span>{report.package_name || report.format}</span>
                    <strong>{report.report_name || report.name}</strong>
                    <small>{formatDate(report.generated_at)} - {report.status || "Ready"}</small>
                  </div>
                ))}
              </div>
              <button className="secondary-button" type="button" onClick={() => onNavigate("reports")}>Open archive</button>
            </article>
          </section>

          <section className="overview-workflow-grid">
            {demoWorkspace.demoWorkflow.map((step) => (
              <article className="overview-workflow-card" key={step.step}>
                <b>{step.step}</b>
                <div>
                  <span>{step.status}</span>
                  <strong>{step.title}</strong>
                  <p>{step.description}</p>
                </div>
                <CheckCircle2 size={18} />
              </article>
            ))}
          </section>
        </>
      ) : projectCount === 0 ? (
        <EmptyState
          title="No project data yet."
          description="Upload schedule, cost, payment, material or risk files to generate the first management dashboard."
          action={<button className="secondary-button" onClick={() => onNavigate("upload")}>Open Upload Flow</button>}
        />
      ) : (
        <section className="panel">
          <h2>Recent projects</h2>
          <div className="table-list">
            {projects.slice(0, 5).map((item) => (
              <article key={item.project_id || item.id}>
                <strong>{item.project_name || item.name || "Untitled project"}</strong>
                <span>{item.current_status || item.status || "Uploaded"}</span>
              </article>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
