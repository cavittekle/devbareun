import { useEffect, useMemo, useState } from "react";
import { Activity, RefreshCw, ShieldCheck } from "lucide-react";
import { workspaceApi } from "../api/client";
import { EmptyState, PageHeader } from "../components/Shell";
import { useT } from "../lib/i18n";

const ACTION_LABELS = {
  "project_access.granted": ["Access given", "Giriş verildi"],
  "project_access.updated": ["Access updated", "Giriş yeniləndi"],
  "project_access.revoked": ["Access removed", "Giriş götürüldü"],
  "upload.prepared": ["Upload started", "Yükləmə başladı"],
  "upload.completed": ["File uploaded", "Fayl yükləndi"],
  "upload.deleted": ["File removed", "Fayl silindi"],
  "analysis.queued": ["Analysis started", "Analiz başladı"],
  "analysis.completed": ["Analysis finished", "Analiz bitdi"],
  "analysis.failed": ["Analysis failed", "Analiz alınmadı"],
  "report.generated": ["Report ready", "Hesabat hazırdır"],
  "report.downloaded": ["Report downloaded", "Hesabat yükləndi"]
};

function displayDate(value, t) {
  if (!value) return t("Time unknown", "Vaxt naməlum");
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

function actorLabel(event, t) {
  if (event?.actor?.type === "system") return "DevBareun";
  return event?.actor?.email || t("Project member", "Layihə üzvü");
}

export function ProjectActivity() {
  const t = useT();
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
      setError(err.message || t("We couldn't load project activity. Try Refresh in a minute.", "Layihə fəaliyyətini yükləmək olmadı. Bir dəqiqə sonra Yenilə düyməsini basın."));
    } finally { setLoading(false); }
  }

  async function loadTimeline(projectId = selectedProjectId) {
    if (!projectId) { setEvents([]); return; }
    setTimelineLoading(true); setError("");
    try {
      const result = await workspaceApi.projectActivity(projectId);
      setEvents(result?.events || []);
    } catch (err) {
      setError(err.message || t("We couldn't load project activity. Try Refresh in a minute.", "Layihə fəaliyyətini yükləmək olmadı. Bir dəqiqə sonra Yenilə düyməsini basın."));
    } finally { setTimelineLoading(false); }
  }

  useEffect(() => { loadProjects(); }, []);
  useEffect(() => { if (selectedProjectId) loadTimeline(selectedProjectId); }, [selectedProjectId]);

  return (
    <>
      <PageHeader
        eyebrow={t("Activity", "Fəaliyyət")}
        title={t("Project activity", "Layihə fəaliyyəti")}
        description={t("Who uploaded files, ran analyses, downloaded reports or changed access, and when.", "Kim nə vaxt fayl yükləyib, analiz başladıb, hesabat yükləyib və ya girişi dəyişib.")}
        action={<button type="button" className="secondary-button" onClick={() => loadTimeline()} disabled={timelineLoading || !selectedProjectId}><RefreshCw size={16} aria-hidden="true" /> {t("Refresh", "Yenilə")}</button>}
      />
      {error ? <div className="status-box warning" role="alert">{error}</div> : null}
      {loading ? <div className="status-box info" role="status">{t("Loading projects…", "Layihələr yüklənir…")}</div> : null}
      {!loading && projects.length === 0 ? <EmptyState title={t("No project activity yet.", "Hələ layihə fəaliyyəti yoxdur.")} description={t("Activity appears here once you upload a project or someone shares one with you.", "Layihə yüklədikdə və ya kimsə sizinlə layihə paylaşdıqda fəaliyyət burada görünür.")} /> : null}
      {!loading && projects.length > 0 ? <>
        <section className="panel project-activity-scope">
          <div className="team-section-head"><div><span className="workspace-eyebrow">{t("Project", "Layihə")}</span><h2>{t("Choose a project", "Layihə seçin")}</h2><p>{t("Only the owner and people the project is shared with see this activity.", "Bu fəaliyyəti yalnız sahib və layihənin paylaşıldığı şəxslər görür.")}</p></div><ShieldCheck size={24} aria-hidden="true" /></div>
          <select aria-label={t("Project", "Layihə")} value={selectedProjectId} onChange={(event) => setSelectedProjectId(event.target.value)}>
            {projects.map((project) => <option key={project.project_id || project.id} value={project.project_id || project.id}>{project.project_name || project.name || t("Untitled project", "Adsız layihə")}</option>)}
          </select>
          {selectedProject ? <small className="project-access-hint">{selectedProject.location || selectedProject.client_name || ""}</small> : null}
        </section>
        <section className="panel project-activity-panel">
          <div className="team-section-head"><div><span className="workspace-eyebrow">{t("Recent events", "Son hadisələr")}</span><h2>{t("Activity timeline", "Fəaliyyət xronologiyası")}</h2><p>{t("Events can't be edited or deleted. File locations and links are never shown here.", "Hadisələr dəyişdirilə və ya silinə bilməz. Fayl yerləri və keçidlər burada göstərilmir.")}</p></div><Activity size={24} aria-hidden="true" /></div>
          {timelineLoading ? <p className="team-empty">{t("Loading…", "Yüklənir…")}</p> : null}
          {!timelineLoading && events.length === 0 ? <p className="team-empty">{t("No activity recorded for this project yet.", "Bu layihə üzrə hələ fəaliyyət qeydə alınmayıb.")}</p> : null}
          {!timelineLoading && events.length > 0 ? (
            <div className="project-activity-list">
              {events.map((event) => (
                <article className="project-activity-row" key={event.event_id}>
                  <div className="project-activity-marker" aria-hidden="true"><Activity size={15} /></div>
                  <div className="project-activity-content">
                    <strong>{ACTION_LABELS[event.action] ? t(...ACTION_LABELS[event.action]) : event.action}</strong>
                    <small>{actorLabel(event, t)} · {displayDate(event.occurred_at, t)}</small>
                    {event.metadata?.project_role ? <span className="project-activity-detail">{t("Project role", "Layihə rolu")}: {event.metadata.project_role}</span> : null}
                    {event.metadata?.format ? <span className="project-activity-detail">{t("Format", "Format")}: {event.metadata.format}</span> : null}
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
