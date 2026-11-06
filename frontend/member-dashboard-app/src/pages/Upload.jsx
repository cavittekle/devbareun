import { Fragment, useMemo, useState } from "react";
import { AlertTriangle, CalendarRange, Check, CreditCard, FileSignature, FileSpreadsheet, Receipt, X } from "lucide-react";
import { uploadBinaryToSignedUrl, workspaceApi } from "../api/client";
import { analysisPackages } from "../data/packages";
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

// Accepted formats per document type; mirrors backend/app/document_types.py.
export const DOCUMENT_TYPES = [
  { id: "schedule", icon: CalendarRange, accept: [".xlsx", ".xls", ".xlsm", ".csv", ".xer", ".xml", ".mpp", ".pdf"], required: true },
  { id: "f2", icon: Receipt, accept: [".xlsx", ".xls", ".xlsm", ".csv", ".docx", ".doc", ".pdf"], required: true },
  { id: "contract", icon: FileSignature, accept: [".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".webp"], required: true }
];
const READABLE_SCHEDULE = [".xlsx", ".xls", ".xlsm", ".csv", ".xer", ".xml"];

function extension(name) {
  const match = /\.[^.]+$/.exec(name || "");
  return match ? match[0].toLowerCase() : "";
}

const COPY = {
  az: {
    eyebrow: "İcra və gecikmə analizi",
    title: "Yeni gecikmə analizi",
    description: "Planlamanı, cari F2 və F3 aktlarını və müqaviləni yükləyin. DevBareun plan və faktiki icranı müqayisə edir, gecikməni gün ilə, proqnoz bitmə tarixini, kritik yolu və gecikmənin məsuliyyətini hesablayır.",
    step1: "İş qrafikinizi və sənədlərinizi hazırlayın",
    example: "Nümunə hesabata bax",
    need: "Lazım olan məlumat",
    receive: "Alacağınız nəticə",
    files: ["Planlama: plan iş qrafiki və faktiki icra (Excel, Primavera XER, MS Project)", "Cari F2 və F3 aktları (Excel, Word və ya PDF)", "Müqavilə (PDF, Word, JPEG və ya PNG)", "Gecikmə hadisələri və məsul tərəf (istəyə bağlı)"],
    outputs: ["Plan və faktiki S-əyrisi, SPI", "Gecikmə günləri və proqnoz bitmə tarixi", "Kritik yol və ən çox gecikən işlər", "Sifarişçi / podratçı / neytral gecikmə bölgüsü", "F2 üzrə ödənilmiş məbləğ fiziki icra ilə müqayisədə", "PDF və Excel icra hesabatı (AZ / EN)"],
    step2: "Layihəni yaradın və faylları yükləyin",
    projectName: "Layihənin adı",
    placeholder: "Məsələn: Baku Business Center",
    types: {
      contract: { title: "Müqavilə", formats: "PDF, Word (.doc, .docx), JPEG, PNG (.jpg, .png)", hint: "Hesabata istinad kimi əlavə olunur." },
      schedule: { title: "Planlama", formats: "Excel, CSV, Primavera XER, MS Project (.xml, .mpp), PDF", hint: "Hesablama Excel, XER və ya MS Project XML-dən aparılır. PDF və .mpp istinad kimi saxlanılır." },
      f2: { title: "Cari F2 və F3 aktları", formats: "Excel (.xlsx, .xls), CSV, Word (.docx, .doc), PDF", hint: "Dövr və məbləğ oxunur, fiziki icra ilə müqayisə edilir." }
    },
    required: "Tələb olunur",
    optional: "İstəyə bağlı",
    choose: "Fayl seçin",
    selected: (count) => `${count} fayl seçildi`,
    remove: "Sil",
    wrongFormat: (name, type) => `${name}: bu format ${type} üçün qəbul edilmir.`,
    scheduleUnreadable: "Planlama yalnız PDF/.mpp-dir: hesablama üçün Excel, XER və ya MS Project XML faylı da əlavə edin.",
    start: "Analizi başlat",
    busy: "Analiz hazırlanır...",
    nameRequired: "Layihənin adı tələb olunur.",
    queued: "Fayllar yükləndi və analiz növbəyə alındı.",
    open: "Nəticəni aç",
    extras: "Əlavə sənədlər (istəyə bağlı)",
    noCreditsTitle: "Analiz üçün aktiv plan lazımdır",
    noCreditsText: "Bu iş sahəsində analiz krediti qalmayıb. Faylları indi hazırlaya bilərsiniz, analizi başlatmaq üçün əvvəlcə plan seçin.",
    choosePlan: "Plan seçin",
    stages: { ready: "Hazırdır", verifying: "Fayl yoxlanılır", requesting: "Təhlükəsiz yükləmə hazırlanır", uploading: "Yüklənir", recording: "Qeyd edilir", queued: "Yükləndi, yoxlama növbəsindədir", done: "Yükləndi" },
    missing: (names) => `Analizə başlamaq üçün çatışmayan faylları əlavə edin: ${names}.`,
    creating: "Layihə yaradılır...",
    uploadedChecking: "Fayllar yükləndi. Onları yoxlayır və analizi aparırıq. Bu adətən 1–2 dəqiqə çəkir.",
    uploadFailed: "Yükləmə başlamadı. Bir az sonra yenidən cəhd edin; problem qalarsa info@devbareun.com ünvanına yazın."
  },
  en: {
    eyebrow: "Execution and delay analysis",
    title: "New delay analysis",
    description: "Upload the schedule, the current F2 and F3 certificates and the contract. DevBareun compares plan and actual execution and calculates delay in days, forecast completion, the critical path and who is responsible for the delay.",
    step1: "Prepare your schedule and documents",
    example: "See an example report",
    need: "What you need",
    receive: "What you receive",
    files: analysisPackages[0].files,
    outputs: analysisPackages[0].outputs,
    types: {
      contract: { title: "Contract", formats: "PDF, Word (.doc, .docx), JPEG, PNG (.jpg, .png)", hint: "Attached to the report as a reference." },
      schedule: { title: "Schedule (plan and actual)", formats: "Excel, CSV, Primavera XER, MS Project (.xml, .mpp), PDF", hint: "Calculated from Excel, XER or MS Project XML. PDF and .mpp are kept as a reference." },
      f2: { title: "Current F2 and F3 certificates", formats: "Excel (.xlsx, .xls), CSV, Word (.docx, .doc), PDF", hint: "Period and amount are read and compared with physical progress." }
    },
    required: "Required",
    optional: "Optional",
    choose: "Choose files",
    selected: (count) => `${count} file${count === 1 ? "" : "s"} selected`,
    remove: "Remove",
    wrongFormat: (name, type) => `${name}: this format is not accepted for ${type}.`,
    scheduleUnreadable: "The schedule is only PDF/.mpp: add an Excel, XER or MS Project XML file for the calculation.",
    step2: "Create the project and upload files",
    projectName: "Project name",
    placeholder: "Example: Residential Tower A",
    start: "Start analysis",
    busy: "Preparing analysis...",
    nameRequired: "Project name is required.",
    queued: "Files uploaded and the analysis is queued.",
    open: "Open result",
    extras: "Supporting documents (optional)",
    noCreditsTitle: "An active plan is needed to run the analysis",
    noCreditsText: "This workspace has no analysis credits left. You can prepare your files now; choose a plan before starting the analysis.",
    choosePlan: "Choose a plan",
    stages: { ready: "Ready", verifying: "Checking file", requesting: "Preparing secure upload", uploading: "Uploading", recording: "Saving", queued: "Uploaded, waiting for the check", done: "Uploaded" },
    missing: (names) => `Add the missing files to start: ${names}.`,
    creating: "Creating the project...",
    uploadedChecking: "Files uploaded. We're checking them and running the analysis. This usually takes 1–2 minutes.",
    uploadFailed: "The upload could not start. Try again in a minute; if it keeps failing, write to info@devbareun.com."
  }
};

export function Upload({ onUploaded, credits, onNavigate }) {
  const [lang, setLang] = useDelayLang();
  const copy = COPY[lang];
  const [resultProjectId, setResultProjectId] = useState(null);
  const selectedPackage = analysisPackages[0].id;
  const [projectName, setProjectName] = useState("");
  const [files, setFiles] = useState([]);
  const [fileStates, setFileStates] = useState([]);
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  // Credits are only known once /api/credits/status answered; unknown never blocks.
  const noCredits = credits != null && Number(credits.remaining ?? 0) <= 0;
  const selected = useMemo(
    () => analysisPackages.find((item) => item.id === selectedPackage) || analysisPackages[0],
    [selectedPackage]
  );

  function addFiles(typeId, event) {
    const type = DOCUMENT_TYPES.find((item) => item.id === typeId);
    const chosen = Array.from(event.target.files || []);
    event.target.value = "";
    const accepted = chosen.filter((file) => type.accept.includes(extension(file.name)));
    const rejected = chosen.filter((file) => !accepted.includes(file));
    const nextFiles = [...files, ...accepted.map((file) => ({ file, type: typeId }))];
    setFiles(nextFiles);
    setFileStates(nextFiles.map(({ file, type: fileType }) => ({
      name: file.name,
      size: file.size,
      type: fileType,
      progress: 0,
      stage: "ready",
      tone: "info"
    })));
    setStatus(rejected.length
      ? { type: "error", text: rejected.map((file) => copy.wrongFormat(file.name, copy.types[typeId].title)).join(" ") }
      : null);
  }

  function removeFile(index) {
    setFiles((current) => current.filter((_, itemIndex) => itemIndex !== index));
    setFileStates((current) => current.filter((_, itemIndex) => itemIndex !== index));
  }

  function patchFileState(index, patch) {
    setFileStates((current) => current.map((item, itemIndex) => (
      itemIndex === index ? { ...item, ...patch } : item
    )));
  }

  async function startAnalysis(event) {
    event.preventDefault();
    if (noCredits) {
      onNavigate?.("billing");
      return;
    }
    if (!projectName.trim()) {
      setStatus({ type: "error", text: copy.nameRequired });
      return;
    }
    const missing = DOCUMENT_TYPES
      .filter((type) => type.required && !files.some((item) => item.type === type.id))
      .map((type) => copy.types[type.id].title);
    if (missing.length) {
      setStatus({ type: "error", text: copy.missing(missing.join(", ")) });
      return;
    }
    const schedules = files.filter((item) => item.type === "schedule");
    if (!schedules.some((item) => READABLE_SCHEDULE.includes(extension(item.file.name)))) {
      setStatus({ type: "error", text: copy.scheduleUnreadable });
      return;
    }
    setBusy(true);
    setStatus({ type: "info", text: copy.creating });
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
      for (const [index, { file, type: documentType }] of files.entries()) {
        patchFileState(index, { stage: "verifying", progress: 3, tone: "info" });
        const checksum = await sha256File(file);
        patchFileState(index, { stage: "requesting", progress: 5, tone: "info" });
        const uploadResponse = await workspaceApi.createUploadUrl({
          project_id: projectId,
          filename: file.name,
          mime_type: file.type || "application/octet-stream",
          size_bytes: file.size,
          checksum,
          document_type: documentType
        });
        const signedUrl = uploadResponse?.signed_upload_url || uploadResponse?.upload?.signed_upload_url || uploadResponse?.upload?.signedUrl || uploadResponse?.upload?.signedURL || uploadResponse?.upload?.url;
        const fileId = uploadResponse?.file_id || uploadResponse?.upload_id || uploadResponse?.file?.file_id || uploadResponse?.file?.id;
        const storagePath = uploadResponse?.storage_path || uploadResponse?.file?.storage_path;
        patchFileState(index, { stage: signedUrl ? "uploading" : "recording", progress: signedUrl ? 10 : 90, tone: "info" });
        await uploadBinaryToSignedUrl(signedUrl, file, (progress) => {
          patchFileState(index, { progress: Math.max(10, Math.min(95, progress)), stage: "uploading" });
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
        patchFileState(index, { stage: scanStatus === "pending" ? "queued" : "done", progress: 100, tone: "success" });
      }
      setStatus({ type: "info", text: copy.uploadedChecking });
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
        text: error.message || copy.uploadFailed
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
        compact
      />

      {noCredits && (
        <div className="status-box warning upload-plan-notice" role="status">
          <AlertTriangle size={18} aria-hidden="true" />
          <div>
            <strong>{copy.noCreditsTitle}</strong>
            <span>{copy.noCreditsText}</span>
          </div>
          <button type="button" className="secondary-button" onClick={() => onNavigate?.("billing")}>
            <CreditCard size={16} /> {copy.choosePlan}
          </button>
        </div>
      )}

      <form className="upload-layout" onSubmit={startAnalysis}>
        <section className="panel upload-guide">
          <h2 className="step-title"><span className="step-badge">1</span>{copy.step1}</h2>
          <div className="delay-upload-links">
            <a className="text-button" href="/workspace/?view=example"><FileSpreadsheet size={16} /> {copy.example}</a>
          </div>
          <div className="guide-stack">
            <article>
              <h3>{copy.need}</h3>
              <ol className="guide-steps">
                {copy.files.map((item) => <li key={item}>{item}</li>)}
              </ol>
            </article>
            <article>
              <h3>{copy.receive}</h3>
              <ul className="guide-checks">
                {copy.outputs.map((item) => <li key={item}><Check size={15} aria-hidden="true" />{item}</li>)}
              </ul>
            </article>
          </div>
        </section>

        <section className="panel upload-form">
          <h2 className="step-title"><span className="step-badge">2</span>{copy.step2}</h2>
          <label className="field-label">
            {copy.projectName}
            <input value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder={copy.placeholder} aria-required="true" />
          </label>
          <div className="doc-zones">
            {DOCUMENT_TYPES.map((type) => {
              const Icon = type.icon;
              const text = copy.types[type.id];
              const count = files.filter((item) => item.type === type.id).length;
              const firstOptional = !type.required && DOCUMENT_TYPES.find((item) => !item.required)?.id === type.id;
              return (
                <Fragment key={type.id}>
                {firstOptional && <span className="doc-zones-heading">{copy.extras}</span>}
                <label className={count ? "upload-zone doc-zone has-files" : "upload-zone doc-zone"}>
                  <Icon size={28} />
                  <span className="doc-zone-title">
                    <strong>{text.title}</strong>
                    <em className={type.required ? "doc-tag required" : "doc-tag"}>{type.required ? copy.required : copy.optional}</em>
                  </span>
                  <span className="doc-zone-formats" id={`doc-formats-${type.id}`}>{text.formats}</span>
                  <small id={`doc-hint-${type.id}`}>{text.hint}</small>
                  <span className="secondary-button doc-choose">{count ? copy.selected(count) : copy.choose}</span>
                  <input type="file" multiple accept={type.accept.join(",")} aria-required={type.required ? "true" : undefined} aria-describedby={`doc-formats-${type.id} doc-hint-${type.id}`} onChange={(event) => addFiles(type.id, event)} />
                </label>
                </Fragment>
              );
            })}
          </div>
          {fileStates.length > 0 && (
            <div className="file-list">
              {fileStates.map((file, index) => (
                <article key={`${file.name}-${file.size}-${index}`} className={`file-state ${file.tone}`}>
                  <div>
                    <strong>{file.name}</strong>
                    <span>{copy.types[file.type]?.title} · {copy.stages[file.stage] || file.stage}</span>
                  </div>
                  <div className="file-progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={file.progress} aria-label={file.name}>
                    <span style={{ width: `${file.progress}%` }} />
                  </div>
                  <small>{fileSize(file.size)}</small>
                  {!busy && file.progress === 0 && (
                    <button type="button" className="icon-button" aria-label={`${copy.remove} ${file.name}`} onClick={() => removeFile(index)}><X size={14} /></button>
                  )}
                </article>
              ))}
            </div>
          )}
          <div role={status?.type === "error" ? "alert" : "status"} aria-live={status?.type === "error" ? "assertive" : "polite"}>
            {status && <div className={`status-box ${status.type}`}>{status.text}</div>}
          </div>
          {resultProjectId && (
            <a className="secondary-button full" href={`/workspace/?view=result&project_id=${encodeURIComponent(resultProjectId)}`}>{copy.open}</a>
          )}
          <button className="primary-button full" type="submit" disabled={busy}>
            {busy ? copy.busy : noCredits ? copy.choosePlan : copy.start}
          </button>
        </section>
      </form>
    </>
  );
}
