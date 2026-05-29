import { FileCheck2, FileClock, FileQuestion, Files, UploadCloud } from "lucide-react";

export default function DocumentSummary({ summary }) {
  const items = [
    { label: "Uploaded Files", value: summary.uploadedFiles, icon: Files, tone: "text-cyanAccent" },
    { label: "Pending Review", value: summary.pendingReview, icon: FileClock, tone: "text-yellow-300" },
    { label: "Approved Documents", value: summary.approvedDocuments, icon: FileCheck2, tone: "text-emerald-400" },
    { label: "Missing Documents", value: summary.missingDocuments, icon: FileQuestion, tone: "text-red-300" }
  ];

  return (
    <article className="db-card-light p-5">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <p className="db-pill mb-2">Document Control</p>
          <h2 className="text-xl font-black text-slate-950 dark:text-white">File review summary</h2>
        </div>
        <button className="db-button db-button-primary shrink-0" type="button">
          <UploadCloud size={17} />
          Upload Project Files
        </button>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <div className="rounded-3xl border border-slate-200/80 bg-white/60 p-4 dark:border-white/10 dark:bg-white/[0.045]" key={item.label}>
              <Icon className={item.tone} size={20} />
              <strong className="mt-3 block text-2xl font-black text-slate-950 dark:text-white">{item.value}</strong>
              <p className="mt-1 text-xs font-black uppercase tracking-[0.1em] text-slate-500 dark:text-slate-400">{item.label}</p>
            </div>
          );
        })}
      </div>
    </article>
  );
}
