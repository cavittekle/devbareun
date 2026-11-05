import { EmptyState, PageHeader } from "../components/Shell";

export function Projects({ projects, onNavigate }) {
  return (
    <>
      <PageHeader
        eyebrow="Project archive"
        title="My projects"
        description="Uploaded projects and generated dashboards will appear here."
        action={<button className="primary-button" onClick={() => onNavigate("upload")}>New delay analysis</button>}
      />
      {projects.length === 0 ? (
        <EmptyState
          title="No projects yet."
          description="Projects appear here after you upload the planning file for a delay analysis."
          action={<button className="secondary-button" onClick={() => onNavigate("upload")}>Create the first project</button>}
        />
      ) : (
        <section className="card-grid">
          {projects.map((project) => (
            <article className="panel" key={project.project_id || project.id}>
              <span className="workspace-eyebrow">{project.current_status || project.status || "Project"}</span>
              <h2>{project.project_name || project.name || "Untitled project"}</h2>
              <p>{project.location || project.client_name || "Project details will update after mapping."}</p>
            </article>
          ))}
        </section>
      )}
    </>
  );
}
