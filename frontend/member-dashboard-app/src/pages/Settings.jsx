import { useEffect, useMemo, useState } from "react";
import {
  Bell,
  Building2,
  CheckCircle2,
  ClipboardList,
  Database,
  Download,
  FileText,
  LockKeyhole,
  ShieldCheck,
  SlidersHorizontal,
  UserRound
} from "lucide-react";
import { PageHeader } from "../components/Shell";
import { workspaceApi } from "../api/client";
import { demoWorkspace } from "../data/demoWorkspace";

const ERASURE_CONFIRMATION = "ERASE MY DATA";
const SETTINGS_STORAGE_KEY = "devbareun.workspace.settings.v1";

const DEFAULT_SETTING_PREFERENCES = {
  uploadParserAlerts: true,
  riskDecisionReminders: true,
  weeklyExecutiveDigest: false,
  reportFormat: "PDF + Excel evidence package",
  reportLanguage: "English",
  dashboardScope: "Only data-backed dashboard sections",
  sourceLinks: false,
  paymentSecrets: false,
  automaticDeletion: false
};

function readStoredPreferences() {
  try {
    const stored = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (!stored) return DEFAULT_SETTING_PREFERENCES;
    return { ...DEFAULT_SETTING_PREFERENCES, ...JSON.parse(stored) };
  } catch {
    return DEFAULT_SETTING_PREFERENCES;
  }
}

function persistPreferences(preferences) {
  try {
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(preferences));
  } catch {
    // Local storage can be unavailable in strict browser modes; keep the in-memory state working.
  }
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? String(value) : date.toLocaleString();
}

function requestLabel(request) {
  const type = request?.request_type === "erasure" ? "Erasure" : "Data export";
  const scope = request?.scope === "project" ? "project" : "account";
  return `${type} - ${scope}`;
}

function statusTone(value) {
  const text = String(value || "").toLowerCase();
  if (["ok", "connected", "configured", "active", "verified"].some((item) => text.includes(item))) return "success";
  if (["missing", "unknown", "not_configured", "error", "failed"].some((item) => text.includes(item))) return "danger";
  return "warning";
}

function SettingStatCard({ label, value, note, icon: Icon, tone = "neutral", actionLabel, onAction, disabled = false }) {
  return (
    <article className={`settings-stat-card ${tone}`}>
      <div className="settings-stat-icon"><Icon size={18} /></div>
      <span>{label}</span>
      <strong>{value || "-"}</strong>
      {note ? <small>{note}</small> : null}
      {actionLabel ? (
        <button className="settings-card-action" type="button" onClick={onAction} disabled={disabled}>
          {actionLabel}
        </button>
      ) : null}
    </article>
  );
}

function SettingsToggleRow({ label, description, checked = false, onChange, disabled = false }) {
  return (
    <div className="settings-toggle-row">
      <div>
        <strong>{label}</strong>
        <span>{description}</span>
      </div>
      <label className={`settings-switch ${disabled ? "disabled" : ""}`} aria-label={label}>
        <input
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={(event) => onChange?.(event.target.checked)}
        />
        <i />
      </label>
    </div>
  );
}

function SettingsChecklist({ rows }) {
  return (
    <div className="settings-checklist">
      {rows.map((row) => (
        <article key={row.label}>
          <CheckCircle2 size={17} />
          <div>
            <strong>{row.label}</strong>
            <span>{row.description}</span>
          </div>
          {row.actionLabel ? (
            <button className="settings-mini-action" type="button" onClick={row.onAction}>
              {row.actionLabel}
            </button>
          ) : null}
        </article>
      ))}
    </div>
  );
}

function SettingsChoiceGroup({ label, value, options, onChange }) {
  return (
    <div className="settings-choice-row">
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <div className="settings-choice-options" role="group" aria-label={label}>
        {options.map((option) => (
          <button
            className={`settings-choice-button ${value === option ? "active" : ""}`}
            type="button"
            aria-pressed={value === option}
            key={option}
            onClick={() => onChange(option)}
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  );
}

export function Settings({ user, health, demoMode = false }) {
  const effectiveUser = demoMode ? demoWorkspace.user : user;
  const [localHealth, setLocalHealth] = useState(demoMode ? demoWorkspace.health : health);
  const [preferences, setPreferences] = useState(readStoredPreferences);
  const [settingsNotice, setSettingsNotice] = useState("");
  const [policy, setPolicy] = useState(null);
  const [requests, setRequests] = useState([]);
  const [loadingPrivacy, setLoadingPrivacy] = useState(true);
  const [privacyError, setPrivacyError] = useState("");
  const [privacyNotice, setPrivacyNotice] = useState("");
  const [busyAction, setBusyAction] = useState("");
  const [erasureConfirmation, setErasureConfirmation] = useState("");

  const activeRequests = useMemo(
    () => requests.filter((request) => ["submitted", "in_review", "approved"].includes(String(request?.status || "").toLowerCase())),
    [requests]
  );
  const displayHealth = localHealth || (demoMode ? demoWorkspace.health : health) || {};

  useEffect(() => {
    setLocalHealth(demoMode ? demoWorkspace.health : health);
  }, [demoMode, health]);

  function updatePreference(key, value, label) {
    setPreferences((current) => {
      const next = { ...current, [key]: value };
      persistPreferences(next);
      return next;
    });
    setSettingsNotice(`${label} saved locally for this browser.`);
  }

  function resetPreferences() {
    setPreferences(DEFAULT_SETTING_PREFERENCES);
    persistPreferences(DEFAULT_SETTING_PREFERENCES);
    setSettingsNotice("Workspace settings were reset to the recommended defaults.");
  }

  async function copySettingValue(label, value) {
    if (!value) {
      setSettingsNotice(`${label} is not available yet.`);
      return;
    }
    try {
      await navigator.clipboard.writeText(String(value));
      setSettingsNotice(`${label} copied to clipboard.`);
    } catch {
      setSettingsNotice(`${label}: ${value}`);
    }
  }

  async function refreshEnvironmentStatus() {
    if (demoMode) {
      setLocalHealth(demoWorkspace.health);
      setSettingsNotice("Preview readiness refreshed locally. No backend call was made.");
      return;
    }
    setSettingsNotice("Refreshing backend readiness...");
    try {
      const nextHealth = await workspaceApi.health();
      setLocalHealth(nextHealth);
      setSettingsNotice("Backend readiness refreshed.");
    } catch (error) {
      setSettingsNotice(error?.message || "Backend readiness could not be refreshed.");
    }
  }

  function scrollToPrivacy(label) {
    document.querySelector(".settings-privacy-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
    setSettingsNotice(label);
  }

  function focusPrivacyCard(selector, label) {
    document.querySelector(selector)?.scrollIntoView({ behavior: "smooth", block: "center" });
    setSettingsNotice(label);
  }

  async function refreshPrivacy() {
    if (demoMode) {
      setLoadingPrivacy(false);
      setPrivacyError("");
      setPrivacyNotice("Privacy lifecycle preview is local-only in demo mode.");
      return;
    }
    setLoadingPrivacy(true);
    setPrivacyError("");
    try {
      const [policyPayload, requestsPayload] = await Promise.all([
        workspaceApi.privacyPolicy(),
        workspaceApi.privacyRequests()
      ]);
      setPolicy(policyPayload?.policy || requestsPayload?.policy || null);
      setRequests(Array.isArray(requestsPayload?.requests) ? requestsPayload.requests : []);
    } catch (error) {
      setPrivacyError(error?.message || "Privacy request information could not be loaded.");
    } finally {
      setLoadingPrivacy(false);
    }
  }

  useEffect(() => {
    if (demoMode) {
      setLoadingPrivacy(false);
      setPolicy(null);
      setRequests([]);
      setPrivacyError("");
      return;
    }
    let mounted = true;
    (async () => {
      try {
        const [policyPayload, requestsPayload] = await Promise.all([
          workspaceApi.privacyPolicy(),
          workspaceApi.privacyRequests()
        ]);
        if (!mounted) return;
        setPolicy(policyPayload?.policy || requestsPayload?.policy || null);
        setRequests(Array.isArray(requestsPayload?.requests) ? requestsPayload.requests : []);
      } catch (error) {
        if (mounted) setPrivacyError(error?.message || "Privacy request information could not be loaded.");
      } finally {
        if (mounted) setLoadingPrivacy(false);
      }
    })();
    return () => { mounted = false; };
  }, [demoMode]);

  async function submitExport() {
    setBusyAction("export");
    setPrivacyError("");
    setPrivacyNotice("");
    try {
      const response = await workspaceApi.requestDataExport({ scope: "account" });
      setPrivacyNotice(response?.deduplicated ? "An active account export request already exists." : "Your account data export request was submitted for review.");
      await refreshPrivacy();
    } catch (error) {
      setPrivacyError(error?.message || "Data export request could not be submitted.");
    } finally {
      setBusyAction("");
    }
  }

  async function submitErasure() {
    if (erasureConfirmation.trim() !== ERASURE_CONFIRMATION) {
      setPrivacyError(`Type “${ERASURE_CONFIRMATION}” exactly to submit an erasure request.`);
      return;
    }
    const confirmed = window.confirm("Submit an account erasure request for owner review? This does not immediately delete data.");
    if (!confirmed) return;
    setBusyAction("erasure");
    setPrivacyError("");
    setPrivacyNotice("");
    try {
      const response = await workspaceApi.requestDataErasure({
        scope: "account",
        confirmation: erasureConfirmation.trim()
      });
      setPrivacyNotice(response?.deduplicated ? "An active account erasure request already exists." : "Your erasure request was submitted for owner review. No data was deleted automatically.");
      setErasureConfirmation("");
      await refreshPrivacy();
    } catch (error) {
      setPrivacyError(error?.message || "Erasure request could not be submitted.");
    } finally {
      setBusyAction("");
    }
  }

  async function cancelRequest(requestId) {
    if (!window.confirm("Cancel this pending privacy request?")) return;
    setBusyAction(requestId);
    setPrivacyError("");
    setPrivacyNotice("");
    try {
      await workspaceApi.cancelPrivacyRequest(requestId);
      setPrivacyNotice("Privacy request cancelled.");
      await refreshPrivacy();
    } catch (error) {
      setPrivacyError(error?.message || "Privacy request could not be cancelled.");
    } finally {
      setBusyAction("");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow={demoMode ? "Workspace settings preview" : "Workspace settings"}
        title="Workspace control center."
        description={demoMode ? "Preview account identity, readiness and reporting preferences with local sample workspace data." : "Manage account identity, service readiness, reporting preferences and reviewed data lifecycle requests."}
      />

      <section className="settings-command-panel panel featured">
        <div>
          <span className={`status-pill ${statusTone(displayHealth?.status)}`}>{displayHealth?.status || "Unknown"}</span>
          <h2>Account and environment readiness</h2>
          <p>{demoMode ? "This preview keeps the same safety framing while staying local to the browser. No private key, customer record or lifecycle request is sent." : "Keep the workspace safe for customer uploads, report exports and team collaboration. Private keys stay on the backend; this screen only shows user-safe status."}</p>
          <div className="settings-card-actions">
            <button className="secondary-button" type="button" onClick={refreshEnvironmentStatus}>
              Refresh readiness
            </button>
            <button className="secondary-button" type="button" onClick={resetPreferences}>
              Reset preferences
            </button>
          </div>
        </div>
        <aside>
          <span>Signed-in account</span>
          <strong>{effectiveUser?.email || "No active session"}</strong>
          <p>{effectiveUser?.company_name || effectiveUser?.company || "Company profile not returned"} - {effectiveUser?.plan || "Plan not returned"}</p>
        </aside>
      </section>

      {settingsNotice ? <div className="status-box success settings-live-notice">{settingsNotice}</div> : null}

      <section className="settings-stat-grid">
        <SettingStatCard
          label="Account"
          value={effectiveUser?.email || "No session"}
          note={effectiveUser?.name || "Supabase session required"}
          icon={UserRound}
          tone={effectiveUser?.email ? "success" : "warning"}
          actionLabel="Copy email"
          onAction={() => copySettingValue("Account email", effectiveUser?.email)}
          disabled={!effectiveUser?.email}
        />
        <SettingStatCard
          label="Company"
          value={effectiveUser?.company_name || effectiveUser?.company || "Not returned"}
          note={`Plan: ${effectiveUser?.plan || "not returned"}`}
          icon={Building2}
          tone={effectiveUser?.company_name || effectiveUser?.company ? "success" : "warning"}
          actionLabel="Copy company"
          onAction={() => copySettingValue("Company name", effectiveUser?.company_name || effectiveUser?.company)}
          disabled={!(effectiveUser?.company_name || effectiveUser?.company)}
        />
        <SettingStatCard
          label="Database"
          value={displayHealth?.database || "Unknown"}
          note="Backend owned connection"
          icon={Database}
          tone={statusTone(displayHealth?.database)}
          actionLabel="Refresh"
          onAction={refreshEnvironmentStatus}
        />
        <SettingStatCard
          label="Storage"
          value={displayHealth?.storage || "Unknown"}
          note="Upload evidence storage"
          icon={FileText}
          tone={statusTone(displayHealth?.storage)}
          actionLabel="Refresh"
          onAction={refreshEnvironmentStatus}
        />
      </section>

      <section className="settings-control-grid">
        <article className="panel settings-control-card">
          <div className="settings-section-head">
            <div>
              <span className="workspace-eyebrow">Security posture</span>
              <h2>Access and session guardrails</h2>
            </div>
            <ShieldCheck size={22} />
          </div>
          <SettingsChecklist rows={[
            {
              label: "Protected workspace",
              description: effectiveUser?.email ? "Session identity is available in this view." : "No active session identity was returned.",
              actionLabel: "Copy account",
              onAction: () => copySettingValue("Account email", effectiveUser?.email)
            },
            {
              label: "Private keys stay server-side",
              description: "Service role, payment and storage secrets are not exposed in the browser.",
              actionLabel: "Acknowledge",
              onAction: () => setSettingsNotice("Secret exposure guardrail acknowledged.")
            },
            {
              label: "Reviewed privacy actions",
              description: "Export and erasure requests are submitted for review before execution.",
              actionLabel: "Open lifecycle",
              onAction: () => scrollToPrivacy("Data lifecycle controls opened.")
            }
          ]} />
        </article>

        <article className="panel settings-control-card">
          <div className="settings-section-head">
            <div>
              <span className="workspace-eyebrow">Notifications</span>
              <h2>Workspace alerts</h2>
            </div>
            <Bell size={22} />
          </div>
          <SettingsToggleRow
            label="Upload and parser alerts"
            description="Show status changes for file screening and dashboard generation."
            checked={preferences.uploadParserAlerts}
            onChange={(checked) => updatePreference("uploadParserAlerts", checked, "Upload and parser alerts")}
          />
          <SettingsToggleRow
            label="Risk decision reminders"
            description="Highlight overdue owner decisions in the workspace topbar."
            checked={preferences.riskDecisionReminders}
            onChange={(checked) => updatePreference("riskDecisionReminders", checked, "Risk decision reminders")}
          />
          <SettingsToggleRow
            label="Weekly executive digest"
            description="Saved as a workspace preference; no email is sent until the notification endpoint is connected."
            checked={preferences.weeklyExecutiveDigest}
            onChange={(checked) => updatePreference("weeklyExecutiveDigest", checked, "Weekly executive digest")}
          />
        </article>

        <article className="panel settings-control-card">
          <div className="settings-section-head">
            <div>
              <span className="workspace-eyebrow">Report defaults</span>
              <h2>Export behavior</h2>
            </div>
            <SlidersHorizontal size={22} />
          </div>
          <div className="settings-default-list settings-choice-list">
            <SettingsChoiceGroup
              label="Primary format"
              value={preferences.reportFormat}
              options={["PDF + Excel evidence package", "PDF only", "Excel only"]}
              onChange={(value) => updatePreference("reportFormat", value, "Primary report format")}
            />
            <SettingsChoiceGroup
              label="Default language"
              value={preferences.reportLanguage}
              options={["English", "Azerbaijani"]}
              onChange={(value) => updatePreference("reportLanguage", value, "Default report language")}
            />
            <SettingsChoiceGroup
              label="Management scope"
              value={preferences.dashboardScope}
              options={["Only data-backed dashboard sections", "Executive summary first", "Full trace view"]}
              onChange={(value) => updatePreference("dashboardScope", value, "Management scope")}
            />
            <small className="settings-preference-note">Saved locally in this browser until a backend preference endpoint is connected.</small>
          </div>
        </article>

        <article className="panel settings-control-card">
          <div className="settings-section-head">
            <div>
              <span className="workspace-eyebrow">Data boundaries</span>
              <h2>What this page does not expose</h2>
            </div>
            <LockKeyhole size={22} />
          </div>
          <SettingsChecklist rows={[
            {
              label: "No direct storage links",
              description: "Source file provenance is shown without private storage URLs.",
              actionLabel: "Copy policy",
              onAction: () => copySettingValue("Storage boundary", "Source file provenance is shown without private storage URLs.")
            },
            {
              label: "No payment secrets",
              description: "Checkout and webhook secrets remain backend-only.",
              actionLabel: "Acknowledge",
              onAction: () => setSettingsNotice("Payment secret boundary acknowledged.")
            },
            {
              label: "No automatic deletion",
              description: "Erasure requests require review and grace period handling.",
              actionLabel: "Open erasure",
              onAction: () => scrollToPrivacy("Erasure request controls opened.")
            }
          ]} />
        </article>
      </section>

      <section className="panel settings-privacy-panel">
        <div className="settings-privacy-header">
          <div>
            <span className="result-eyebrow">Data lifecycle</span>
            <h2>Export or request erasure</h2>
            <p>{demoMode ? "This lifecycle area stays visible in preview mode, but export and erasure actions remain local-only." : "Requests are reviewed before execution. This workflow does not automatically remove invoices, immutable audit records, encrypted backups or your authentication identity."}</p>
          </div>
          <button className="secondary-button" type="button" onClick={refreshPrivacy} disabled={loadingPrivacy || Boolean(busyAction)}>
            {loadingPrivacy ? "Refreshing..." : "Refresh"}
          </button>
        </div>
        {demoMode ? <div className="status-box info">Preview only: export and erasure requests are not submitted from demo mode.</div> : null}

        <section className="settings-lifecycle-summary">
          <article>
            <Download size={18} />
            <button className="settings-mini-action" type="button" aria-label="Open account data export card" onClick={() => focusPrivacyCard("[data-settings-card='export']", "Account data export card focused.")}>
              Open
            </button>
            <div><span>Export target</span><strong>{policy?.export_request_ttl_days ?? "-"} days</strong></div>
          </article>
          <article>
            <ClipboardList size={18} />
            <button className="settings-mini-action" type="button" aria-label="Refresh privacy requests" onClick={refreshPrivacy} disabled={loadingPrivacy || Boolean(busyAction)}>
              Refresh
            </button>
            <div><span>Active requests</span><strong>{activeRequests.length}</strong></div>
          </article>
          <article>
            <LockKeyhole size={18} />
            <button className="settings-mini-action" type="button" aria-label="Open account erasure card" onClick={() => focusPrivacyCard("[data-settings-card='erasure']", "Account erasure card focused.")}>
              Open
            </button>
            <div><span>Erasure grace</span><strong>{policy?.erasure_grace_days ?? "-"} days</strong></div>
          </article>
        </section>

        {privacyError ? <div className="status-box error">{privacyError}</div> : null}
        {privacyNotice ? <div className="status-box success">{privacyNotice}</div> : null}

        <div className="settings-privacy-grid">
          <article className="settings-privacy-card" data-settings-card="export">
            <h3>Account data export</h3>
            <p>Request an export of the account-level information available through this workspace.</p>
            <button className="secondary-button" type="button" onClick={submitExport} disabled={Boolean(busyAction) || loadingPrivacy}>
              {busyAction === "export" ? "Submitting..." : "Request export"}
            </button>
          </article>
          <article className="settings-privacy-card danger-zone" data-settings-card="erasure">
            <h3>Account erasure request</h3>
            <p>Type <code>{ERASURE_CONFIRMATION}</code> exactly. The request is reviewed; no data is deleted immediately.</p>
            <input
              aria-label="Erasure confirmation"
              value={erasureConfirmation}
              onChange={(event) => setErasureConfirmation(event.target.value)}
              placeholder={ERASURE_CONFIRMATION}
              autoComplete="off"
            />
            <button className="secondary-button" type="button" onClick={submitErasure} disabled={Boolean(busyAction) || loadingPrivacy}>
              {busyAction === "erasure" ? "Submitting..." : "Submit erasure request"}
            </button>
          </article>
        </div>

        <div className="settings-privacy-requests">
          <div>
            <h3>Request status</h3>
            <p>{loadingPrivacy ? "Loading reviewed requests..." : activeRequests.length ? `${activeRequests.length} active request${activeRequests.length === 1 ? "" : "s"}.` : "No active privacy requests."}</p>
          </div>
          <div className="settings-privacy-list">
            {requests.length ? requests.map((request) => {
              const status = String(request?.status || "submitted").replace(/_/g, " ");
              const cancellable = ["submitted", "in_review", "approved"].includes(String(request?.status || "").toLowerCase());
              const requestId = request?.lifecycle_request_id || request?.id;
              return (
                <article className="settings-privacy-request" key={requestId || `${requestLabel(request)}-${request?.requested_at || ""}`}>
                  <div>
                    <strong>{requestLabel(request)}</strong>
                    <small>Submitted {formatDate(request?.requested_at || request?.created_at)} - Status: {status}</small>
                    {request?.scheduled_purge_at ? <small>Purge window: {formatDate(request.scheduled_purge_at)}</small> : null}
                  </div>
                  {cancellable && requestId ? (
                    <button className="secondary-button" type="button" onClick={() => cancelRequest(requestId)} disabled={Boolean(busyAction)}>
                      {busyAction === requestId ? "Cancelling..." : "Cancel"}
                    </button>
                  ) : null}
                </article>
              );
            }) : <p className="settings-privacy-empty">No requests have been submitted.</p>}
          </div>
        </div>

        <small className="settings-privacy-policy">
          Soft-delete retention: {policy?.soft_delete_retention_days ?? "-"} days - Erasure review grace period: {policy?.erasure_grace_days ?? "-"} days - Export request target: {policy?.export_request_ttl_days ?? "-"} days.
        </small>
      </section>
    </>
  );
}
