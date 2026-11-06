import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Clock3, XCircle } from "lucide-react";
import { workspaceApi } from "../api/client";
import { useT } from "../lib/i18n";

const TERMINAL_SUCCESS = new Set(["paid", "subscription_active"]);
const TERMINAL_FAILURE = new Set(["payment_failed", "canceled", "expired", "refunded"]);

export function PaymentStatus({ status = "success" }) {
  const t = useT();
  const [message, setMessage] = useState(t("Checking your payment...", "Ödənişiniz yoxlanılır..."));
  const [lifecycle, setLifecycle] = useState(null);
  const [loading, setLoading] = useState(false);
  const params = useMemo(() => new URLSearchParams(location.search), []);
  const planCode = params.get("plan") || "";
  const plan = { single: "Single Project", plus: "Plus", pro: "Pro" }[planCode] || planCode;
  const checkoutId = params.get("checkout_id") || params.get("session_id") || "";
  const lifecycleStatus = String(lifecycle?.checkout?.status || "").toLowerCase();
  const isLifecycleSuccess = TERMINAL_SUCCESS.has(lifecycleStatus);
  const isLifecycleFailure = TERMINAL_FAILURE.has(lifecycleStatus);
  const isSuccess = isLifecycleSuccess || (!checkoutId && status === "success");
  const isFailed = !isLifecycleSuccess && (isLifecycleFailure || status === "failed");

  useEffect(() => {
    if (!checkoutId) {
      setMessage(isFailed
        ? t("The payment was cancelled or didn't go through. No money was taken. You can try again from Billing.", "Ödəniş ləğv edildi və ya baş tutmadı. Pul tutulmayıb. Ödəniş bölməsindən yenidən cəhd edə bilərsiniz.")
        : t("Thank you. Your credits appear in the workspace within a few minutes.", "Təşəkkür edirik. Kreditləriniz bir neçə dəqiqə ərzində iş sahəsində görünəcək."));
      return undefined;
    }

    let cancelled = false;
    let timer = null;
    let attempts = 0;
    const maxAttempts = 12;
    async function refresh() {
      setLoading(true);
      try {
        const response = await workspaceApi.checkoutStatus(checkoutId);
        if (cancelled) return;
        setLifecycle(response);
        const current = String(response?.checkout?.status || "").toLowerCase();
        if (TERMINAL_SUCCESS.has(current)) {
          setMessage(t("Payment confirmed. Your credits are ready to use.", "Ödəniş təsdiqləndi. Kreditləriniz istifadəyə hazırdır."));
          return;
        }
        if (TERMINAL_FAILURE.has(current)) {
          setMessage(t("The payment didn't go through. You can try again from Billing.", "Ödəniş baş tutmadı. Ödəniş bölməsindən yenidən cəhd edə bilərsiniz."));
          return;
        }
        attempts += 1;
        setMessage(t("Waiting for the bank to confirm the payment. This page updates by itself.", "Ödənişin bank tərəfindən təsdiqi gözlənilir. Bu səhifə özü yenilənəcək."));
        if (attempts < maxAttempts) timer = window.setTimeout(refresh, Math.max(2000, Number(response?.poll_after_seconds || 5) * 1000));
      } catch (error) {
        if (cancelled) return;
        setMessage(error?.message || t("We can't check the payment yet. Refresh this page in a minute.", "Ödənişi hələ yoxlamaq olmur. Bir dəqiqə sonra səhifəni yeniləyin."));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    refresh();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [checkoutId, isFailed]);

  const Icon = isSuccess ? CheckCircle2 : isFailed ? XCircle : Clock3;
  const stateClass = isSuccess ? "success" : isFailed ? "error" : "";
  const label = isSuccess ? t("Payment confirmed", "Ödəniş təsdiqləndi") : isFailed ? t("Payment not completed", "Ödəniş tamamlanmadı") : t("Payment pending", "Ödəniş gözlənilir");
  const title = isSuccess ? t("Your payment is confirmed.", "Ödənişiniz təsdiqləndi.") : isFailed ? t("The payment was not completed.", "Ödəniş tamamlanmadı.") : t("Waiting for payment confirmation.", "Ödənişin təsdiqi gözlənilir.");

  return (
    <main className="auth-screen compact">
      <section className={`auth-card panel payment-state ${stateClass}`}>
        <Icon size={42} aria-hidden="true" />
        <span className="workspace-eyebrow">{label}</span>
        <h1>{title}</h1>
        <p role="status">{message}</p>
        {(plan || checkoutId) && (
          <div className="payment-meta">
            {plan && <><span>{t("Plan", "Plan")}</span><strong>{plan}</strong></>}
            {checkoutId && <><span>{t("Payment reference", "Ödəniş nömrəsi")}</span><strong>{checkoutId}</strong></>}
          </div>
        )}
        <div className="auth-actions">
          {isFailed
            ? <><a className="primary-button" href="/workspace/?view=billing">{t("Try again", "Yenidən cəhd et")}</a><a className="secondary-button" href="/workspace/">{t("Open workspace", "İş sahəsini aç")}</a></>
            : <><a className="primary-button" href="/workspace/">{t("Open workspace", "İş sahəsini aç")}</a><a className="secondary-button" href="/workspace/?view=billing">{t("Billing", "Ödəniş")}</a></>}
        </div>
        {loading && <p className="workspace-muted">{t("Checking with the payment provider…", "Ödəniş provayderi ilə yoxlanılır…")}</p>}
      </section>
    </main>
  );
}
