import { EmptyState, PageHeader } from "../components/Shell";
import { workspaceApi } from "../api/client";
import { useT } from "../lib/i18n";

export function Reports({ reports, onNavigate }) {
  const t = useT();
  return (
    <>
      <PageHeader
        eyebrow={t("Reports", "Hesabatlar")}
        title={t("Reports", "Hesabatlar")}
        description={t("Execution and delay reports from your analyses, as PDF and Excel.", "Analizlərinizdən hazırlanmış PDF və Excel icra və gecikmə hesabatları.")}
      />
      {reports.length === 0 ? (
        <EmptyState
          title={t("No reports yet.", "Hələ hesabat yoxdur.")}
          description={t("A report is ready here when an analysis finishes.", "Analiz bitən kimi hesabat burada görünür.")}
          action={<button type="button" className="secondary-button" onClick={() => onNavigate("upload")}>{t("Start an analysis", "Analizə başla")}</button>}
        />
      ) : (
        <section className="table-list">
          {reports.map((report) => {
            const name = report.report_name || report.name || t("Project report", "Layihə hesabatı");
            const downloads = Number(report.download_count || 0);
            return (
              <article key={report.report_id || report.id}>
                <div>
                  <strong>{name}</strong>
                  <span>{report.project_name || report.type || t("Project report", "Layihə hesabatı")}</span>
                  <small>{report.format || "PDF"} · {report.snapshot_available ? t("Frozen analysis snapshot", "Dəyişməz analiz nüsxəsi") : t("Earlier report format", "Əvvəlki hesabat formatı")}{downloads > 0 ? ` · ${t(`${downloads} downloads`, `${downloads} dəfə yüklənib`)}` : ""}</small>
                </div>
                <a className="secondary-button" href={workspaceApi.reportDownloadUrl(report.id || report.report_id)} aria-label={`${t("Download", "Yüklə")}: ${name}`}>{t("Download", "Yüklə")}</a>
              </article>
            );
          })}
        </section>
      )}
    </>
  );
}
