import { useMemo, useState } from "react";
import { ArrowRight, CheckCircle2, ClipboardList, FileSearch, Gauge, ShieldCheck, UploadCloud, Workflow } from "lucide-react";
import { uploadBinaryToSignedUrl, workspaceApi } from "../api/client";
import { analysisPackages } from "../data/packages";
import { demoWorkspace } from "../data/demoWorkspace";
import { fileSize } from "../lib/format";
import { PageHeader } from "../components/Shell";

async function sha256File(file) {
  if (!globalThis.crypto?.subtle || typeof file?.arrayBuffer !== "function") {
    throw new Error("Your browser cannot calculate the required SHA-256 file integrity check.");
  }
  const digest = await globalThis.crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return Array.from(new Uint8Array(digest)).map((item) => item.toString(16).padStart(2, "0")).join("");
}

const demoFilesByPackage = {
  "schedule-recovery": [
    { name: "baseline_schedule_demo.xer", size: 1843200, progress: 100, stage: "Sample file mapped", tone: "success" },
    { name: "actual_progress_june_demo.xlsx", size: 624000, progress: 100, stage: "Sample file mapped", tone: "success" },
    { name: "workforce_daily_log_demo.xlsx", size: 348000, progress: 100, stage: "Sample file mapped", tone: "success" }
  ],
  "cost-control": [
    { name: "boq_cost_plan_demo.xlsx", size: 734000, progress: 100, stage: "Sample file mapped", tone: "success" },
    { name: "actual_cost_june_demo.xlsx", size: 512400, progress: 100, stage: "Sample file mapped", tone: "success" },
    { name: "f2_payment_certificate_demo.pdf", size: 392000, progress: 100, stage: "Sample file mapped", tone: "success" }
  ],
  "material-continuity": [
    { name: "material_boq_demo.xlsx", size: 684000, progress: 100, stage: "Sample file mapped", tone: "success" },
    { name: "stock_records_demo.xlsx", size: 348000, progress: 100, stage: "Sample file mapped", tone: "success" },
    { name: "procurement_updates_demo.csv", size: 126000, progress: 100, stage: "Sample file mapped", tone: "success" }
  ],
  "risk-decisions": [
    { name: "risk_register_demo.xlsx", size: 244000, progress: 100, stage: "Sample file mapped", tone: "success" },
    { name: "decision_log_demo.xlsx", size: 188000, progress: 100, stage: "Sample file mapped", tone: "success" },
    { name: "site_notes_demo.pdf", size: 418000, progress: 100, stage: "Sample file mapped", tone: "success" }
  ]
};

const demoMappingByPackage = {
  "schedule-recovery": [
    { label: "Baseline logic", source: "Primavera XER", confidence: 96, note: "Activities, dates and critical path detected." },
    { label: "Progress evidence", source: "June progress sheet", confidence: 92, note: "Planned vs actual progress mapped by building." },
    { label: "Workforce signal", source: "Daily manpower log", confidence: 88, note: "Crew availability linked to recovery actions." }
  ],
  "cost-control": [
    { label: "BOQ baseline", source: "Cost plan workbook", confidence: 95, note: "Budget packages and remaining value mapped." },
    { label: "Actual cost", source: "Posted cost sheet", confidence: 91, note: "Committed and actual cost rows aligned." },
    { label: "Payment evidence", source: "F-2 certificate", confidence: 86, note: "Certified payment trend prepared for review." }
  ],
  "material-continuity": [
    { label: "Material demand", source: "Material BOQ", confidence: 94, note: "Required quantities grouped by critical item." },
    { label: "Stock position", source: "Warehouse records", confidence: 89, note: "Coverage days and shortage flags calculated." },
    { label: "Inbound supply", source: "Procurement update", confidence: 84, note: "Supplier lane dates linked to continuity risk." }
  ],
  "risk-decisions": [
    { label: "Risk register", source: "Risk workbook", confidence: 93, note: "Probability, impact and owners detected." },
    { label: "Decision log", source: "Decision records", confidence: 90, note: "Overdue approvals surfaced for escalation." },
    { label: "Site notes", source: "Supporting PDF", confidence: 78, note: "Narrative notes retained as review evidence." }
  ]
};

const demoOutputByPackage = {
  "schedule-recovery": ["Delay dashboard", "Critical activities", "Recovery actions", "Source traceability"],
  "cost-control": ["Commercial control board", "Payment trend", "Cost package grid", "Decision queue"],
  "material-continuity": ["Supply continuity board", "Supplier lanes", "Material shortage grid", "Procurement actions"],
  "risk-decisions": ["Decision command board", "Risk matrix", "Overdue decisions", "Management moves"]
};

function demoFileStates(packageId) {
  return demoFilesByPackage[packageId] || demoFilesByPackage["schedule-recovery"];
}

export function Upload({ onUploaded, demoMode = false, initialPackage = analysisPackages[0].id }) {
  const safeInitialPackage = analysisPackages.some((item) => item.id === initialPackage) ? initialPackage : analysisPackages[0].id;
  const [selectedPackage, setSelectedPackage] = useState(safeInitialPackage);
  const [projectName, setProjectName] = useState(demoMode ? demoWorkspace.projects[0].project_name : "");
  const [files, setFiles] = useState([]);
  const [fileStates, setFileStates] = useState(demoMode ? demoFileStates(safeInitialPackage) : []);
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const selected = useMemo(
    () => analysisPackages.find((item) => item.id === selectedPackage) || analysisPackages[0],
    [selectedPackage]
  );
  const packageInsight = demoWorkspace.packageInsights?.[selectedPackage];
  const demoMappingRows = demoMappingByPackage[selectedPackage] || demoMappingByPackage["schedule-recovery"];
  const demoOutputs = demoOutputByPackage[selectedPackage] || demoOutputByPackage["schedule-recovery"];

  function handleFiles(event) {
    const nextFiles = Array.from(event.target.files || []);
    setFiles(nextFiles);
    setFileStates(nextFiles.map((file) => ({
      name: file.name,
      size: file.size,
      progress: 0,
      stage: "Ready",
      tone: "info"
    })));
    setStatus(null);
  }

  function choosePackage(packageId) {
    setSelectedPackage(packageId);
    if (demoMode) {
      setFiles([]);
      setFileStates(demoFileStates(packageId));
      setStatus(null);
    }
  }

  function patchFileState(index, patch) {
    setFileStates((current) => current.map((item, itemIndex) => (
      itemIndex === index ? { ...item, ...patch } : item
    )));
  }

  async function startAnalysis(event) {
    event.preventDefault();
    if (demoMode) {
      setFileStates((current) => (current.length ? current : demoFileStates(selectedPackage)).map((file) => ({
        ...file,
        progress: 100,
        stage: "Sample analysis ready",
        tone: "success"
      })));
      setStatus({
        type: "success",
        text: "Sample analysis is ready. Open the dashboard to review the project-control output."
      });
      onUploaded?.(demoWorkspace.projects[0], selectedPackage);
      return;
    }
    if (!projectName.trim()) {
      setStatus({ type: "error", text: "Project name is required." });
      return;
    }
    if (!files.length) {
      setStatus({ type: "error", text: "Choose at least one project file before starting analysis." });
      return;
    }
    setBusy(true);
    setStatus({ type: "info", text: "Creating project workspace..." });
    try {
      const projectResponse = await workspaceApi.createProject({
        project_name: projectName.trim(),
        project_status: "uploading",
        analysis_type: selected.name
      });
      const project = projectResponse?.project;
      const projectId = project?.project_id || project?.id;
      if (!projectId) {
        throw new Error("Project was created, but no project id was returned.");
      }
      const uploadedFileIds = [];
      for (const [index, file] of files.entries()) {
        patchFileState(index, { stage: "Verifying file integrity", progress: 3, tone: "info" });
        const checksum = await sha256File(file);
        patchFileState(index, { stage: "Requesting secure upload URL", progress: 5, tone: "info" });
        const uploadResponse = await workspaceApi.createUploadUrl({
          project_id: projectId,
          filename: file.name,
          mime_type: file.type || "application/octet-stream",
          size_bytes: file.size,
          checksum
        });
        const signedUrl = uploadResponse?.signed_upload_url || uploadResponse?.upload?.signed_upload_url || uploadResponse?.upload?.signedUrl || uploadResponse?.upload?.signedURL || uploadResponse?.upload?.url;
        const fileId = uploadResponse?.file_id || uploadResponse?.upload_id || uploadResponse?.file?.file_id || uploadResponse?.file?.id;
        const storagePath = uploadResponse?.storage_path || uploadResponse?.file?.storage_path;
        patchFileState(index, { stage: signedUrl ? "Uploading file" : "Recording local upload metadata", progress: signedUrl ? 10 : 90, tone: "info" });
        await uploadBinaryToSignedUrl(signedUrl, file, (progress) => {
          patchFileState(index, { progress: Math.max(10, Math.min(95, progress)), stage: "Uploading file" });
        });
        const uploadedRecord = await workspaceApi.markUploaded({
          upload_id: uploadResponse?.upload_id || fileId,
          file_id: fileId,
          project_id: projectId,
          storage_path: storagePath,
          uploaded: true,
          checksum
        });
        uploadedFileIds.push(fileId);
        const scanStatus = uploadedRecord?.file?.security_scan_status || "pending";
        patchFileState(index, { stage: scanStatus === "pending" ? "Uploaded - queued for security screening" : "Uploaded", progress: 100, tone: "success" });
      }
      setStatus({ type: "info", text: "Files uploaded. The worker will verify file integrity and run content security screening before parser execution." });
      const analysisResponse = await workspaceApi.createAnalysis({
        project_id: projectId,
        uploaded_file_ids: uploadedFileIds.filter(Boolean),
        analysis_type: selected.id,
        package_name: selected.name
      });
      const jobId = analysisResponse?.job_id || analysisResponse?.job?.id;
      setStatus({
        type: "success",
        text: `Upload is complete. Analysis job${jobId ? ` ${jobId}` : ""} is queued and the dashboard will show only detected sections.`
      });
      onUploaded?.(project);
    } catch (error) {
      setStatus({
        type: "error",
        text: error.message || "Upload flow could not start. Check backend and session configuration."
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Guided upload"
        title={demoMode ? "Upload package and mapping preview." : "Choose the problem, then upload the right files."}
        description={demoMode ? "These local sample files demonstrate how the upload workspace looks before a real backend run." : "The workspace shows only relevant dashboard sections after real project data is uploaded and mapped."}
      />

      <form className="upload-layout" onSubmit={startAnalysis}>
        <section className="panel">
          <h2>Analysis package</h2>
          <div className="package-grid">
            {analysisPackages.map((item) => (
              <button
                key={item.id}
                type="button"
                className={item.id === selectedPackage ? "package-card active" : "package-card"}
                onClick={() => choosePackage(item.id)}
              >
                <small>{item.name}</small>
                <strong>{item.label}</strong>
              </button>
            ))}
          </div>
          <div className="guide-grid">
            <article>
              <h3>Required files</h3>
              <ol>
                {selected.files.map((item) => <li key={item}>{item}</li>)}
              </ol>
            </article>
            <article>
              <h3>You will receive</h3>
              <ul>
                {selected.outputs.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </article>
          </div>
          {demoMode ? (
            <div className="upload-demo-command">
              <div>
                <span className="workspace-eyebrow">Package logic preview</span>
                <h3>{selected.name}</h3>
                <p>{packageInsight?.signal}</p>
              </div>
              <strong>{packageInsight?.metric}</strong>
              <small>{packageInsight?.metricLabel}</small>
            </div>
          ) : null}
        </section>

        <section className="panel">
          <label className="field-label">
            Project name
            <input value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="Example: Residential Tower A" />
          </label>
          <label className="upload-zone">
            <UploadCloud size={36} />
            <strong>Drop project files here, or choose files</strong>
            <span>Excel, CSV, PDF, Primavera XER, MS Project XML and supporting images.</span>
            <input type="file" multiple onChange={handleFiles} />
          </label>
          {demoMode ? (
            <div className="upload-stage-rail">
              <article>
                <FileSearch size={18} />
                <strong>Screen</strong>
                <span>File names, size and type are checked.</span>
              </article>
              <ArrowRight size={17} />
              <article>
                <Workflow size={18} />
                <strong>Map</strong>
                <span>Evidence is matched to package logic.</span>
              </article>
              <ArrowRight size={17} />
              <article>
                <Gauge size={18} />
                <strong>Score</strong>
                <span>Dashboard sections are selected.</span>
              </article>
            </div>
          ) : null}
          {fileStates.length > 0 && (
            <div className="file-list">
              {fileStates.map((file, index) => (
                <article key={`${file.name}-${file.size}-${index}`} className={`file-state ${file.tone}`}>
                  <div>
                    <strong>{file.name}</strong>
                    <span>{file.stage}</span>
                  </div>
                  <div className="file-progress" aria-label={`${file.progress}% uploaded`}>
                    <span style={{ width: `${file.progress}%` }} />
                  </div>
                  <small>{fileSize(file.size)}</small>
                </article>
              ))}
            </div>
          )}
          {demoMode ? (
            <>
              <div className="upload-mapping-grid">
                {demoMappingRows.map((row) => (
                  <article className="upload-mapping-card" key={row.label}>
                    <div>
                      <ClipboardList size={17} />
                      <span>{row.source}</span>
                    </div>
                    <strong>{row.label}</strong>
                    <p>{row.note}</p>
                    <div className="upload-confidence">
                      <i style={{ width: `${row.confidence}%` }} />
                    </div>
                    <small>{row.confidence}% mapping confidence</small>
                  </article>
                ))}
              </div>
              <div className="upload-output-board">
                <div>
                  <ShieldCheck size={19} />
                  <strong>Output readiness</strong>
                  <span>Sample files are already mapped, so Start Analysis opens the selected dashboard.</span>
                </div>
                <ul>
                  {demoOutputs.map((item) => (
                    <li key={item}><CheckCircle2 size={15} /> {item}</li>
                  ))}
                </ul>
              </div>
            </>
          ) : null}
          {status && <div className={`status-box ${status.type}`}>{status.text}</div>}
          <button className="primary-button full" type="submit" disabled={busy}>
            {busy ? "Preparing analysis..." : "Start Analysis"}
          </button>
        </section>
      </form>
    </>
  );
}
