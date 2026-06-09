/*
DevBareun Payment Flow
v1.3.8 — checkout result and pilot activation helper.
*/
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const params = new URLSearchParams(location.search);

  function esc(value) {
    return String(value ?? "").replace(/[&<>\"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[ch]));
  }

  function lastCheckout() {
    try { return JSON.parse(localStorage.getItem("devbareun_last_checkout") || "null"); }
    catch { return null; }
  }

  function pendingSingleProject() {
    try { return JSON.parse(localStorage.getItem("devbareun_pending_single_project") || "null"); }
    catch { return null; }
  }

  function isGuestSingleFlow() {
    const checkout = lastCheckout();
    return (params.get("plan") || checkout?.plan) === "single" &&
      (params.get("guest") === "1" || params.get("mode") === "guest" || !window.DevBareunAuth?.getSession?.()?.access_token);
  }

  function renderCheckout() {
    const mount = $("#checkoutPanel");
    if (!mount) return;
    const checkout = lastCheckout();
    const checkoutId = params.get("checkout_id") || checkout?.checkout_id || checkout?.data?.checkout_session?.checkout_id || "";
    const plan = params.get("plan") || checkout?.plan || "single";
    mount.innerHTML = `
      <section class="workspace-panel wide checkout-review-card">
        <p class="eyebrow">Checkout review</p>
        <h1>${esc(plan).toUpperCase()} package</h1>
        <p class="muted">${isGuestSingleFlow() ? "No account is required for Single Project. Payment confirmation is handled by the payment provider webhook." : "Checkout opens through the payment provider. Credits are activated after webhook confirmation."}</p>
        <div class="report-meta-grid">
          <div class="report-meta-item"><span>Checkout ID</span><strong>${esc(checkoutId || "pending")}</strong></div>
          <div class="report-meta-item"><span>Mode</span><strong>${esc(params.get("mode") || "payment-provider")}</strong></div>
        </div>
        <div class="workspace-actions">
          <a class="btn btn-primary" href="${isGuestSingleFlow() ? "/index.html#upload" : "/dashboard.html"}">Continue</a>
          <a class="btn btn-ghost" href="${isGuestSingleFlow() ? "/index.html#pricing" : "/billing.html"}">Back</a>
        </div>
        <p id="paymentFlowStatus" class="auth-status"></p>
      </section>`;
  }

  function bindActivation() {
    return;
  }

  async function renderSuccess() {
    const mount = $("#paymentSuccessStatus");
    if (!mount) return;
    const projectId = params.get("project_id");
    if (projectId && window.DevBareunAPI?.analyzeProject) {
      const pending = pendingSingleProject() || {};
      const analysisType = pending.analysis_type || "all";
      const attempts = 4;
      for (let i = 1; i <= attempts; i += 1) {
        try {
          mount.textContent = i === 1
            ? "Payment received. Generating your Single Project dashboard..."
            : "Payment webhook is still confirming. Retrying dashboard generation...";
          await window.DevBareunAPI.analyzeProject(projectId, analysisType, {});
          localStorage.removeItem("devbareun_pending_single_project");
          mount.textContent = "Dashboard is ready. Opening your result...";
          setTimeout(() => {
            location.href = `result-dashboard.html?project_id=${encodeURIComponent(projectId)}`;
          }, 650);
          return;
        } catch (err) {
          if (i >= attempts || !/payment|credit|required|402|paid/i.test(String(err.message || err))) {
            mount.textContent = `Payment page loaded, but dashboard generation needs review: ${err.message || err}`;
            return;
          }
          await new Promise(resolve => setTimeout(resolve, 1800));
        }
      }
      return;
    }
    const checkoutId = params.get("checkout_id");
    if (!checkoutId || checkoutId === "{CHECKOUT_SESSION_ID}") {
      mount.textContent = "Payment status received. Open your dashboard to continue.";
      return;
    }
    try {
      mount.textContent = "Payment page loaded. Waiting for provider webhook confirmation.";
      await window.DevBareunAuth?.refreshEntitlements?.();
    } catch (err) {
      mount.textContent = "Payment page loaded. Webhook confirmation may still be pending.";
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    renderCheckout();
    bindActivation();
    renderSuccess();
  });
})();
