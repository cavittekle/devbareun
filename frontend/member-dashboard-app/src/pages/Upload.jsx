import { useMemo, useState } from "react";
import { Download, FileSpreadsheet, UploadCloud } from "lucide-react";
import { uploadBinaryToSignedUrl, workspaceApi } from "../api/client";
import { DELAY_TEMPLATE_URL, analysisPackages } from "../data/packages";
import { LangToggle, useDelayLang } from "../components/DelayDashboard";
import { fileSize } from "../lib/format";
import { PageHeader } from "../components/Shell";

async function sha256File(file) {
  if (!globalThis.crypto?.subtle || typeof file?.arrayBuffer !== "function") {
    throw new Error("Your browser cannot calculate the required SHA-256 file integrity check.");
  }
  const digest = await globalThis.crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return Array.from(new Uint8Array(digest)).map((item) => item.toString(16).padStart(2, "0")).join("");
}

const COPY = {
  az: {
    eyebrow: "İcra və gecikmə analizi",
    title: "İş qrafikini və faktiki icranı yükləyin.",
    description: "DevBareun plan və faktiki icranı müqayisə edir, gecikməni gün ilə, proqnoz bitmə tarixini, kritik yolu və gecikmənin məsuliyyətini hesablayır.",
    step1: "1. Şablonu doldurun və ya iş qrafiki ixracınızı hazırlayın",
    template: "Excel şablonunu yüklə",
    example: "Nümunə hesabata bax",
    need: "Lazım olan məlumat",
    receive: "Alacağınız nəticə",
    files: ["Plan iş qrafiki (hər iş üçün plan başlanğıc və bitiş)", "Faktiki icra (faktiki tarixlər və icra %)", "Gecikmə hadisələri və məsul tərəf (istəyə bağlı)", "Və ya Primavera XER / MS Project XML faylı"],
    outputs: ["Plan və faktiki S-əyrisi, SPI", "Gecikmə günləri və proqnoz bitmə tarixi", "Kritik yol və ən çox gecikən işlər", "Sifarişçi / podratçı / neytral gecikmə bölgüsü", "PDF və Excel icra hesabatı (AZ / EN)"],
    step2: "2. Layihəni yaradın və faylları yükləyin",
    projectName: "Layihənin adı",
    placeholder: "Məsələn: Baku Business Center",
    drop: "Faylları bura atın və ya seçin",
    formats: "Excel (.xlsx, .xls), CSV, Primavera XER, MS Project XML. Digər sənədlər (PDF, şəkil) əlavə material kimi saxlanır.",
    start: "Analizi başlat",
    busy: "Analiz hazırlanır...",
    nameRequired: "Layihənin adı tələb olunur.",
    fileRequired: "Analiz üçün ən azı bir fayl seçin.",
    queued: "Fayllar yükləndi və analiz növbəyə alındı.",
    open: "Nəticəni aç"
  },
  en: {
    eyebrow: "Execution and delay analysis",
    title: "Upload the schedule and the actual progress.",
    description: "DevBareun compares plan and actual execution and calculates delay in days, forecast completion, the critical path and who is responsible for the delay.",
    step1: "1. Fill in the template or prepare your schedule export",
    template: "Download Excel template",
    example: "See an example report",
    need: "What you need",
    receive: "What you receive",
    files: analysisPackages[0].files,
    outputs: analysisPackages[0].outputs,
    step2: "2. Create the project and upload files",
    projectName: "Project name",
    placeholder: "Example: Residential Tower A",
    drop: "Drop files here, or choose files",
    formats: "Excel (.xlsx, .xls), CSV, Primavera XER, MS Project XML. Other documents (PDF, images) are kept as supporting files.",
    start: "Start analysis",
    busy: "Preparing analysis...",
    nameRequired: "Project name is required.",
    fileRequired: "Choose at least one file to analyse.",
    queued: "Files uploaded and the analysis is queued.",
    open: "Open result"
  }
};

export function Upload({ onUploaded }) {
  const [lang, setLang] = useDelayLang();
  const copy = COPY[lang];
  const [resultProjectId, setResultProjectId] = useState(null);
  const selectedPackage = analysisPackages[0].id;
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
      setStatus({ type: "error", text: copy.nameRequired });
      return;
    }
    if (!files.length) {
      setStatus({ type: "error", text: copy.fileRequired });
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
      setStatus({ type: "success", text: `${copy.queued}${jobId ? ` (${jobId})` : ""}` });
      setResultProjectId(projectId);
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
        eyebrow={copy.eyebrow}
        title={copy.title}
        description={copy.description}
        action={<LangToggle lang={lang} onChange={setLang} />}
      />

      <form className="upload-layout" onSubmit={startAnalysis}>
        <section className="panel">
          <h2>{copy.step1}</h2>
          <div className="delay-upload-links">
            <a className="primary-button" href={DELAY_TEMPLATE_URL} download><Download size={16} /> {copy.template}</a>
            <a className="secondary-button" href="/workspace/?view=example"><FileSpreadsheet size={16} /> {copy.example}</a>
          </div>
          <div className="guide-grid">
            <article>
              <h3>{copy.need}</h3>
              <ol>
                {copy.files.map((item) => <li key={item}>{item}</li>)}
              </ol>
            </article>
            <article>
              <h3>{copy.receive}</h3>
              <ul>
                {copy.outputs.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </article>
          </div>
        </section>

        <section className="panel">
          <h2>{copy.step2}</h2>
          <label className="field-label">
            {copy.projectName}
            <input value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder={copy.placeholder} />
          </label>
          <label className="upload-zone">
            <UploadCloud size={36} />
            <strong>{copy.drop}</strong>
            <span>{copy.formats}</span>
            <input type="file" multiple accept=".xlsx,.xlsm,.xls,.csv,.xer,.xml,.pdf,.png,.jpg,.jpeg,.webp" onChange={handleFiles} />
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
          {resultProjectId && (
            <a className="secondary-button full" href={`/workspace/?view=result&project_id=${encodeURIComponent(resultProjectId)}`}>{copy.open}</a>
          )}
          <button className="primary-button full" type="submit" disabled={busy}>
            {busy ? copy.busy : copy.start}
          </button>
        </section>
      </form>
    </>
  );
}
