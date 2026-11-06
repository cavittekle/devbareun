import { useEffect, useMemo, useState } from "react";
import { FolderKey, RefreshCw, ShieldCheck, UsersRound } from "lucide-react";
import { workspaceApi } from "../api/client";
import { EmptyState, PageHeader } from "../components/Shell";
import { useT } from "../lib/i18n";
import { roleLabel } from "./Team";


export function ProjectAccess() {
  const t = useT();
  const [projects, setProjects] = useState([]);
  const [members, setMembers] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [grants, setGrants] = useState([]);
  const [selectedMembershipId, setSelectedMembershipId] = useState("");
  const [projectRole, setProjectRole] = useState("viewer");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const selectedProject = useMemo(
    () => projects.find((project) => String(project.project_id || project.id) === selectedProjectId),
    [projects, selectedProjectId]
  );
  const activeMembers = useMemo(() => members.filter((item) => item.status === "active" && item.company_role !== "owner"), [members]);

  async function loadBase() {
    setLoading(true); setError("");
    try {
      const [projectPayload, workspace] = await Promise.all([workspaceApi.projectAccessProjects(), workspaceApi.companyWorkspace()]);
      const items = projectPayload.projects || [];
      setProjects(items);
      setMembers(workspace.members || []);
      const next = selectedProjectId || String(items[0]?.project_id || items[0]?.id || "");
      setSelectedProjectId(next);
    } catch (err) {
      setError(err.message || t("We couldn't load project sharing. Try Refresh in a minute.", "Layihə paylaşmasını yükləmək olmadı. Bir dəqiqə sonra Yenilə düyməsini basın."));
    } finally { setLoading(false); }
  }

  async function loadGrants(projectId = selectedProjectId) {
    if (!projectId) { setGrants([]); return; }
    setBusy("grants"); setError("");
    try {
      const payload = await workspaceApi.projectAccessMembers(projectId);
      setGrants(payload.grants || []);
    } catch (err) {
      // A viewer/editor can see the workspace but cannot inspect roster data.
      setGrants([]);
      setError(err.code === "forbidden" ? t("Only the project owner or a project manager can change who has access.", "Girişi yalnız layihənin sahibi və ya layihə meneceri dəyişə bilər.") : (err.message || t("We couldn't load who has access. Try again in a minute.", "Kimin girişi olduğunu yükləmək olmadı. Bir dəqiqə sonra yenidən cəhd edin.")));
    } finally { setBusy(""); }
  }

  useEffect(() => { loadBase(); }, []);
  useEffect(() => { if (selectedProjectId) loadGrants(selectedProjectId); }, [selectedProjectId]);

  async function addGrant(event) {
    event.preventDefault();
    if (!selectedProjectId || !selectedMembershipId) return;
    setBusy("grant"); setError(""); setNotice("");
    try {
      await workspaceApi.grantProjectAccess(selectedProjectId, { membership_id: selectedMembershipId, project_role: projectRole });
      setNotice(t("Access given.", "Giriş verildi.")); setSelectedMembershipId(""); await loadGrants();
    } catch (err) { setError(err.message || t("Access wasn't given. Try again in a minute.", "Giriş verilmədi. Bir dəqiqə sonra yenidən cəhd edin.")); }
    finally { setBusy(""); }
  }

  async function patchGrant(grant, patch) {
    setBusy(`grant-${grant.grant_id}`); setError(""); setNotice("");
    try { await workspaceApi.updateProjectAccess(selectedProjectId, grant.grant_id, patch); setNotice(t("Access updated.", "Giriş yeniləndi.")); await loadGrants(); }
    catch (err) { setError(err.message || t("Access wasn't updated. Try again in a minute.", "Giriş yenilənmədi. Bir dəqiqə sonra yenidən cəhd edin.")); }
    finally { setBusy(""); }
  }

  async function revokeGrant(grant) {
    setBusy(`grant-${grant.grant_id}`); setError(""); setNotice("");
    try { await workspaceApi.revokeProjectAccess(selectedProjectId, grant.grant_id); setNotice(t("Access removed.", "Giriş götürüldü.")); await loadGrants(); }
    catch (err) { setError(err.message || t("Access wasn't removed. Try again in a minute.", "Giriş götürülmədi. Bir dəqiqə sonra yenidən cəhd edin.")); }
    finally { setBusy(""); }
  }

  return (
    <>
      <PageHeader eyebrow={t("Sharing", "Paylaşma")} title={t("Project access", "Layihəyə giriş")} description={t("Being in the company does not open a project. Share each project with the colleagues who need it.", "Şirkətdə olmaq layihəni açmır. Hər layihəni ona ehtiyacı olan həmkarlarla paylaşın.")} action={<button type="button" className="secondary-button" onClick={loadBase} disabled={loading}><RefreshCw size={16} aria-hidden="true" /> {t("Refresh", "Yenilə")}</button>} />
      {error ? <div className="status-box warning" role="alert">{error}</div> : null}
      {notice ? <div className="status-box info" role="status">{notice}</div> : null}
      {loading ? <div className="status-box info" role="status">{t("Loading projects…", "Layihələr yüklənir…")}</div> : null}
      {!loading && projects.length === 0 ? <EmptyState title={t("No projects to share yet.", "Paylaşmaq üçün hələ layihə yoxdur.")} description={t("Upload a project first, then share it with a colleague from your company.", "Əvvəlcə layihə yükləyin, sonra onu şirkətinizdən bir həmkarla paylaşın.")} /> : null}
      {!loading && projects.length ? <>
        <section className="panel project-access-panel">
          <div className="team-section-head"><div><span className="workspace-eyebrow">{t("Project", "Layihə")}</span><h2>{t("Choose a project", "Layihə seçin")}</h2><p>{t("Only the owner and project managers can change who has access.", "Girişi yalnız sahib və layihə menecerləri dəyişə bilər.")}</p></div><FolderKey size={24} aria-hidden="true" /></div>
          <select aria-label={t("Project", "Layihə")} value={selectedProjectId} onChange={(event) => setSelectedProjectId(event.target.value)}>
            {projects.map((project) => <option key={project.project_id || project.id} value={project.project_id || project.id}>{project.project_name || project.name || t("Untitled project", "Adsız layihə")}</option>)}
          </select>
          {selectedProject ? <small className="project-access-hint">{selectedProject.location || selectedProject.client_name || ""}</small> : null}
        </section>
        <section className="panel project-access-panel">
          <div className="team-section-head"><div><span className="workspace-eyebrow">{t("Share", "Paylaş")}</span><h2>{t("Share with a colleague", "Həmkarla paylaşın")}</h2><p>{t("Viewer sees the results. Editor can also upload files and run the analysis. Manager can also change who has access.", "İzləyici nəticələri görür. Redaktor həm də fayl yükləyib analizi başlada bilər. Menecer həm də girişi dəyişə bilər.")}</p></div><ShieldCheck size={24} aria-hidden="true" /></div>
          <form className="team-invite-form" onSubmit={addGrant}>
            <select aria-label={t("Colleague", "Həmkar")} required value={selectedMembershipId} onChange={(event) => setSelectedMembershipId(event.target.value)}><option value="">{t("Choose a colleague", "Həmkar seçin")}</option>{activeMembers.map((member) => <option key={member.membership_id} value={member.membership_id}>{member.member_email} · {roleLabel(member.company_role, t)}</option>)}</select>
            <select aria-label={t("Project role", "Layihə rolu")} value={projectRole} onChange={(event) => setProjectRole(event.target.value)}><option value="viewer">{roleLabel("viewer", t)}</option><option value="editor">{roleLabel("editor", t)}</option><option value="manager">{roleLabel("manager", t)}</option></select>
            <button className="primary-button" type="submit" disabled={busy === "grant" || !selectedMembershipId}>{busy === "grant" ? t("Sharing…", "Paylaşılır…") : t("Share project", "Layihəni paylaş")}</button>
          </form>
        </section>
        <section className="panel team-roster-panel"><div className="team-section-head"><div><span className="workspace-eyebrow">{t("Who has access", "Kimin girişi var")}</span><h2>{t("People with access to this project", "Bu layihəyə girişi olanlar")}</h2><p>{t("Removed access stays in the list as a record.", "Götürülmüş giriş qeyd kimi siyahıda qalır.")}</p></div><UsersRound size={24} aria-hidden="true" /></div><div className="team-list">{busy === "grants" ? <p className="team-empty">{t("Loading…", "Yüklənir…")}</p> : grants.length ? grants.map((grant) => <article className="team-member-row" key={grant.grant_id}><div><strong>{grant.member_email}</strong><small>{roleLabel(grant.project_role, t)} · {grant.status}</small></div><div className="team-member-actions"><select aria-label={`${t("Project role", "Layihə rolu")}: ${grant.member_email}`} value={grant.project_role} disabled={grant.status !== "active" || busy === `grant-${grant.grant_id}`} onChange={(event) => patchGrant(grant, { project_role: event.target.value })}><option value="manager">{roleLabel("manager", t)}</option><option value="editor">{roleLabel("editor", t)}</option><option value="viewer">{roleLabel("viewer", t)}</option></select>{grant.status === "active" ? <button className="secondary-button" type="button" disabled={busy === `grant-${grant.grant_id}`} onClick={() => revokeGrant(grant)}>{t("Remove access", "Girişi götür")}</button> : <span className="team-role-pill">{t("Removed", "Götürülüb")}</span>}</div></article>) : <p className="team-empty">{t("Not shared with anyone yet.", "Hələ heç kimlə paylaşılmayıb.")}</p>}</div></section>
      </> : null}
    </>
  );
}
