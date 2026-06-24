import { useMemo, useState } from "react";
import { UploadCloud } from "lucide-react";
import { uploadBinaryToSignedUrl, workspaceApi } from "../api/client";
import { analysisPackages } from "../data/packages";
import { fileSize } from "../lib/format";
import { PageHeader } from "../components/Shell";

async function sha256File(file) {
  if (!globalThis.crypto?.subtle || typeof file?.arrayBuffer !== "function") {
    throw new Error("Your browser cannot calculate the required SHA-256 file integrity check.");
  }
  const digest = await globalThis.crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return Array.from(new Uint8Array(digest)).map((item) => item.toString(16).padStart(2, "0")).join("");
}

export function Upload({ onUploaded }) {
  const [selectedPackage, setSelectedPackage] = useState(analysisPackages[0].id);
  const [projectName, setProjectName] = useState("");
  const [files, setFiles] = useState([]);
  const [fileStates, setFileStates] = useState([]);
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const selected = useMemo(
    () => analysisPackages.find((item) => item.id === selectedPackage) || analysisPackages[0],
    [selectedPackage]
  );

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

  function patchFileState(index, patch) {
    setFileStates((current) => current.map((item, itemIndex) => (
      itemIndex === index ? { ...item, ...patch } : item
    )));
  }

  async function startAnalysis(event) {
    event.preventDefault();
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
        patchFileState(index, { stage: scanStatus === "pending" ? "Uploaded — queued for security screening" : "Uploaded", progress: 100, tone: "success" });
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
        title="Choose the problem, then upload the right files."
        description="The workspace shows only relevant dashboard sections after real project data is uploaded and mapped."
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
                onClick={() => setSelectedPackage(item.id)}
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
          {status && <div className={`status-box ${status.type}`}>{status.text}</div>}
          <button className="primary-button full" type="submit" disabled={busy}>
            {busy ? "Preparing analysis..." : "Start Analysis"}
          </button>
        </section>
      </form>
    </>
  );
}
