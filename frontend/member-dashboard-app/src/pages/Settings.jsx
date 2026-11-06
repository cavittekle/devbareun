import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "../components/Shell";
import { workspaceApi } from "../api/client";
import { useT } from "../lib/i18n";

const ERASURE_CONFIRMATION = "ERASE MY DATA";

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? String(value) : date.toLocaleString();
}

function requestLabel(request, t) {
  const type = request?.request_type === "erasure" ? t("Erasure", "Silinmə") : t("Data export", "Məlumat ixracı");
  const scope = request?.scope === "project" ? t("project", "layihə") : t("account", "hesab");
  return `${type} · ${scope}`;
}

export function Settings({ user, health }) {
  const t = useT();
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
      setPrivacyError(error?.message || t("We couldn't load your privacy requests. Try Refresh in a minute.", "Məxfilik sorğularınızı yükləmək olmadı. Bir dəqiqə sonra Yenilə düyməsini basın."));
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
        if (mounted) setPrivacyError(error?.message || t("We couldn't load your privacy requests. Try Refresh in a minute.", "Məxfilik sorğularınızı yükləmək olmadı. Bir dəqiqə sonra Yenilə düyməsini basın."));
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
      setPrivacyNotice(response?.deduplicated ? t("You already have an open export request.", "Artıq açıq ixrac sorğunuz var.") : t("Export request sent for review. You can follow its status below.", "İxrac sorğusu yoxlanmaya göndərildi. Vəziyyətini aşağıda izləyə bilərsiniz."));
      await refreshPrivacy();
    } catch (error) {
      setPrivacyError(error?.message || t("The export request wasn't sent. Try again in a minute.", "İxrac sorğusu göndərilmədi. Bir dəqiqə sonra yenidən cəhd edin."));
    } finally {
      setBusyAction("");
    }
  }

  async function submitErasure() {
    if (erasureConfirmation.trim() !== ERASURE_CONFIRMATION) {
      setPrivacyError(t(`Type ${ERASURE_CONFIRMATION} exactly as shown to send the request.`, `Sorğunu göndərmək üçün ${ERASURE_CONFIRMATION} ifadəsini olduğu kimi yazın.`));
      return;
    }
    const confirmed = window.confirm(t("Send an account erasure request? We review it before anything is deleted.", "Hesabın silinməsi sorğusu göndərilsin? Heç nə silinməzdən əvvəl sorğunu yoxlayırıq."));
    if (!confirmed) return;
    setBusyAction("erasure");
    setPrivacyError("");
    setPrivacyNotice("");
    try {
      const response = await workspaceApi.requestDataErasure({
        scope: "account",
        confirmation: erasureConfirmation.trim()
      });
      setPrivacyNotice(response?.deduplicated ? t("You already have an open erasure request.", "Artıq açıq silinmə sorğunuz var.") : t("Erasure request sent for review. No data was deleted automatically.", "Silinmə sorğusu yoxlamaya göndərildi. Heç bir məlumat avtomatik silinmədi."));
      setErasureConfirmation("");
      await refreshPrivacy();
    } catch (error) {
      setPrivacyError(error?.message || t("The erasure request wasn't sent. Try again in a minute.", "Silinmə sorğusu göndərilmədi. Bir dəqiqə sonra yenidən cəhd edin."));
    } finally {
      setBusyAction("");
    }
  }

  async function cancelRequest(requestId) {
    if (!window.confirm(t("Cancel this request?", "Bu sorğu ləğv edilsin?"))) return;
    setBusyAction(requestId);
    setPrivacyError("");
    setPrivacyNotice("");
    try {
      await workspaceApi.cancelPrivacyRequest(requestId);
      setPrivacyNotice(t("Request cancelled.", "Sorğu ləğv edildi."));
      await refreshPrivacy();
    } catch (error) {
      setPrivacyError(error?.message || t("The request wasn't cancelled. Try again in a minute.", "Sorğu ləğv edilmədi. Bir dəqiqə sonra yenidən cəhd edin."));
    } finally {
      setBusyAction("");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow={t("Settings", "Ayarlar")}
        title={t("Account and privacy", "Hesab və məxfilik")}
        description={t("See your account, check the service status and ask for a copy or deletion of your data.", "Hesabınıza baxın, xidmətin vəziyyətini yoxlayın və məlumatlarınızın surətini və ya silinməsini istəyin.")}
      />
      <section className="card-grid">
        <article className="panel">
          <h2>{t("Account", "Hesab")}</h2>
          <p>{user?.email || t("You're not signed in.", "Daxil olmamısınız.")}</p>
          <small>{t("Signed in with email and password.", "Email və şifrə ilə daxil olunub.")}</small>
        </article>
        <article className="panel">
          <h2>{t("Service status", "Xidmətin vəziyyəti")}</h2>
          <p>{health?.status || t("Unknown", "Naməlum")}</p>
          <small>{t("Database", "Verilənlər bazası")}: {health?.database || t("unknown", "naməlum")} · {t("File storage", "Fayl yaddaşı")}: {health?.storage || t("unknown", "naməlum")}</small>
        </article>
      </section>

      {/* Data lifecycle: guarded export and erasure requests, reviewed before anything runs. */}
      <section className="panel settings-privacy-panel">
        <div className="settings-privacy-header">
          <div>
            <span className="result-eyebrow">{t("Your data", "Məlumatlarınız")}</span>
            <h2>{t("Export or delete your data", "Məlumatlarınızı ixrac edin və ya silin")}</h2>
            <p>{t("We review every request before acting on it. Invoices, audit records, encrypted backups and your sign-in account are kept as the law and security require.", "Hər sorğunu icra etməzdən əvvəl yoxlayırıq. Fakturalar, audit qeydləri, şifrəli ehtiyat nüsxələr və giriş hesabınız qanun və təhlükəsizlik tələblərinə uyğun saxlanılır.")}</p>
          </div>
          <button className="secondary-button" type="button" onClick={refreshPrivacy} disabled={loadingPrivacy || Boolean(busyAction)}>
            {loadingPrivacy ? t("Refreshing…", "Yenilənir…") : t("Refresh", "Yenilə")}
          </button>
        </div>

        {privacyError ? <div className="status-box error" role="alert">{privacyError}</div> : null}
        {privacyNotice ? <div className="status-box success" role="status">{privacyNotice}</div> : null}

        <div className="settings-privacy-grid">
          <article className="settings-privacy-card">
            <h3>{t("Get a copy of your data", "Məlumatlarınızın surətini alın")}</h3>
            <p>{t("We prepare a file with your account information, projects and reports.", "Hesab məlumatlarınız, layihələriniz və hesabatlarınızla fayl hazırlayırıq.")}</p>
            <button className="secondary-button" type="button" onClick={submitExport} disabled={Boolean(busyAction) || loadingPrivacy}>
              {busyAction === "export" ? t("Sending…", "Göndərilir…") : t("Request a copy", "Surət istə")}
            </button>
          </article>
          <article className="settings-privacy-card danger-zone">
            <h3>{t("Delete your account data", "Hesab məlumatlarını silin")}</h3>
            <p id="erasure-help">{t("To confirm, type", "Təsdiq üçün yazın:")} <code>{ERASURE_CONFIRMATION}</code>. {t("Nothing is deleted until we review the request.", "Sorğu yoxlanılana qədər heç nə silinmir.")}</p>
            <input
              aria-label={t("Confirmation phrase", "Təsdiq ifadəsi")}
              aria-describedby="erasure-help"
              value={erasureConfirmation}
              onChange={(event) => setErasureConfirmation(event.target.value)}
              placeholder={ERASURE_CONFIRMATION}
              autoComplete="off"
            />
            <button className="secondary-button" type="button" onClick={submitErasure} disabled={Boolean(busyAction) || loadingPrivacy}>
              {busyAction === "erasure" ? t("Sending…", "Göndərilir…") : t("Request deletion", "Silinməni istə")}
            </button>
          </article>
        </div>

        <div className="settings-privacy-requests">
          <div>
            <h3>{t("Your requests", "Sorğularınız")}</h3>
            <p>{loadingPrivacy ? t("Loading requests…", "Sorğular yüklənir…") : activeRequests.length ? t(`${activeRequests.length} open request${activeRequests.length === 1 ? "" : "s"}.`, `${activeRequests.length} açıq sorğu.`) : t("No open requests.", "Açıq sorğu yoxdur.")}</p>
          </div>
          <div className="settings-privacy-list">
            {requests.length ? requests.map((request) => {
              const status = String(request?.status || "submitted").replace(/_/g, " ");
              const cancellable = ["submitted", "in_review", "approved"].includes(String(request?.status || "").toLowerCase());
              const requestId = request?.lifecycle_request_id || request?.id;
              return (
                <article className="settings-privacy-request" key={requestId || `${requestLabel(request, t)}-${request?.requested_at || ""}`}>
                  <div>
                    <strong>{requestLabel(request, t)}</strong>
                    <small>{t("Sent", "Göndərilib")} {formatDate(request?.requested_at || request?.created_at)} · {t("Status", "Vəziyyət")}: {status}</small>
                    {request?.scheduled_purge_at ? <small>{t("Deletion date", "Silinmə tarixi")}: {formatDate(request.scheduled_purge_at)}</small> : null}
                  </div>
                  {cancellable && requestId ? (
                    <button className="secondary-button" type="button" onClick={() => cancelRequest(requestId)} disabled={Boolean(busyAction)}>
                      {busyAction === requestId ? t("Cancelling…", "Ləğv edilir…") : t("Cancel request", "Sorğunu ləğv et")}
                    </button>
                  ) : null}
                </article>
              );
            }) : <p className="settings-privacy-empty">{t("You haven't sent any requests.", "Hələ sorğu göndərməmisiniz.")}</p>}
          </div>
        </div>

        <small className="settings-privacy-policy">
          {t("Deleted items are kept for", "Silinmiş elementlər saxlanılır:")} {policy?.soft_delete_retention_days ?? "—"} {t("days", "gün")} · {t("Erasure review period", "Silinmə sorğusunun yoxlanma müddəti")}: {policy?.erasure_grace_days ?? "—"} {t("days", "gün")} · {t("Export ready within", "İxrac hazır olur")}: {policy?.export_request_ttl_days ?? "—"} {t("days", "gün")}.
        </small>
      </section>
    </>
  );
}
