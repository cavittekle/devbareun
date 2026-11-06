import { PageHeader, EmptyState } from "../components/Shell";
import { formatCount } from "../lib/format";
import { useT } from "../lib/i18n";

export function Overview({ projects, reports, credits, onNavigate }) {
  const t = useT();
  const projectCount = projects.length;
  const reportCount = reports.length;
  const remaining = credits?.remaining ?? 0;

  return (
    <>
      <PageHeader
        eyebrow={t("Workspace", "İş sahəsi")}
        title={t("Your delay analyses", "Gecikmə analizləriniz")}
        description={t("Projects, execution reports and remaining analysis credits in one place.", "Layihələr, icra hesabatları və qalan analiz kreditləri bir yerdə.")}
        action={<button type="button" className="primary-button" onClick={() => onNavigate("upload")}>{t("Start new analysis", "Yeni analizə başla")}</button>}
      />

      <section className="kpi-grid">
        <article>
          <span>{t("Projects", "Layihələr")}</span>
          <strong>{formatCount(projectCount)}</strong>
          <small>{t("In this workspace", "Bu iş sahəsində")}</small>
        </article>
        <article>
          <span>{t("Reports ready", "Hazır hesabatlar")}</span>
          <strong>{formatCount(reportCount)}</strong>
          <small>{t("PDF and Excel", "PDF və Excel")}</small>
        </article>
        <article>
          <span>{t("Credits left", "Qalan kreditlər")}</span>
          <strong>{formatCount(remaining)}</strong>
          <small>{t("One credit runs one analysis", "Bir kredit bir analiz üçündür")}</small>
        </article>
        <article>
          <span>{t("Status", "Vəziyyət")}</span>
          <strong>{projectCount ? t("Active", "Aktiv") : t("Empty", "Boş")}</strong>
          <small>{projectCount ? t("Projects uploaded", "Layihələr yüklənib") : t("Nothing uploaded yet", "Hələ heç nə yüklənməyib")}</small>
        </article>
      </section>

      {projectCount === 0 ? (
        <EmptyState
          title={t("No projects yet.", "Hələ layihə yoxdur.")}
          description={t(
            "Upload the planning, the current F2 and F3 certificates and the contract to get your first execution and delay report.",
            "İlk icra və gecikmə hesabatını almaq üçün planlamanı, cari F2 və F3 aktlarını və müqaviləni yükləyin."
          )}
          action={<button type="button" className="secondary-button" onClick={() => onNavigate("upload")}>{t("Upload files", "Faylları yüklə")}</button>}
        />
      ) : (
        <section className="panel">
          <h2>{t("Recent projects", "Son layihələr")}</h2>
          <div className="table-list">
            {projects.slice(0, 5).map((project) => (
              <article key={project.project_id || project.id}>
                <strong>{project.project_name || project.name || t("Untitled project", "Adsız layihə")}</strong>
                <span>{project.current_status || project.status || t("Uploaded", "Yüklənib")}</span>
              </article>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
