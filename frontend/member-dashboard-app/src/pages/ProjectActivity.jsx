import { useEffect, useMemo, useState } from "react";
import { Activity, RefreshCw, ShieldCheck } from "lucide-react";
import { workspaceApi } from "../api/client";
import { EmptyState, PageHeader } from "../components/Shell";

const ACTION_LABELS = {
  "project_access.granted": "Project access granted",
  "project_access.updated": "Project access updated",
  "project_access.revoked": "Project access revoked",
  "upload.prepared": "Upload prepared",
  "upload.completed": "File uploaded",
  "upload.deleted": "File removed",
  "analysis.queued": "Analysis queued",
  "analysis.completed": "Analysis completed",
  "analysis.failed": "Analysis failed",
  "report.generated": "Report generated",
  "report.downloaded": "Report downloaded"
};

function displayDate(value) {
  if (!value) return "Time unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

function actorLabel(event) {
  if (event?.actor?.type === "system") return "DevBareun system";
  return event?.actor?.email || "Project member";
}

export function ProjectActivity() {
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [error, setError] = useState("");

  const selectedProject = useMemo(
    () => projects.find((project) => String(project.project_id || project.id) === String(selectedProjectId)),
    [projects, selectedProjectId]
  );

  async function loadProjects() {
    setLoading(true); setError("");
    try {
      const result = await workspaceApi.projectAccessProjects();
      const rows = result?.projects || [];
      setProjects(rows);
      setSelectedProjectId((current) => current || String(rows[0]?.project_id || rows[0]?.id || ""));
    } catch (err) {
      setError(err.message || "Project activity could not be loaded.");
    } finally { setLoading(false); }
  }

  async function loadTimeline(projectId = selectedProjectId) {
    if (!projectId) { setEvents([]); return; }
    setTimelineLoading(true); setError("");
    try {
      const result = await workspaceApi.projectActivity(projectId);
      setEvents(result?.events || []);
    } catch (err) {
      setError(err.message || "Project activity could not be loaded.");
    } finally { setTimelineLoading(false); }
  }

  useEffect(() => { loadProjects(); }, []);
  useEffect(() => { if (selectedProjectId) loadTimeline(selectedProjectId); }, [selectedProjectId]);

  return (
    <>
      <PageHeader
        eyebrow="Project traceability"
        title="Project Activity"
        description="A collaboration-safe timeline of uploads, analyses, reports and project access changes."
        action={<button className="secondary-button" onClick={() => loadTimeline()} disabled={timelineLoading || !selectedProjectId}><RefreshCw size={16} /> Refresh</button>}
      />
      {error ? <div className="status-box warning">{error}</div> : null}
      {loading ? <div className="status-box info">Loading accessible projects…</div> : null}
      {!loading && projects.length === 0 ? <EmptyState title="No accessible projects." description="Project activity appears after you own or receive explicit access to a project." /> : null}
      {!loading && projects.length > 0 ? <>
        <section className="panel project-activity-scope">
          <div className="team-section-head"><div><span className="workspace-eyebrow">Project scope</span><h2>Choose a project</h2><p>Only the owner and explicitly shared project roles can view this timeline.</p></div><ShieldCheck size={24} /></div>
          <select value={selectedProjectId} onChange={(event) => setSelectedProjectId(event.target.value)}>
            {projects.map((project) => <option key={project.project_id || project.id} value={project.project_id || project.id}>{project.project_name || project.name || "Untitled project"}</option>)}
          </select>
          {selectedProject ? <small className="project-access-hint">{selectedProject.location || selectedProject.client_name || "Project workspace"}</small> : null}
        </section>
        <section className="panel project-activity-panel">
          <div className="team-section-head"><div><span className="workspace-eyebrow">Recent events</span><h2>Collaboration timeline</h2><p>Events are append-only. Sensitive storage paths, signed URLs and credentials are never shown here.</p></div><Activity size={24} /></div>
          {timelineLoading ? <p className="team-empty">Loading activity timeline…</p> : null}
          {!timelineLoading && events.length === 0 ? <p className="team-empty">No project activity has been recorded since timeline tracking was enabled.</p> : null}
          {!timelineLoading && events.length > 0 ? (
            <div className="project-activity-list">
              {events.map((event) => (
                <article className="project-activity-row" key={event.event_id}>
                  <div className="project-activity-marker"><Activity size={15} /></div>
                  <div className="project-activity-content">
                    <strong>{ACTION_LABELS[event.action] || event.action}</strong>
                    <small>{actorLabel(event)} · {displayDate(event.occurred_at)}</small>
                    {event.metadata?.risk_count !== undefined ? <span className="project-activity-detail">{event.metadata.risk_count} risk item(s) recorded</span> : null}
                    {event.metadata?.project_role ? <span className="project-activity-detail">Project role: {event.metadata.project_role}</span> : null}
                    {event.metadata?.format ? <span className="project-activity-detail">Format: {event.metadata.format}</span> : null}
                  </div>
                </article>
              ))}
            </div>
          ) : null}
        </section>
      </> : null}
    </>
  );
}
