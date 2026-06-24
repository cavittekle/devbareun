import { useState } from "react";
import { workspaceApi } from "../api/client";
import { planCatalog } from "../data/packages";
import { PageHeader } from "../components/Shell";

export function Billing({ user, credits }) {
  const [status, setStatus] = useState(null);

  async function openCheckout(planCode) {
    setStatus("Preparing Lemon Squeezy checkout...");
    try {
      const response = await workspaceApi.checkout(planCode, {
        customer_email: user?.email,
        success_url: `${location.origin}/workspace/?view=payment-success&plan=${encodeURIComponent(planCode)}`,
        cancel_url: `${location.origin}/workspace/?view=payment-failed&plan=${encodeURIComponent(planCode)}`
      });
      const checkoutUrl = response?.checkout_url || response?.url;
      if (checkoutUrl) location.href = checkoutUrl;
      else setStatus("Checkout URL was not returned by the backend.");
    } catch (error) {
      setStatus(error.message || "Checkout could not be created.");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Billing and credits"
        title="Manage project analysis credits."
        description="Single Project unlocks one analysis. Plus and Pro use monthly project credits."
      />
      <section className="card-grid three">
        {Object.entries(planCatalog).map(([code, plan]) => (
          <article className={code === "plus" ? "panel featured" : "panel"} key={code}>
            <span className="workspace-eyebrow">{plan.credits}</span>
            <h2>{plan.name}</h2>
            <p><strong className="price">{plan.price}</strong> / {plan.cadence}</p>
            <button className={code === "plus" ? "primary-button full" : "secondary-button full"} onClick={() => openCheckout(code)}>
              {code === "single" ? "Upload one project" : `Start ${plan.name}`}
            </button>
          </article>
        ))}
      </section>
      <section className="panel">
        <h2>Current usage</h2>
        <p>{credits?.remaining ?? 0} credits remaining. Usage updates after successful payment and webhook delivery.</p>
        {status && <div className="status-box info">{status}</div>}
      </section>
    </>
  );
}
