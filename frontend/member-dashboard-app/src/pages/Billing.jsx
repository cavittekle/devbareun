import { useState } from "react";
import { workspaceApi } from "../api/client";
import { planCatalog } from "../data/packages";
import { PageHeader } from "../components/Shell";
import { useT } from "../lib/i18n";

const PLAN_TEXT = {
  single: { credits: ["1 project", "1 layihə"], cadence: ["one-time", "birdəfəlik"] },
  plus: { credits: ["5 / month", "5 / ay"], cadence: ["month", "ay"] },
  pro: { credits: ["20 / month", "20 / ay"], cadence: ["month", "ay"] }
};

export function Billing({ user, credits }) {
  const t = useT();
  const pick = (pair) => t(pair[0], pair[1]);
  const [status, setStatus] = useState(null);

  async function openCheckout(planCode) {
    setStatus({ type: "info", text: t("Opening the secure payment page...", "Təhlükəsiz ödəniş səhifəsi açılır...") });
    try {
      const response = await workspaceApi.checkout(planCode, {
        customer_email: user?.email,
        success_url: `${location.origin}/workspace/?view=payment-success&plan=${encodeURIComponent(planCode)}`,
        cancel_url: `${location.origin}/workspace/?view=payment-failed&plan=${encodeURIComponent(planCode)}`
      });
      const checkoutUrl = response?.checkout_url || response?.url;
      if (checkoutUrl) location.href = checkoutUrl;
      else setStatus({ type: "error", text: t("The payment page didn't open. Try again, or write to info@devbareun.com.", "Ödəniş səhifəsi açılmadı. Yenidən cəhd edin və ya info@devbareun.com ünvanına yazın.") });
    } catch (error) {
      setStatus({ type: "error", text: error.message || t("The payment page didn't open. Try again in a minute.", "Ödəniş səhifəsi açılmadı. Bir dəqiqə sonra yenidən cəhd edin.") });
    }
  }

  return (
    <>
      <PageHeader
        eyebrow={t("Billing", "Ödəniş")}
        title={t("Plans and analysis credits", "Planlar və analiz kreditləri")}
        description={t("Single Project pays for one analysis. Plus and Pro add analysis credits every month.", "Single Project bir analiz üçündür. Plus və Pro hər ay analiz krediti əlavə edir.")}
      />
      <section className="card-grid three">
        {Object.entries(planCatalog).map(([code, plan]) => (
          <article className={code === "plus" ? "panel featured" : "panel"} key={code}>
            <span className="workspace-eyebrow">{pick(PLAN_TEXT[code]?.credits || [plan.credits, plan.credits])}</span>
            <h2>{plan.name}</h2>
            <p><strong className="price">{plan.price}</strong> / {pick(PLAN_TEXT[code]?.cadence || [plan.cadence, plan.cadence])}</p>
            <button type="button" className={code === "plus" ? "primary-button full" : "secondary-button full"} onClick={() => openCheckout(code)}>
              {code === "single" ? t("Pay for one project", "Bir layihə üçün ödə") : t(`Start ${plan.name}`, `${plan.name} başlat`)}
            </button>
          </article>
        ))}
      </section>
      <section className="panel">
        <h2>{t("Current usage", "Cari istifadə")}</h2>
        <p>{t(
          `${credits?.remaining ?? 0} credits left. New credits appear a few minutes after payment is confirmed.`,
          `${credits?.remaining ?? 0} kredit qalıb. Yeni kreditlər ödəniş təsdiqləndikdən bir neçə dəqiqə sonra görünür.`
        )}</p>
        {status && <div className={`status-box ${status.type}`} role={status.type === "error" ? "alert" : "status"}>{status.text}</div>}
      </section>
    </>
  );
}
