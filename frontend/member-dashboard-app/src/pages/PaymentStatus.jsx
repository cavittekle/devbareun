import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Clock3, XCircle } from "lucide-react";
import { workspaceApi } from "../api/client";

const TERMINAL_SUCCESS = new Set(["paid", "subscription_active"]);
const TERMINAL_FAILURE = new Set(["payment_failed", "canceled", "expired", "refunded"]);

export function PaymentStatus({ status = "success" }) {
  const [message, setMessage] = useState("Reading checkout status...");
  const [lifecycle, setLifecycle] = useState(null);
  const [loading, setLoading] = useState(false);
  const params = useMemo(() => new URLSearchParams(location.search), []);
  const plan = params.get("plan") || "workspace";
  const checkoutId = params.get("checkout_id") || params.get("session_id") || "";
  const lifecycleStatus = String(lifecycle?.checkout?.status || "").toLowerCase();
  const isLifecycleSuccess = TERMINAL_SUCCESS.has(lifecycleStatus);
  const isLifecycleFailure = TERMINAL_FAILURE.has(lifecycleStatus);
  const isSuccess = isLifecycleSuccess || (!checkoutId && status === "success");
  const isFailed = !isLifecycleSuccess && (isLifecycleFailure || status === "failed");

  useEffect(() => {
    if (!checkoutId) {
      setMessage(isFailed ? "Payment was cancelled or could not be completed. You can return to billing and try again." : "Payment page loaded. Credits and access update after the Lemon Squeezy webhook is delivered.");
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
          setMessage("Payment confirmed. Your workspace access has been updated.");
          return;
        }
        if (TERMINAL_FAILURE.has(current)) {
          setMessage("The payment provider reported that this checkout was not completed. You can try again from Billing.");
          return;
        }
        attempts += 1;
        setMessage("Checkout is waiting for verified payment confirmation. This page will update automatically.");
        if (attempts < maxAttempts) timer = window.setTimeout(refresh, Math.max(2000, Number(response?.poll_after_seconds || 5) * 1000));
      } catch (error) {
        if (cancelled) return;
        setMessage(error?.message || "Checkout status could not be read yet. You can refresh this page shortly.");
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
  const label = isSuccess ? "Payment confirmed" : isFailed ? "Checkout incomplete" : "Payment confirmation pending";
  const title = isSuccess ? "Payment status confirmed." : isFailed ? "Payment was not completed." : "Waiting for payment confirmation.";

  return (
    <main className="auth-screen compact">
      <section className={`auth-card panel payment-state ${stateClass}`}>
        <Icon size={42} />
        <span className="workspace-eyebrow">{label}</span>
        <h1>{title}</h1>
        <p>{message}</p>
        <div className="payment-meta">
          <span>Plan</span><strong>{plan}</strong>
          <span>Checkout</span><strong>{checkoutId || "pending webhook"}</strong>
          {lifecycleStatus && <><span>Lifecycle</span><strong>{lifecycleStatus}</strong></>}
        </div>
        <div className="auth-actions">
          <a className="primary-button" href="/workspace/">Open workspace</a>
          <a className="secondary-button" href="/workspace/?view=billing">Billing</a>
        </div>
        {loading && <p className="workspace-muted">Verifying provider confirmation…</p>}
      </section>
    </main>
  );
}
