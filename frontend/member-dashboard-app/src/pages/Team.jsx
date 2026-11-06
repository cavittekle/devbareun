import { useEffect, useMemo, useState } from "react";
import { Copy, RefreshCw, UsersRound } from "lucide-react";
import { EmptyState, PageHeader } from "../components/Shell";
import { workspaceApi } from "../api/client";
import { useT } from "../lib/i18n";

const ROLE_LABELS = {
  owner: ["Owner", "Sahib"],
  manager: ["Manager", "Menecer"],
  editor: ["Editor", "Redaktor"],
  viewer: ["Viewer", "İzləyici"]
};

export function roleLabel(role, t) {
  const pair = ROLE_LABELS[role];
  return pair ? t(pair[0], pair[1]) : role || "—";
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? String(value) : date.toLocaleString();
}

function readableStatus(value) {
  return String(value || "pending").replace(/_/g, " ");
}

export function Team() {
  const t = useT();
  const inviteToken = new URLSearchParams(location.search).get("invite") || "";
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
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
    setLoading(true);
    setError("");
    try {
      const next = await workspaceApi.companyWorkspace();
      setPayload(next || null);
    } catch (requestError) {
      setError(requestError?.message || t("We couldn't load your company workspace. Try Refresh in a minute.", "Şirkət iş sahəsini yükləmək olmadı. Bir dəqiqə sonra Yenilə düyməsini basın."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function createWorkspace(event) {
    event.preventDefault();
    if (!companyName.trim()) return;
    setBusy("workspace");
    setError("");
    setNotice("");
    try {
      const next = await workspaceApi.createCompanyWorkspace({ company_name: companyName.trim() });
      setPayload(next || null);
      setNotice(next?.created ? t("Company workspace created.", "Şirkət iş sahəsi yaradıldı.") : t("Your existing company workspace is open.", "Mövcud şirkət iş sahəniz açıldı."));
      setCompanyName("");
    } catch (requestError) {
      setError(requestError?.message || t("The company workspace wasn't created. Try again in a minute.", "Şirkət iş sahəsi yaradılmadı. Bir dəqiqə sonra yenidən cəhd edin."));
    } finally {
      setBusy("");
    }
  }

  async function acceptInvite() {
    if (!inviteToken) return;
    setBusy("accept-invite");
    setError("");
    setNotice("");
    try {
      const next = await workspaceApi.acceptCompanyInvitation({ token: inviteToken });
      setPayload(next || null);
      setNotice(t("Invitation accepted. You are now a member of this company.", "Dəvət qəbul edildi. Artıq bu şirkətin üzvüsünüz."));
      const current = new URL(location.href);
      current.searchParams.delete("invite");
      history.replaceState(null, "", current.toString());
    } catch (requestError) {
      setError(requestError?.message || t("The invitation wasn't accepted. Check that you signed in with the invited email.", "Dəvət qəbul edilmədi. Dəvət göndərilən email ilə daxil olduğunuzu yoxlayın."));
    } finally {
      setBusy("");
    }
  }

  async function submitInvite(event) {
    event.preventDefault();
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
      setNotice(response?.notice || t("Invitation created. Copy the link below and send it to your colleague.", "Dəvət yaradıldı. Aşağıdakı keçidi kopyalayıb həmkarınıza göndərin."));
      setInvite({ email: "", company_role: "viewer", expires_in_hours: 72 });
      await refresh();
    } catch (requestError) {
      setError(requestError?.message || t("The invitation wasn't created. Try again in a minute.", "Dəvət yaradılmadı. Bir dəqiqə sonra yenidən cəhd edin."));
    } finally {
      setBusy("");
    }
  }

  async function copyInviteUrl() {
    if (!inviteUrl) return;
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setNotice(t("Link copied. It is shown only once, so send it now.", "Keçid kopyalandı. O yalnız bir dəfə göstərilir, indi göndərin."));
    } catch {
      setError(t("Couldn't copy. Select the link and copy it manually.", "Kopyalamaq olmadı. Keçidi seçib əl ilə kopyalayın."));
    }
  }

  async function revokeInvitation(invitationId) {
    if (!window.confirm(t("Cancel this invitation? The link will stop working.", "Bu dəvət ləğv edilsin? Keçid işləməyəcək."))) return;
    setBusy(`revoke-${invitationId}`);
    setError("");
    try {
      await workspaceApi.revokeCompanyInvitation(invitationId);
      setNotice(t("Invitation cancelled.", "Dəvət ləğv edildi."));
      await refresh();
    } catch (requestError) {
      setError(requestError?.message || t("The invitation wasn't cancelled. Try again in a minute.", "Dəvət ləğv edilmədi. Bir dəqiqə sonra yenidən cəhd edin."));
    } finally {
      setBusy("");
    }
  }

  async function changeMember(member, patch) {
    const memberId = member?.membership_id;
    if (!memberId) return;
    setBusy(`member-${memberId}`);
    setError("");
    try {
      await workspaceApi.updateCompanyMember(memberId, patch);
      setNotice(t("Member updated.", "Üzv yeniləndi."));
      await refresh();
    } catch (requestError) {
      setError(requestError?.message || t("The member wasn't updated. Try again in a minute.", "Üzv yenilənmədi. Bir dəqiqə sonra yenidən cəhd edin."));
    } finally {
      setBusy("");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow={t("Team", "Komanda")}
        title={t("Team and invitations", "Komanda və dəvətlər")}
        description={t("Invite colleagues to your company. Joining the company does not open any project; you share each project separately.", "Həmkarlarınızı şirkətə dəvət edin. Şirkətə qoşulmaq heç bir layihəni açmır, hər layihəni ayrıca paylaşırsınız.")}
        action={
          <button className="secondary-button" type="button" onClick={refresh} disabled={loading || Boolean(busy)}>
            <RefreshCw size={16} aria-hidden="true" /> {loading ? t("Refreshing…", "Yenilənir…") : t("Refresh", "Yenilə")}
          </button>
        }
      />

      {error ? <div className="status-box error" role="alert">{error}</div> : null}
      {notice ? <div className="status-box success" role="status">{notice}</div> : null}

      {inviteToken ? (
        <section className="panel team-invite-accept">
          <div>
            <span className="workspace-eyebrow">{t("Invitation", "Dəvət")}</span>
            <h2>{t("Join a company workspace", "Şirkət iş sahəsinə qoşulun")}</h2>
            <p>{t("Sign in with the email address that received the invitation, then accept it.", "Dəvət göndərilən email ilə daxil olun, sonra dəvəti qəbul edin.")}</p>
          </div>
          <button className="primary-button" type="button" disabled={busy === "accept-invite"} onClick={acceptInvite}>
            {busy === "accept-invite" ? t("Accepting…", "Qəbul edilir…") : t("Accept invitation", "Dəvəti qəbul et")}
          </button>
        </section>
      ) : null}

      {loading ? <div className="status-box info" role="status">{t("Loading your team…", "Komanda yüklənir…")}</div> : null}

      {!loading && !workspace ? (
        <section className="team-bootstrap-grid">
          <EmptyState
            title={t("Create your company workspace", "Şirkət iş sahənizi yaradın")}
            description={t("Keep your team and invitations in one list. Projects are not shared automatically.", "Komandanızı və dəvətləri bir siyahıda saxlayın. Layihələr avtomatik paylaşılmır.")}
          />
          <form className="panel team-bootstrap-form" onSubmit={createWorkspace}>
            <span className="workspace-eyebrow">{t("Setup", "Quraşdırma")}</span>
            <h2><label htmlFor="team-company-name">{t("Company name", "Şirkətin adı")}</label></h2>
            <p id="team-company-name-help">{t("Use the name your team knows the company by.", "Komandanızın tanıdığı şirkət adını yazın.")}</p>
            <input id="team-company-name" aria-describedby="team-company-name-help" value={companyName} onChange={(event) => setCompanyName(event.target.value)} required minLength={2} maxLength={180} placeholder={t("Company name", "Şirkətin adı")} />
            <button className="primary-button" type="submit" disabled={busy === "workspace"}>
              {busy === "workspace" ? t("Creating…", "Yaradılır…") : t("Create company workspace", "Şirkət iş sahəsini yarat")}
            </button>
          </form>
        </section>
      ) : null}

      {!loading && workspace ? (
        <>
          <section className="team-overview-grid">
            <article className="panel">
              <span className="workspace-eyebrow">{t("Company", "Şirkət")}</span>
              <h2>{workspace.company_name || t("Company workspace", "Şirkət iş sahəsi")}</h2>
              <p>{t("Plan", "Plan")}: {workspace.plan || t("free", "pulsuz")}</p>
            </article>
            <article className="panel">
              <span className="workspace-eyebrow">{t("Your role", "Rolunuz")}</span>
              <h2>{roleLabel(membership?.company_role, t)}</h2>
              <p>{t("Status", "Vəziyyət")}: {readableStatus(membership?.status)}</p>
            </article>
            <article className="panel">
              <span className="workspace-eyebrow">{t("Active members", "Aktiv üzvlər")}</span>
              <h2>{activeMembers.length}</h2>
              <p>{canManage ? t("You can invite and manage members.", "Üzvləri dəvət edə və idarə edə bilərsiniz.") : t("You can view the member list.", "Üzv siyahısına baxa bilərsiniz.")}</p>
            </article>
          </section>

          {canManage ? (
            <section className="panel team-invite-panel">
              <div className="team-section-head">
                <div>
                  <span className="workspace-eyebrow">{t("Invite", "Dəvət")}</span>
                  <h2>{t("Invite a colleague", "Həmkarınızı dəvət edin")}</h2>
                  <p>{t("You get a one-time link to send. It works once and expires after the time you choose.", "Göndərmək üçün birdəfəlik keçid alırsınız. O bir dəfə işləyir və seçdiyiniz müddətdən sonra etibarsız olur.")}</p>
                </div>
              </div>
              <form className="team-invite-form" onSubmit={submitInvite}>
                <input type="email" required aria-label={t("Colleague's email", "Həmkarın emaili")} autoComplete="off" placeholder="person@company.com" value={invite.email} onChange={(event) => setInvite({ ...invite, email: event.target.value })} />
                <select aria-label={t("Role", "Rol")} value={invite.company_role} onChange={(event) => setInvite({ ...invite, company_role: event.target.value })}>
                  <option value="viewer">{roleLabel("viewer", t)}</option>
                  <option value="editor">{roleLabel("editor", t)}</option>
                  <option value="manager">{roleLabel("manager", t)}</option>
                </select>
                <select aria-label={t("Link expires after", "Keçidin etibarlılıq müddəti")} value={invite.expires_in_hours} onChange={(event) => setInvite({ ...invite, expires_in_hours: event.target.value })}>
                  <option value="24">{t("24 hours", "24 saat")}</option>
                  <option value="72">{t("72 hours", "72 saat")}</option>
                  <option value="168">{t("7 days", "7 gün")}</option>
                </select>
                <button className="primary-button" type="submit" disabled={busy === "invite"}>{busy === "invite" ? t("Creating…", "Yaradılır…") : t("Create invitation link", "Dəvət keçidi yarat")}</button>
              </form>
              {inviteUrl ? (
                <div className="team-invite-url">
                  <code>{inviteUrl}</code>
                  <button className="secondary-button" type="button" onClick={copyInviteUrl}><Copy size={16} aria-hidden="true" /> {t("Copy link", "Keçidi kopyala")}</button>
                </div>
              ) : null}
            </section>
          ) : null}

          <section className="panel team-roster-panel">
            <div className="team-section-head">
              <div>
                <span className="workspace-eyebrow">{t("Members", "Üzvlər")}</span>
                <h2>{t("Company members", "Şirkət üzvləri")}</h2>
                <p>{t("Members see a project, its files and reports only after you share that project.", "Üzvlər layihəni, onun fayllarını və hesabatlarını yalnız siz paylaşdıqdan sonra görür.")}</p>
              </div>
              <UsersRound size={24} aria-hidden="true" />
            </div>
            <div className="team-list">
              {members.map((member) => {
                const editable = canManage && member?.company_role !== "owner";
                const memberId = member?.membership_id;
                return (
                  <article className="team-member-row" key={memberId || member.member_email}>
                    <div>
                      <strong>{member.member_email}</strong>
                      <small>{t("Joined", "Qoşulub")} {formatDate(member.joined_at)} · {readableStatus(member.status)}</small>
                    </div>
                    <div className="team-member-actions">
                      {editable ? (
                        <select aria-label={`${t("Role", "Rol")}: ${member.member_email}`} value={member.company_role || "viewer"} disabled={busy === `member-${memberId}`} onChange={(event) => changeMember(member, { company_role: event.target.value })}>
                          <option value="manager">{roleLabel("manager", t)}</option>
                          <option value="editor">{roleLabel("editor", t)}</option>
                          <option value="viewer">{roleLabel("viewer", t)}</option>
                        </select>
                      ) : <span className="team-role-pill">{roleLabel(member.company_role, t)}</span>}
                      {editable ? (
                        <button className="secondary-button" type="button" disabled={busy === `member-${memberId}`} onClick={() => changeMember(member, { status: member.status === "active" ? "suspended" : "active" })}>
                          {member.status === "active" ? t("Suspend", "Dayandır") : t("Activate", "Aktivləşdir")}
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
                  <span className="workspace-eyebrow">{t("Invitations", "Dəvətlər")}</span>
                  <h2>{t("Sent invitations", "Göndərilmiş dəvətlər")}</h2>
                </div>
              </div>
              <div className="team-list">
                {invitations.length ? invitations.map((item) => (
                  <article className="team-member-row" key={item.invitation_id}>
                    <div>
                      <strong>{item.invitee_email}</strong>
                      <small>{roleLabel(item.company_role, t)} · {readableStatus(item.status)} · {t("Expires", "Bitir")} {formatDate(item.expires_at)}</small>
                    </div>
                    {item.status === "pending" ? (
                      <button className="secondary-button" type="button" disabled={busy === `revoke-${item.invitation_id}`} onClick={() => revokeInvitation(item.invitation_id)}>
                        {busy === `revoke-${item.invitation_id}` ? t("Cancelling…", "Ləğv edilir…") : t("Cancel invitation", "Dəvəti ləğv et")}
                      </button>
                    ) : null}
                  </article>
                )) : <p className="team-empty">{t("No invitations sent yet.", "Hələ dəvət göndərilməyib.")}</p>}
              </div>
            </section>
          ) : null}
        </>
      ) : null}
    </>
  );
}
