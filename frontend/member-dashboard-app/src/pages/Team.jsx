import { useEffect, useMemo, useState } from "react";
import { Copy, RefreshCw, UsersRound } from "lucide-react";
import { EmptyState, PageHeader } from "../components/Shell";
import { workspaceApi } from "../api/client";
import { demoWorkspace } from "../data/demoWorkspace";

const ROLE_LABELS = {
  owner: "Owner",
  manager: "Manager",
  editor: "Editor",
  viewer: "Viewer"
};

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? String(value) : date.toLocaleString();
}

function readableStatus(value) {
  return String(value || "pending").replace(/_/g, " ");
}

function demoTeamPayload() {
  return {
    workspace: demoWorkspace.team.workspace,
    membership: demoWorkspace.team.membership,
    members: demoWorkspace.team.members,
    invitations: demoWorkspace.team.invitations,
    can_manage_team: true
  };
}

export function Team({ demoMode = false }) {
  const inviteToken = new URLSearchParams(location.search).get("invite") || "";
  const [payload, setPayload] = useState(demoMode ? demoTeamPayload() : null);
  const [loading, setLoading] = useState(!demoMode);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [invite, setInvite] = useState({ email: "", company_role: "viewer", expires_in_hours: 72 });
  const [inviteUrl, setInviteUrl] = useState("");

  const workspace = payload?.workspace || null;
  const membership = payload?.membership || null;
  const members = Array.isArray(payload?.members) ? payload.members : [];
  const invitations = Array.isArray(payload?.invitations) ? payload.invitations : [];
  const canManage = Boolean(payload?.can_manage_team);

  const activeMembers = useMemo(
    () => members.filter((member) => String(member?.status || "").toLowerCase() === "active"),
    [members]
  );

  async function refresh() {
    if (demoMode) {
      setPayload(demoTeamPayload());
      setLoading(false);
      setError("");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const next = await workspaceApi.companyWorkspace();
      setPayload(next || null);
    } catch (requestError) {
      setError(requestError?.message || "Company workspace could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, [demoMode]);

  async function createWorkspace(event) {
    event.preventDefault();
    if (!companyName.trim()) return;
    if (demoMode) {
      setPayload((current) => ({
        ...(current || demoTeamPayload()),
        workspace: { company_name: companyName.trim(), plan: "Plus" }
      }));
      setNotice("Preview workspace name updated locally.");
      setCompanyName("");
      return;
    }
    setBusy("workspace");
    setError("");
    setNotice("");
    try {
      const next = await workspaceApi.createCompanyWorkspace({ company_name: companyName.trim() });
      setPayload(next || null);
      setNotice(next?.created ? "Company workspace created." : "Existing company workspace loaded.");
      setCompanyName("");
    } catch (requestError) {
      setError(requestError?.message || "Company workspace could not be created.");
    } finally {
      setBusy("");
    }
  }

  async function acceptInvite() {
    if (!inviteToken) return;
    if (demoMode) {
      setNotice("Preview invitation accepted locally.");
      return;
    }
    setBusy("accept-invite");
    setError("");
    setNotice("");
    try {
      const next = await workspaceApi.acceptCompanyInvitation({ token: inviteToken });
      setPayload(next || null);
      setNotice("Invitation accepted. Your company membership is now active.");
      const current = new URL(location.href);
      current.searchParams.delete("invite");
      history.replaceState(null, "", current.toString());
    } catch (requestError) {
      setError(requestError?.message || "Invitation could not be accepted.");
    } finally {
      setBusy("");
    }
  }

  async function submitInvite(event) {
    event.preventDefault();
    if (demoMode) {
      const email = invite.email.trim();
      if (!email) return;
      const invitationId = `demo-invite-${Date.now()}`;
      const nextInvitation = {
        invitation_id: invitationId,
        invitee_email: email,
        company_role: invite.company_role,
        status: "pending",
        expires_at: new Date(Date.now() + Number(invite.expires_in_hours || 72) * 60 * 60 * 1000).toISOString()
      };
      setPayload((current) => ({
        ...(current || demoTeamPayload()),
        invitations: [nextInvitation, ...(current?.invitations || [])]
      }));
      setInviteUrl(`${location.origin}/workspace/?demo=1&invite=${invitationId}`);
      setNotice("Preview invitation created locally. No backend call was made.");
      setInvite({ email: "", company_role: "viewer", expires_in_hours: 72 });
      return;
    }
    setBusy("invite");
    setError("");
    setNotice("");
    setInviteUrl("");
    try {
      const response = await workspaceApi.inviteCompanyMember({
        email: invite.email.trim(),
        company_role: invite.company_role,
        expires_in_hours: Number(invite.expires_in_hours) || 72
      });
      setInviteUrl(response?.invite_url || "");
      setNotice(response?.notice || "Invitation created. Copy the one-time invitation URL.");
      setInvite({ email: "", company_role: "viewer", expires_in_hours: 72 });
      await refresh();
    } catch (requestError) {
      setError(requestError?.message || "Invitation could not be created.");
    } finally {
      setBusy("");
    }
  }

  async function copyInviteUrl() {
    if (!inviteUrl) return;
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setNotice("Invitation URL copied. It is shown only once; send it through an approved channel.");
    } catch {
      setError("Copy failed. Select and copy the invitation URL manually.");
    }
  }

  async function revokeInvitation(invitationId) {
    if (demoMode) {
      setPayload((current) => ({
        ...(current || demoTeamPayload()),
        invitations: (current?.invitations || []).map((item) => item.invitation_id === invitationId ? { ...item, status: "revoked" } : item)
      }));
      setNotice("Preview invitation revoked locally.");
      return;
    }
    if (!window.confirm("Revoke this pending invitation? The URL will no longer be accepted.")) return;
    setBusy(`revoke-${invitationId}`);
    setError("");
    try {
      await workspaceApi.revokeCompanyInvitation(invitationId);
      setNotice("Invitation revoked.");
      await refresh();
    } catch (requestError) {
      setError(requestError?.message || "Invitation could not be revoked.");
    } finally {
      setBusy("");
    }
  }

  async function changeMember(member, patch) {
    const memberId = member?.membership_id;
    if (!memberId) return;
    if (demoMode) {
      setPayload((current) => ({
        ...(current || demoTeamPayload()),
        members: (current?.members || []).map((item) => item.membership_id === memberId ? { ...item, ...patch } : item)
      }));
      setNotice("Preview member access updated locally.");
      return;
    }
    setBusy(`member-${memberId}`);
    setError("");
    try {
      await workspaceApi.updateCompanyMember(memberId, patch);
      setNotice("Member access updated.");
      await refresh();
    } catch (requestError) {
      setError(requestError?.message || "Member access could not be updated.");
    } finally {
      setBusy("");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow={demoMode ? "Company workspace preview" : "Company workspace"}
        title="Team roster and controlled invitations."
        description={demoMode ? "Preview company membership, invitations and role boundaries with local sample data." : "Manage company membership without automatically widening project access. Project sharing remains explicit and separate."}
        action={
          <button className="secondary-button" type="button" onClick={refresh} disabled={loading || Boolean(busy)}>
            <RefreshCw size={16} /> {loading ? "Refreshing..." : "Refresh"}
          </button>
        }
      />

      {error ? <div className="status-box error">{error}</div> : null}
      {notice ? <div className="status-box success">{notice}</div> : null}

      {inviteToken ? (
        <section className="panel team-invite-accept">
          <div>
            <span className="workspace-eyebrow">Invitation</span>
            <h2>Join a company workspace</h2>
            <p>Accept only when you are signed in with the exact email address that received this invitation.</p>
          </div>
          <button className="primary-button" type="button" disabled={busy === "accept-invite"} onClick={acceptInvite}>
            {busy === "accept-invite" ? "Accepting..." : "Accept invitation"}
          </button>
        </section>
      ) : null}

      {loading ? <div className="status-box info">Loading company workspace...</div> : null}

      {!loading && !workspace ? (
        <section className="team-bootstrap-grid">
          <EmptyState
            title="Create your company workspace"
            description="A company workspace keeps team membership and invitations in one controlled roster. It does not share projects automatically."
          />
          <form className="panel team-bootstrap-form" onSubmit={createWorkspace}>
            <span className="workspace-eyebrow">Workspace setup</span>
            <h2>Company name</h2>
            <p>Use the legal or operating name your team recognizes.</p>
            <input value={companyName} onChange={(event) => setCompanyName(event.target.value)} required minLength={2} maxLength={180} placeholder="Company name" />
            <button className="primary-button" type="submit" disabled={busy === "workspace"}>
              {busy === "workspace" ? "Creating..." : "Create company workspace"}
            </button>
          </form>
        </section>
      ) : null}

      {!loading && workspace ? (
        <>
          <section className="team-overview-grid">
            <article className="panel">
              <span className="workspace-eyebrow">Company</span>
              <h2>{workspace.company_name || "Company workspace"}</h2>
              <p>Plan: {workspace.plan || "free"}</p>
            </article>
            <article className="panel">
              <span className="workspace-eyebrow">Your company role</span>
              <h2>{ROLE_LABELS[membership?.company_role] || membership?.company_role || "-"}</h2>
              <p>Status: {readableStatus(membership?.status)}</p>
            </article>
            <article className="panel">
              <span className="workspace-eyebrow">Active members</span>
              <h2>{activeMembers.length}</h2>
              <p>{canManage ? "You can manage roster invitations." : "Your roster access is read-only."}</p>
            </article>
          </section>

          {canManage ? (
            <section className="panel team-invite-panel">
              <div className="team-section-head">
                <div>
                  <span className="workspace-eyebrow">Invite member</span>
                  <h2>Create a one-time invitation</h2>
                  <p>DevBareun stores only a hashed token. Copy the URL and send it through an approved channel.</p>
                </div>
              </div>
              <form className="team-invite-form" onSubmit={submitInvite}>
                <input type="email" required placeholder="person@company.com" value={invite.email} onChange={(event) => setInvite({ ...invite, email: event.target.value })} />
                <select value={invite.company_role} onChange={(event) => setInvite({ ...invite, company_role: event.target.value })}>
                  <option value="viewer">Viewer</option>
                  <option value="editor">Editor</option>
                  <option value="manager">Manager</option>
                </select>
                <select value={invite.expires_in_hours} onChange={(event) => setInvite({ ...invite, expires_in_hours: event.target.value })}>
                  <option value="24">24 hours</option>
                  <option value="72">72 hours</option>
                  <option value="168">7 days</option>
                </select>
                <button className="primary-button" type="submit" disabled={busy === "invite"}>{busy === "invite" ? "Creating..." : "Create invitation"}</button>
              </form>
              {inviteUrl ? (
                <div className="team-invite-url">
                  <code>{inviteUrl}</code>
                  <button className="secondary-button" type="button" onClick={copyInviteUrl}><Copy size={16} /> Copy URL</button>
                </div>
              ) : null}
            </section>
          ) : null}

          <section className="panel team-roster-panel">
            <div className="team-section-head">
              <div>
                <span className="workspace-eyebrow">Team roster</span>
                <h2>Company members</h2>
                <p>Membership alone does not expose projects, files, reports or analysis results.</p>
              </div>
              <UsersRound size={24} />
            </div>
            <div className="team-list">
              {members.map((member) => {
                const editable = canManage && member?.company_role !== "owner";
                const memberId = member?.membership_id;
                return (
                  <article className="team-member-row" key={memberId || member.member_email}>
                    <div>
                      <strong>{member.member_email}</strong>
                      <small>Joined {formatDate(member.joined_at)} - {readableStatus(member.status)}</small>
                    </div>
                    <div className="team-member-actions">
                      {editable ? (
                        <select value={member.company_role || "viewer"} disabled={busy === `member-${memberId}`} onChange={(event) => changeMember(member, { company_role: event.target.value })}>
                          <option value="manager">Manager</option>
                          <option value="editor">Editor</option>
                          <option value="viewer">Viewer</option>
                        </select>
                      ) : <span className="team-role-pill">{ROLE_LABELS[member.company_role] || member.company_role}</span>}
                      {editable ? (
                        <button className="secondary-button" type="button" disabled={busy === `member-${memberId}`} onClick={() => changeMember(member, { status: member.status === "active" ? "suspended" : "active" })}>
                          {member.status === "active" ? "Suspend" : "Activate"}
                        </button>
                      ) : null}
                    </div>
                  </article>
                );
              })}
            </div>
          </section>

          {canManage ? (
            <section className="panel team-pending-panel">
              <div className="team-section-head">
                <div>
                  <span className="workspace-eyebrow">Invitation record</span>
                  <h2>Pending and completed invitations</h2>
                </div>
              </div>
              <div className="team-list">
                {invitations.length ? invitations.map((item) => (
                  <article className="team-member-row" key={item.invitation_id}>
                    <div>
                      <strong>{item.invitee_email}</strong>
                      <small>{ROLE_LABELS[item.company_role] || item.company_role} - {readableStatus(item.status)} - Expires {formatDate(item.expires_at)}</small>
                    </div>
                    {item.status === "pending" ? (
                      <button className="secondary-button" type="button" disabled={busy === `revoke-${item.invitation_id}`} onClick={() => revokeInvitation(item.invitation_id)}>
                        {busy === `revoke-${item.invitation_id}` ? "Revoking..." : "Revoke"}
                      </button>
                    ) : null}
                  </article>
                )) : <p className="team-empty">No invitations created yet.</p>}
              </div>
            </section>
          ) : null}
        </>
      ) : null}
    </>
  );
}
