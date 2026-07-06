import { useEffect, useMemo, useState } from "react";
import { FolderKey, RefreshCw, ShieldCheck, UsersRound } from "lucide-react";
import { workspaceApi } from "../api/client";
import { EmptyState, PageHeader } from "../components/Shell";
import { demoWorkspace } from "../data/demoWorkspace";

const ROLE_LABELS = { viewer: "Viewer", editor: "Editor", manager: "Manager" };

function demoProjectRows() {
  return demoWorkspace.projects.map((project) => ({
    ...project,
    id: project.project_id || project.id
  }));
}

export function ProjectAccess({ demoMode = false }) {
  const [projects, setProjects] = useState(demoMode ? demoProjectRows() : []);
  const [members, setMembers] = useState(demoMode ? demoWorkspace.team.members : []);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [grants, setGrants] = useState(demoMode ? demoWorkspace.projectAccess.grants : []);
  const [selectedMembershipId, setSelectedMembershipId] = useState("");
  const [projectRole, setProjectRole] = useState("viewer");
  const [loading, setLoading] = useState(!demoMode);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const selectedProject = useMemo(
    () => projects.find((project) => String(project.project_id || project.id) === selectedProjectId),
    [projects, selectedProjectId]
  );
  const activeMembers = useMemo(() => members.filter((item) => item.status === "active" && item.company_role !== "owner"), [members]);

  async function loadBase() {
    if (demoMode) {
      const items = demoProjectRows();
      setProjects(items);
      setMembers(demoWorkspace.team.members);
      setSelectedProjectId((current) => current || String(items[0]?.project_id || items[0]?.id || ""));
      setLoading(false);
      setError("");
      return;
    }
    setLoading(true); setError("");
    try {
      const [projectPayload, workspace] = await Promise.all([workspaceApi.projectAccessProjects(), workspaceApi.companyWorkspace()]);
      const items = projectPayload.projects || [];
      setProjects(items);
      setMembers(workspace.members || []);
      const next = selectedProjectId || String(items[0]?.project_id || items[0]?.id || "");
      setSelectedProjectId(next);
    } catch (err) {
      setError(err.message || "Project sharing could not be loaded.");
    } finally { setLoading(false); }
  }

  async function loadGrants(projectId = selectedProjectId) {
    if (!projectId) { setGrants([]); return; }
    if (demoMode) {
      setGrants(demoWorkspace.projectAccess.grants);
      return;
    }
    setBusy("grants"); setError("");
    try {
      const payload = await workspaceApi.projectAccessMembers(projectId);
      setGrants(payload.grants || []);
    } catch (err) {
      // A viewer/editor can see the workspace but cannot inspect roster data.
      setGrants([]);
      setError(err.code === "forbidden" ? "Only the project owner or a project manager can manage access." : (err.message || "Project access could not be loaded."));
    } finally { setBusy(""); }
  }

  useEffect(() => { loadBase(); }, [demoMode]);
  useEffect(() => { if (selectedProjectId) loadGrants(selectedProjectId); }, [selectedProjectId]);

  async function addGrant(event) {
    event.preventDefault();
    if (!selectedProjectId || !selectedMembershipId) return;
    if (demoMode) {
      const member = activeMembers.find((item) => item.membership_id === selectedMembershipId);
      if (!member) return;
      const nextGrant = {
        grant_id: `demo-grant-${Date.now()}`,
        member_email: member.member_email,
        project_role: projectRole,
        status: "active"
      };
      setGrants((current) => [nextGrant, ...current]);
      setNotice("Preview project access granted locally.");
      setSelectedMembershipId("");
      return;
    }
    setBusy("grant"); setError(""); setNotice("");
    try {
      await workspaceApi.grantProjectAccess(selectedProjectId, { membership_id: selectedMembershipId, project_role: projectRole });
      setNotice("Project access granted."); setSelectedMembershipId(""); await loadGrants();
    } catch (err) { setError(err.message || "Project access could not be granted."); }
    finally { setBusy(""); }
  }

  async function patchGrant(grant, patch) {
    if (demoMode) {
      setGrants((current) => current.map((item) => item.grant_id === grant.grant_id ? { ...item, ...patch } : item));
      setNotice("Preview project access updated locally.");
      return;
    }
    setBusy(`grant-${grant.grant_id}`); setError(""); setNotice("");
    try { await workspaceApi.updateProjectAccess(selectedProjectId, grant.grant_id, patch); setNotice("Project access updated."); await loadGrants(); }
    catch (err) { setError(err.message || "Project access could not be updated."); }
    finally { setBusy(""); }
  }

  async function revokeGrant(grant) {
    if (demoMode) {
      setGrants((current) => current.map((item) => item.grant_id === grant.grant_id ? { ...item, status: "revoked" } : item));
      setNotice("Preview project access revoked locally.");
      return;
    }
    setBusy(`grant-${grant.grant_id}`); setError(""); setNotice("");
    try { await workspaceApi.revokeProjectAccess(selectedProjectId, grant.grant_id); setNotice("Project access revoked."); await loadGrants(); }
    catch (err) { setError(err.message || "Project access could not be revoked."); }
    finally { setBusy(""); }
  }

  return (
    <>
      <PageHeader eyebrow={demoMode ? "Collaboration control preview" : "Collaboration control"} title="Project Access" description={demoMode ? "Preview explicit project grants with local sample membership data." : "Company membership never gives automatic project access. Share each project explicitly."} action={<button className="secondary-button" onClick={loadBase} disabled={loading}><RefreshCw size={16} /> Refresh</button>} />
      {error ? <div className="status-box warning">{error}</div> : null}
      {notice ? <div className="status-box info">{notice}</div> : null}
      {loading ? <div className="status-box info">Loading project access...</div> : null}
      {!loading && projects.length === 0 ? <EmptyState title="No accessible projects." description="Create a project first, then share it with an active company member." /> : null}
      {!loading && projects.length ? <>
        <section className="panel project-access-panel">
          <div className="team-section-head"><div><span className="workspace-eyebrow">Project scope</span><h2>Choose a project</h2><p>Only owners and explicit project managers can change the access roster.</p></div><FolderKey size={24} /></div>
          <select value={selectedProjectId} onChange={(event) => setSelectedProjectId(event.target.value)}>
            {projects.map((project) => <option key={project.project_id || project.id} value={project.project_id || project.id}>{project.project_name || project.name || "Untitled project"}</option>)}
          </select>
          {selectedProject ? <small className="project-access-hint">{selectedProject.location || selectedProject.client_name || "Project workspace"}</small> : null}
        </section>
        <section className="panel project-access-panel">
          <div className="team-section-head"><div><span className="workspace-eyebrow">Grant access</span><h2>Share with an active company member</h2><p>Viewer reads outcomes; editor can upload and run analysis; manager can also manage this roster.</p></div><ShieldCheck size={24} /></div>
          <form className="team-invite-form" onSubmit={addGrant}>
            <select required value={selectedMembershipId} onChange={(event) => setSelectedMembershipId(event.target.value)}><option value="">Choose a member</option>{activeMembers.map((member) => <option key={member.membership_id} value={member.membership_id}>{member.member_email} - {member.company_role}</option>)}</select>
            <select value={projectRole} onChange={(event) => setProjectRole(event.target.value)}><option value="viewer">Viewer</option><option value="editor">Editor</option><option value="manager">Manager</option></select>
            <button className="primary-button" type="submit" disabled={busy === "grant" || !selectedMembershipId}>{busy === "grant" ? "Granting..." : "Grant project access"}</button>
          </form>
        </section>
        <section className="panel team-roster-panel"><div className="team-section-head"><div><span className="workspace-eyebrow">Access roster</span><h2>Explicit project grants</h2><p>Revoked grants stay visible as an authorization record.</p></div><UsersRound size={24} /></div><div className="team-list">{busy === "grants" ? <p className="team-empty">Loading access roster...</p> : grants.length ? grants.map((grant) => <article className="team-member-row" key={grant.grant_id}><div><strong>{grant.member_email}</strong><small>{ROLE_LABELS[grant.project_role] || grant.project_role} - {grant.status}</small></div><div className="team-member-actions"><select value={grant.project_role} disabled={grant.status !== "active" || busy === `grant-${grant.grant_id}`} onChange={(event) => patchGrant(grant, { project_role: event.target.value })}><option value="manager">Manager</option><option value="editor">Editor</option><option value="viewer">Viewer</option></select>{grant.status === "active" ? <button className="secondary-button" type="button" disabled={busy === `grant-${grant.grant_id}`} onClick={() => revokeGrant(grant)}>Revoke</button> : <span className="team-role-pill">Revoked</span>}</div></article>) : <p className="team-empty">No project access grants yet.</p>}</div></section>
      </> : null}
    </>
  );
}
