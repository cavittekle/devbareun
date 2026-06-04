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

  async function activatePilot(checkoutId) {
    const api = window.DevBareunAuth?.api;
    if (!api) throw new Error("Workspace API is not ready.");
    const email = window.DevBareunAuth?.getSession?.()?.user?.email || params.get("email") || "";
    const q = new URLSearchParams({ checkout_id: checkoutId });
    if (email) q.set("customer_email", email);
    return api(`/api/payments/activate-pilot-checkout?${q.toString()}`, { method: "POST", body: "{}" });
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
        <p class="muted">${isGuestSingleFlow() ? "No account is required for Single Project. In staging, activate the pilot checkout to continue with one paid project analysis." : "Lemon Squeezy checkout will open automatically when production keys are configured. In staging, activate the pilot checkout to grant test credits."}</p>
        <div class="report-meta-grid">
          <div class="report-meta-item"><span>Checkout ID</span><strong>${esc(checkoutId || "pending")}</strong></div>
          <div class="report-meta-item"><span>Mode</span><strong>${esc(params.get("mode") || "lemonsqueezy/pilot")}</strong></div>
        </div>
        <div class="workspace-actions">
          <button class="btn btn-primary" data-activate-pilot ${checkoutId ? "" : "disabled"}>Activate pilot checkout</button>
          <a class="btn btn-ghost" href="${isGuestSingleFlow() ? "/index.html#pricing" : "/billing.html"}">Back</a>
        </div>
        <p id="paymentFlowStatus" class="auth-status"></p>
      </section>`;
  }

  function bindActivation() {
    document.addEventListener("click", async (event) => {
      const btn = event.target.closest("[data-activate-pilot]");
      if (!btn) return;
      event.preventDefault();
      const status = $("#paymentFlowStatus");
      const checkout = lastCheckout();
      const checkoutId = params.get("checkout_id") || checkout?.checkout_id || checkout?.data?.checkout_session?.checkout_id || "";
      try {
        btn.disabled = true;
        if (status) status.textContent = "Activating checkout...";
        await activatePilot(checkoutId);
        await window.DevBareunAuth?.refreshEntitlements?.();
        if (status) status.textContent = isGuestSingleFlow() ? "Checkout activated. Continue with your project upload." : "Checkout activated. Credits are available in your workspace.";
        setTimeout(() => { location.href = isGuestSingleFlow() ? "/index.html#upload" : "/dashboard.html"; }, 600);
      } catch (err) {
        if (status) status.textContent = err.message;
        btn.disabled = false;
      }
    });
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
      mount.textContent = "Confirming payment access...";
      await activatePilot(checkoutId);
      await window.DevBareunAuth?.refreshEntitlements?.();
      mount.textContent = isGuestSingleFlow() ? "Payment confirmed. Continue with your project upload." : "Access confirmed. Credits are ready.";
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
