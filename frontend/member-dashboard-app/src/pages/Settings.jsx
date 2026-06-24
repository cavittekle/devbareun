import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "../components/Shell";
import { workspaceApi } from "../api/client";

const ERASURE_CONFIRMATION = "ERASE MY DATA";

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? String(value) : date.toLocaleString();
}

function requestLabel(request) {
  const type = request?.request_type === "erasure" ? "Erasure" : "Data export";
  const scope = request?.scope === "project" ? "project" : "account";
  return `${type} · ${scope}`;
}

export function Settings({ user, health }) {
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

  async function refreshPrivacy() {
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
  }, []);

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
        eyebrow="Workspace settings"
        title="Account, privacy and production readiness."
        description="Manage your session information, view service health and submit reviewed data lifecycle requests."
      />
      <section className="card-grid">
        <article className="panel">
          <h2>Account</h2>
          <p>{user?.email || "No active session detected."}</p>
          <small>Production login should be backed by Supabase Auth and HTTP-only cookies.</small>
        </article>
        <article className="panel">
          <h2>Backend health</h2>
          <p>{health?.status || "Unknown"}</p>
          <small>Database: {health?.database || "unknown"} · Storage: {health?.storage || "unknown"}</small>
        </article>
      </section>

      <section className="panel settings-privacy-panel">
        <div className="settings-privacy-header">
          <div>
            <span className="result-eyebrow">Data lifecycle</span>
            <h2>Export or request erasure</h2>
            <p>Requests are reviewed before execution. This workflow does not automatically remove invoices, immutable audit records, encrypted backups or your authentication identity.</p>
          </div>
          <button className="secondary-button" type="button" onClick={refreshPrivacy} disabled={loadingPrivacy || Boolean(busyAction)}>
            {loadingPrivacy ? "Refreshing…" : "Refresh"}
          </button>
        </div>

        {privacyError ? <div className="status-box error">{privacyError}</div> : null}
        {privacyNotice ? <div className="status-box success">{privacyNotice}</div> : null}

        <div className="settings-privacy-grid">
          <article className="settings-privacy-card">
            <h3>Account data export</h3>
            <p>Request an export of the account-level information available through this workspace.</p>
            <button className="secondary-button" type="button" onClick={submitExport} disabled={Boolean(busyAction) || loadingPrivacy}>
              {busyAction === "export" ? "Submitting…" : "Request export"}
            </button>
          </article>
          <article className="settings-privacy-card danger-zone">
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
              {busyAction === "erasure" ? "Submitting…" : "Submit erasure request"}
            </button>
          </article>
        </div>

        <div className="settings-privacy-requests">
          <div>
            <h3>Request status</h3>
            <p>{loadingPrivacy ? "Loading reviewed requests…" : activeRequests.length ? `${activeRequests.length} active request${activeRequests.length === 1 ? "" : "s"}.` : "No active privacy requests."}</p>
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
                    <small>Submitted {formatDate(request?.requested_at || request?.created_at)} · Status: {status}</small>
                    {request?.scheduled_purge_at ? <small>Purge window: {formatDate(request.scheduled_purge_at)}</small> : null}
                  </div>
                  {cancellable && requestId ? (
                    <button className="secondary-button" type="button" onClick={() => cancelRequest(requestId)} disabled={Boolean(busyAction)}>
                      {busyAction === requestId ? "Cancelling…" : "Cancel"}
                    </button>
                  ) : null}
                </article>
              );
            }) : <p className="settings-privacy-empty">No requests have been submitted.</p>}
          </div>
        </div>

        <small className="settings-privacy-policy">
          Soft-delete retention: {policy?.soft_delete_retention_days ?? "—"} days · Erasure review grace period: {policy?.erasure_grace_days ?? "—"} days · Export request target: {policy?.export_request_ttl_days ?? "—"} days.
        </small>
      </section>
    </>
  );
}
