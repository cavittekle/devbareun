import {
  Activity,
  ArrowRight,
  BarChart3,
  FileText,
  FolderKey,
  Gauge,
  ShieldAlert,
  UploadCloud,
  UsersRound
} from "lucide-react";
import { EmptyState, PageHeader } from "../components/Shell";
import { analysisPackages } from "../data/packages";
import { demoWorkspace } from "../data/demoWorkspace";

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

function packageIcon(packageId) {
  if (packageId === "cost-control") return Gauge;
  if (packageId === "material-continuity") return FileText;
  if (packageId === "risk-decisions") return ShieldAlert;
  return BarChart3;
}

function progressGap(project) {
  const planned = Number(project?.planned_progress);
  const actual = Number(project?.actual_progress);
  if (!Number.isFinite(planned) || !Number.isFinite(actual)) return null;
  return planned - actual;
}

export function Projects({
  projects,
  onNavigate,
  demoMode = false,
  activeDemoPackage = "schedule-recovery",
  onDemoPackageChange
}) {
  const selectedPackage = analysisPackages.find((item) => item.id === activeDemoPackage) || analysisPackages[0];
  const packageInsight = demoWorkspace.packageInsights?.[activeDemoPackage] || demoWorkspace.packageInsights?.["schedule-recovery"];
  const SelectedIcon = packageIcon(selectedPackage.id);
  const project = projects[0];
  const reportCount = demoMode ? demoWorkspace.reports.length : 0;

  function openPackage(packageId) {
    onDemoPackageChange?.(packageId);
    onNavigate("result");
  }

  return (
    <>
      <PageHeader
        eyebrow={demoMode ? "Project archive preview" : "Project archive"}
        title={demoMode ? "Project command archive." : "My Projects"}
        description={demoMode ? "A customer-facing archive view with project health, access, reports and active dashboard routing." : "Uploaded projects and generated dashboards will appear here."}
        action={<button className="primary-button" onClick={() => onNavigate("upload")}><UploadCloud size={17} /> {demoMode ? "Review upload flow" : "Upload Project"}</button>}
      />
      {projects.length === 0 ? (
        <EmptyState
          title="No projects yet."
          description="A customer workspace should stay clean until real files are uploaded."
          action={<button className="secondary-button" onClick={() => onNavigate("upload")}>Create First Project</button>}
        />
      ) : demoMode && project ? (
        <>
          <section className="project-command-hero panel featured">
            <div>
              <span className={`status-pill ${statusTone(project.current_status || project.status)}`}>{project.current_status || project.status}</span>
              <h2>{project.project_name || project.name}</h2>
              <p>{project.location} - {project.client_name}. This archive connects the selected project to dashboards, reports, access control and activity traceability.</p>
              <div className="project-command-actions">
                <button className="primary-button" type="button" onClick={() => onNavigate("result")}>Open active dashboard</button>
                <button className="secondary-button" type="button" onClick={() => onNavigate("reports")}>View reports</button>
                <button className="secondary-button" type="button" onClick={() => onNavigate("project-activity")}>Activity</button>
              </div>
            </div>
            <aside>
              <div className="project-package-icon"><SelectedIcon size={24} /></div>
              <span>Active package</span>
              <strong>{selectedPackage.name}</strong>
              <p>{packageInsight?.nextStep}</p>
              <b>{packageInsight?.metric}</b>
              <small>{packageInsight?.metricLabel}</small>
            </aside>
          </section>

          <section className="project-health-grid">
            <article>
              <span>Contract value</span>
              <strong>{formatMoney(project.contract_value, project.currency)}</strong>
              <small>Project baseline</small>
            </article>
            <article>
              <span>Progress gap</span>
              <strong>{progressGap(project) === null ? "-" : `+${progressGap(project)} pp`}</strong>
              <small>{project.planned_progress}% planned - {project.actual_progress}% actual</small>
            </article>
            <article>
              <span>Delay exposure</span>
              <strong>{project.delay_days} days</strong>
              <small>Largest schedule signal</small>
            </article>
            <article>
              <span>Risk score</span>
              <strong>{project.risk_score}/100</strong>
              <small>Package-aware control signal</small>
            </article>
          </section>

          <section className="project-archive-grid">
            <article className="panel project-archive-card">
              <div className="team-section-head">
                <div>
                  <span className="workspace-eyebrow">Project record</span>
                  <h2>{project.project_name || project.name}</h2>
                  <p>Updated {formatDate(project.updated_at)} - {project.location}</p>
                </div>
                <FolderKey size={24} />
              </div>
              <div className="project-progress-stack">
                <div>
                  <span>Planned progress</span>
                  <strong>{project.planned_progress}%</strong>
                  <i><b style={{ width: `${project.planned_progress}%` }} /></i>
                </div>
                <div>
                  <span>Actual progress</span>
                  <strong>{project.actual_progress}%</strong>
                  <i><b style={{ width: `${project.actual_progress}%` }} /></i>
                </div>
              </div>
              <div className="project-card-actions">
                <button className="secondary-button" type="button" onClick={() => onNavigate("result")}>Dashboard <ArrowRight size={16} /></button>
                <button className="secondary-button" type="button" onClick={() => onNavigate("project-access")}>Access <UsersRound size={16} /></button>
              </div>
            </article>

            <article className="panel project-routing-card">
              <div className="team-section-head">
                <div>
                  <span className="workspace-eyebrow">Control routing</span>
                  <h2>Package dashboards</h2>
                  <p>Switch the project archive into the dashboard you want to inspect.</p>
                </div>
                <Activity size={24} />
              </div>
              <div className="project-package-list">
                {analysisPackages.map((item) => {
                  const Icon = packageIcon(item.id);
                  const insight = demoWorkspace.packageInsights?.[item.id];
                  return (
                    <button
                      key={item.id}
                      type="button"
                      className={item.id === activeDemoPackage ? "active" : ""}
                      onClick={() => openPackage(item.id)}
                    >
                      <Icon size={17} />
                      <span>
                        <strong>{item.name}</strong>
                        <small>{insight?.metric} - {insight?.metricLabel}</small>
                      </span>
                    </button>
                  );
                })}
              </div>
            </article>

            <article className="panel project-output-card">
              <div className="team-section-head">
                <div>
                  <span className="workspace-eyebrow">Archive outputs</span>
                  <h2>{reportCount} report snapshots</h2>
                  <p>Frozen outputs linked to the same sample project record.</p>
                </div>
                <FileText size={24} />
              </div>
              <div className="project-output-list">
                {demoWorkspace.reports.slice(0, 3).map((report) => (
                  <div key={report.report_id || report.id}>
                    <span>{report.package_name}</span>
                    <strong>{report.report_name || report.name}</strong>
                    <small>{report.format} - {report.status}</small>
                  </div>
                ))}
              </div>
              <button className="secondary-button full" type="button" onClick={() => onNavigate("reports")}>Open report archive</button>
            </article>
          </section>
        </>
      ) : (
        <section className="card-grid">
          {projects.map((item) => (
            <article className="panel" key={item.project_id || item.id}>
              <span className="workspace-eyebrow">{item.current_status || item.status || "Project"}</span>
              <h2>{item.project_name || item.name || "Untitled project"}</h2>
              <p>{item.location || item.client_name || "Project details will update after mapping."}</p>
            </article>
          ))}
        </section>
      )}
    </>
  );
}
