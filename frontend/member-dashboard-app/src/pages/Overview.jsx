import { PageHeader, EmptyState } from "../components/Shell";
import { formatCount } from "../lib/format";

export function Overview({ projects, reports, credits, onNavigate }) {
  const projectCount = projects.length;
  const reportCount = reports.length;
  const remaining = credits?.remaining ?? 0;

  return (
    <>
      <PageHeader
        eyebrow="Workspace dashboard"
        title="Your delay analyses"
        description="Projects, execution reports and remaining analysis credits in one place."
        action={<button className="primary-button" onClick={() => onNavigate("upload")}>Start new analysis</button>}
      />

      <section className="kpi-grid">
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

      {projectCount === 0 ? (
        <EmptyState
          title="No project data yet."
          description="Upload the planning file, and optionally the contract and F2 certificates, to get the first execution and delay report."
          action={<button className="secondary-button" onClick={() => onNavigate("upload")}>Open the upload page</button>}
        />
      ) : (
        <section className="panel">
          <h2>Recent projects</h2>
          <div className="table-list">
            {projects.slice(0, 5).map((project) => (
              <article key={project.project_id || project.id}>
                <strong>{project.project_name || project.name || "Untitled project"}</strong>
                <span>{project.current_status || project.status || "Uploaded"}</span>
              </article>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
