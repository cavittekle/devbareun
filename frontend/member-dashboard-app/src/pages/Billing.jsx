import { useState } from "react";
import { CheckCircle2, CreditCard, LockKeyhole, RefreshCw, ShieldCheck, Sparkles } from "lucide-react";
import { workspaceApi } from "../api/client";
import { analysisPackages, planCatalog } from "../data/packages";
import { demoWorkspace } from "../data/demoWorkspace";
import { PageHeader } from "../components/Shell";

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

function planTone(code, currentCode) {
  if (code === currentCode) return "current";
  if (code === "pro") return "upgrade";
  return "neutral";
}

export function Billing({ user, credits, demoMode = false, activeDemoPackage = "schedule-recovery" }) {
  const [status, setStatus] = useState(demoMode ? "Preview billing is local-only. No checkout, payment or webhook request is sent." : null);
  const currentPlan = credits?.plan_code || "plus";
  const used = Number(credits?.used || 0);
  const remaining = Number(credits?.remaining || 0);
  const allowance = Number(credits?.monthly_allowance || used + remaining || 0);
  const usagePercent = allowance ? Math.min(100, Math.round((used / allowance) * 100)) : 0;
  const selectedPackage = analysisPackages.find((item) => item.id === activeDemoPackage) || analysisPackages[0];
  const packageInsight = demoWorkspace.packageInsights?.[activeDemoPackage] || demoWorkspace.packageInsights?.["schedule-recovery"];

  async function openCheckout(planCode) {
    if (demoMode) {
      const plan = planCatalog[planCode]?.name || planCode;
      setStatus(`${plan} checkout preview opened. No customer, payment or checkout request was sent.`);
      return;
    }
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
        eyebrow={demoMode ? "Billing center preview" : "Billing and credits"}
        title={demoMode ? "Credit control and plan preview." : "Manage project analysis credits."}
        description={demoMode ? "Review how customer billing, credits and checkout safety behave without sending payment data." : "Single Project unlocks one analysis. Plus and Pro use monthly project credits."}
      />

      {demoMode ? (
        <section className="billing-command-hero panel featured">
          <div>
            <span className="status-pill success">Preview safe</span>
            <h2>{credits?.plan_name || demoWorkspace.credits.plan_name} workspace credits</h2>
            <p>Active package: {selectedPackage.name}. {packageInsight?.signal}</p>
            <div className="billing-usage-bar">
              <i style={{ width: `${usagePercent}%` }} />
            </div>
            <small>{used} used - {remaining} remaining - renews {formatDate(credits?.renews_at)}</small>
          </div>
          <aside>
            <CreditCard size={26} />
            <span>Checkout boundary</span>
            <strong>No payment sent</strong>
            <p>Preview plan buttons only update this notice. Lemon Squeezy is not opened.</p>
          </aside>
        </section>
      ) : null}

      <section className="billing-plan-grid">
        {Object.entries(planCatalog).map(([code, plan]) => {
          const tone = planTone(code, currentPlan);
          return (
            <article className={`panel billing-plan-card ${tone} ${code === "plus" ? "featured" : ""}`} key={code}>
              <div className="billing-plan-head">
                <span className="workspace-eyebrow">{plan.credits}</span>
                {tone === "current" ? <span className="status-pill success">Current</span> : null}
                {tone === "upgrade" ? <span className="status-pill warning">Scale</span> : null}
              </div>
              <h2>{plan.name}</h2>
              <p><strong className="price">{plan.price}</strong> / {plan.cadence}</p>
              <ul className="billing-feature-list">
                <li><CheckCircle2 size={15} /> Project analysis credits</li>
                <li><CheckCircle2 size={15} /> Workspace dashboard history</li>
                <li><CheckCircle2 size={15} /> PDF / Excel report archive</li>
              </ul>
              <button className={code === "plus" ? "primary-button full" : "secondary-button full"} onClick={() => openCheckout(code)}>
                {demoMode ? `Preview ${plan.name}` : code === "single" ? "Upload one project" : `Start ${plan.name}`}
              </button>
            </article>
          );
        })}
      </section>

      <section className="billing-control-grid">
        <article className="panel">
          <div className="team-section-head">
            <div>
              <span className="workspace-eyebrow">Current usage</span>
              <h2>{remaining} credits remaining</h2>
              <p>Usage updates after successful payment and webhook delivery.</p>
            </div>
            <RefreshCw size={24} />
          </div>
          <div className="billing-usage-meta">
            <div><span>Used</span><strong>{used}</strong></div>
            <div><span>Allowance</span><strong>{allowance || "-"}</strong></div>
            <div><span>Renewal</span><strong>{formatDate(credits?.renews_at)}</strong></div>
          </div>
        </article>

        <article className="panel">
          <div className="team-section-head">
            <div>
              <span className="workspace-eyebrow">Payment safety</span>
              <h2>{demoMode ? "Preview payment boundary" : "Checkout status"}</h2>
              <p>{demoMode ? "No checkout URLs, customer emails, cards or webhook calls are sent from this preview." : "Checkout uses backend-created Lemon Squeezy sessions."}</p>
            </div>
            <ShieldCheck size={24} />
          </div>
          <div className="billing-safety-list">
            <div><LockKeyhole size={16} /><span>Private payment keys stay backend-only.</span></div>
            <div><Sparkles size={16} /><span>Credits unlock package dashboards after analysis.</span></div>
          </div>
          {status && <div className="status-box info">{status}</div>}
        </article>
      </section>
    </>
  );
}
