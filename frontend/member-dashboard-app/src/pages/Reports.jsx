import { Archive, ArrowRight, BarChart3, CheckCircle2, Download, FileSpreadsheet, FileText, FolderCheck, LockKeyhole, ShieldCheck } from "lucide-react";
import { EmptyState, PageHeader } from "../components/Shell";
import { PackageSegmentedControl } from "../components/PackageSegmentedControl";
import { workspaceApi } from "../api/client";
import { analysisPackages } from "../data/packages";
import { demoWorkspace } from "../data/demoWorkspace";

function formatDate(value) {
  if (!value) return "Not generated yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });
}

function reportIcon(format) {
  return String(format || "").toLowerCase().includes("excel") ? FileSpreadsheet : FileText;
}

function reportTone(report) {
  const status = String(report.status || "").toLowerCase();
  if (status.includes("review")) return "warning";
  if (status.includes("ready") || report.snapshot_available) return "success";
  return "neutral";
}

function packageFromReport(report) {
  const packageName = String(report.package_name || report.package || "").toLowerCase();
  return analysisPackages.find((item) => (
    item.id === report.package_id || item.name.toLowerCase() === packageName
  ));
}

export function Reports({
  reports,
  onNavigate,
  demoMode = false,
  activeDemoPackage = "schedule-recovery",
  onDemoPackageChange
}) {
  const selectedPackage = analysisPackages.find((item) => item.id === activeDemoPackage) || analysisPackages[0];
  const packageInsight = demoWorkspace.packageInsights?.[selectedPackage.id];
  const activeReports = demoMode
    ? reports.filter((report) => packageFromReport(report)?.id === selectedPackage.id)
    : reports;
  const visibleReports = demoMode && activeReports.length ? activeReports : reports;
  const readyCount = reports.filter((report) => report.snapshot_available || report.status === "Ready").length;
  const downloadCount = reports.reduce((total, report) => total + Number(report.download_count || 0), 0);
  const activeReadyCount = activeReports.filter((report) => report.snapshot_available || report.status === "Ready").length;
  const activeDownloadCount = activeReports.reduce((total, report) => total + Number(report.download_count || 0), 0);

  function openDashboard(packageId = selectedPackage.id) {
    if (demoMode) onDemoPackageChange?.(packageId);
    onNavigate("result");
  }

  function createOutput(packageId = selectedPackage.id) {
    if (demoMode) onDemoPackageChange?.(packageId);
    onNavigate("upload");
  }

  return (
    <>
      <PageHeader
        eyebrow="Report archive"
        title={demoMode ? "Report package archive." : "Reports"}
        description={demoMode ? "PDF and Excel outputs grouped by the selected construction-control package." : "PDF and Excel outputs generated from real project analyses."}
        action={(
          <div className="report-header-actions">
            <button className="secondary-button" type="button" onClick={() => createOutput()}>Create new output</button>
          </div>
        )}
      />
      {reports.length === 0 ? (
        <EmptyState
          title="No reports generated."
          description="Run an analysis from uploaded files to create report outputs."
          action={<button className="secondary-button" onClick={() => onNavigate("upload")}>Upload Files</button>}
        />
      ) : (
        <>
          <section className="reports-hero panel featured">
            <div>
              <span className="status-pill success">{demoMode ? selectedPackage.name : "Workspace archive"}</span>
              <h2>{demoMode ? `${selectedPackage.name} export control` : "Export-ready management packs"}</h2>
              <p>{demoMode ? packageInsight?.nextStep : "Each report keeps the selected control package, source-trace sections and download history visible for review."}</p>
              {demoMode ? (
                <div className="report-hero-actions">
                  <button className="primary-button" type="button" onClick={() => openDashboard()}>
                    <BarChart3 size={16} /> Open dashboard
                  </button>
                </div>
              ) : null}
            </div>
            <aside>
              <div><span>{demoMode ? "Active package reports" : "Reports"}</span><strong>{demoMode ? activeReports.length : reports.length}</strong></div>
              <div><span>{demoMode ? "Ready for handoff" : "Ready snapshots"}</span><strong>{demoMode ? activeReadyCount : readyCount}</strong></div>
              <div><span>{demoMode ? "Preview downloads" : "Downloads"}</span><strong>{demoMode ? activeDownloadCount : downloadCount}</strong></div>
            </aside>
          </section>

          {demoMode ? (
            <section className="report-package-tabs panel compact">
              <div>
                <span className="workspace-eyebrow">Package focus</span>
                <h2>Switch archive package</h2>
              </div>
              <PackageSegmentedControl
                activePackage={selectedPackage.id}
                onPackageChange={onDemoPackageChange}
                ariaLabel="Switch report package"
              />
            </section>
          ) : null}

          <section className="reports-grid">
            {visibleReports.map((report) => {
              const Icon = reportIcon(report.format);
              const reportId = report.id || report.report_id;
              const reportPackage = packageFromReport(report);
              return (
                <article className={`report-card panel ${demoMode && reportPackage?.id === selectedPackage.id ? "active" : ""}`} key={reportId}>
                  <div className="report-card-head">
                    <div className="report-icon"><Icon size={22} /></div>
                    <div>
                      <span className={`status-pill ${reportTone(report)}`}>{report.status || (report.snapshot_available ? "Ready" : "Legacy")}</span>
                      <h2>{report.report_name || report.name || "Project report"}</h2>
                      <p>{report.summary || report.project_name || "Generated project report."}</p>
                    </div>
                  </div>

                  <div className="report-meta-grid">
                    <div><span>Package</span><strong>{report.package_name || "Project report"}</strong></div>
                    <div><span>Format</span><strong>{report.format || "PDF"}</strong></div>
                    <div><span>Generated</span><strong>{formatDate(report.generated_at)}</strong></div>
                    <div><span>Frozen analysis snapshot</span><strong>{report.snapshot_available ? "Frozen" : "Legacy"}</strong></div>
                  </div>

                  {report.sections?.length ? (
                    <ul className="report-section-list">
                      {report.sections.map((section) => (
                        <li key={section}><CheckCircle2 size={15} /> {section}</li>
                      ))}
                    </ul>
                  ) : null}

                  <div className="report-card-actions">
                    {demoMode ? (
                      <span className="status-pill neutral"><LockKeyhole size={14} /> Preview only</span>
                    ) : (
                      <a className="secondary-button" href={workspaceApi.reportDownloadUrl(reportId)}><Download size={16} /> Download</a>
                    )}
                    <button className="secondary-button" type="button" onClick={() => openDashboard(reportPackage?.id)}>
                      Open dashboard <ArrowRight size={15} />
                    </button>
                  </div>
                </article>
              );
            })}
          </section>

          {demoMode ? (
            <section className="report-readiness-grid">
              <article className="panel report-readiness-card">
                <FolderCheck size={20} />
                <div>
                  <span className="workspace-eyebrow">Output checklist</span>
                  <h2>{selectedPackage.name}</h2>
                  <ul>
                    {selectedPackage.outputs.map((item) => (
                      <li key={item}><CheckCircle2 size={15} /> {item}</li>
                    ))}
                  </ul>
                </div>
              </article>
              <article className="panel report-readiness-card">
                <ShieldCheck size={20} />
                <div>
                  <span className="workspace-eyebrow">Snapshot control</span>
                  <h2>{activeReadyCount ? "Frozen and reviewable" : "Waiting for output"}</h2>
                  <p>{activeReadyCount ? "The selected package has a frozen snapshot with report sections and source trace labels." : "Generate the selected package from Upload to create the first report snapshot."}</p>
                </div>
              </article>
              <article className="panel report-readiness-card">
                <Archive size={20} />
                <div>
                  <span className="workspace-eyebrow">Archive rule</span>
                  <h2>Downloads locked in preview</h2>
                  <p>The handoff structure is visible without exposing files, URLs or backend storage paths.</p>
                </div>
              </article>
            </section>
          ) : null}

          <section className="report-queue panel">
            <div>
              <Archive size={22} />
              <div>
                <span className="workspace-eyebrow">Export queue</span>
                <h2>{demoMode ? "Preview archive behavior" : "Archive behavior"}</h2>
                <p>{demoMode ? "Downloads are locked, but the customer-facing structure is shown." : "Generated reports remain tied to their source analysis snapshot."}</p>
              </div>
            </div>
            <ShieldCheck size={28} />
          </section>
        </>
      )}
    </>
  );
}
