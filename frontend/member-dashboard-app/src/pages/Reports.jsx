import { EmptyState, PageHeader } from "../components/Shell";
import { workspaceApi } from "../api/client";

export function Reports({ reports, onNavigate }) {
  return (
    <>
      <PageHeader
        eyebrow="Report archive"
        title="Reports"
        description="PDF and Excel outputs generated from real project analyses."
      />
      {reports.length === 0 ? (
        <EmptyState
          title="No reports generated."
          description="Run an analysis from uploaded files to create report outputs."
          action={<button className="secondary-button" onClick={() => onNavigate("upload")}>Upload Files</button>}
        />
      ) : (
        <section className="table-list">
          {reports.map((report) => (
            <article key={report.report_id || report.id}>
              <div>
                <strong>{report.report_name || report.name || "Project report"}</strong>
                <span>{report.project_name || report.type || "Project report"}</span>
                <small>{report.format || "PDF"} · {report.snapshot_available ? "Frozen analysis snapshot" : "Legacy report"}{Number(report.download_count || 0) > 0 ? ` · ${report.download_count} downloads` : ""}</small>
              </div>
              <a className="secondary-button" href={workspaceApi.reportDownloadUrl(report.id || report.report_id)}>Download</a>
            </article>
          ))}
        </section>
      )}
    </>
  );
}
