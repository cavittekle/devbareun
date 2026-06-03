/*
DevBareun Billing Gate
v1.3.8 — plan checkout bridge for Single / Plus / Pro packages.
*/
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  function esc(value) {
    return String(value ?? "").replace(/[&<>\"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[ch]));
  }

  function currentEmail() {
    return window.DevBareunAuth?.getSession?.()?.user?.email || "";
  }

  function checkoutEndpoint(plan) {
    return plan === "single" ? "/api/billing/create-one-time-checkout" : "/api/billing/create-subscription-checkout";
  }

  async function createCheckout(plan, projectId) {
    const api = window.DevBareunAuth?.api;
    if (!api) throw new Error("Workspace API is not ready.");
    const email = currentEmail() || window.prompt("Enter your email for checkout receipts:", "");
    if (!email || !email.includes("@")) throw new Error("Email is required to open checkout.");
    const origin = window.location.origin;
    return api(checkoutEndpoint(plan), {
      method: "POST",
      body: JSON.stringify({
        plan: plan,
        plan_code: plan,
        project_id: projectId || null,
        customer_email: email || null,
        success_url: `${origin}/payment-success.html?plan=${encodeURIComponent(plan)}`,
        cancel_url: `${origin}/payment-failed.html?plan=${encodeURIComponent(plan)}`,
      }),
    });
  }

  function renderEntitlementSummary() {
    const mount = $("#billingEntitlementSummary");
    if (!mount) return;
    const session = window.DevBareunAuth?.getSession?.();
    const ent = session?.entitlements;
    if (!session) {
      mount.innerHTML = `<div class="empty-state">Login to view current plan, credits and report usage.</div>`;
      return;
    }
    mount.innerHTML = `
      <article class="billing-current-card">
        <div>
          <p class="eyebrow">Current workspace</p>
          <h2>${esc(session.user?.email)}</h2>
          <p class="muted">Plan: <b>${esc(session.user?.plan || "guest")}</b> · Credits: <b>${esc(session.user?.credits_remaining ?? 0)}</b></p>
        </div>
        <div class="billing-meter-grid">
          <span><b data-project-count>${esc(ent?.usage?.projects ?? 0)}</b> Projects</span>
          <span><b data-analysis-count>${esc(ent?.usage?.analyses ?? 0)}</b> Analyses</span>
          <span><b data-report-count>${esc(ent?.usage?.reports ?? 0)}</b> Reports</span>
        </div>
      </article>`;
  }


  function selectedPlanFromUrl() {
    const params = new URLSearchParams(location.search);
    return params.get("plan") || localStorage.getItem("devbareun_selected_plan") || "plus";
  }

  function markSelectedPlan(plan) {
    $$('[data-plan-card]').forEach((card) => {
      card.classList.toggle('is-selected', card.getAttribute('data-plan-card') === plan);
      if (card.getAttribute('data-plan-card') === plan) {
        card.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    });
  }

  function bindCheckoutButtons() {
    document.addEventListener("click", async (event) => {
      const btn = event.target.closest("[data-plan-checkout]");
      if (!btn) return;
      event.preventDefault();
      const plan = btn.getAttribute("data-plan-checkout") || "single";
      localStorage.setItem("devbareun_selected_plan", plan);
      markSelectedPlan(plan);
      const status = $("#billingStatus");
      try {
        btn.disabled = true;
        if (status) status.textContent = `Creating ${plan} checkout...`;
        const projectId = new URLSearchParams(location.search).get("project_id");
        const data = await createCheckout(plan, projectId);
        const session = data.checkout_session || {};
        const checkoutId = session.checkout_id || data.checkout_id || new URLSearchParams(data.checkout_url || "").get("checkout_id");
        localStorage.setItem("devbareun_last_checkout", JSON.stringify({ plan, checkout_id: checkoutId, data }));
        if (data.checkout_url) {
          location.href = data.checkout_url;
          return;
        }
        location.href = `/checkout.html?plan=${encodeURIComponent(plan)}&checkout_id=${encodeURIComponent(checkoutId || "")}&mode=pilot`;
      } catch (err) {
        if (status) status.textContent = err.message;
        btn.disabled = false;
      }
    });
  }

  document.addEventListener("DOMContentLoaded", async () => {
    bindCheckoutButtons();
    markSelectedPlan(selectedPlanFromUrl());
    await window.DevBareunAuth?.refreshEntitlements?.();
    renderEntitlementSummary();
  });
})();
