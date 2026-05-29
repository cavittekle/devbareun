import { CheckCircle2, UploadCloud } from "lucide-react";
import SectionHeader from "./SectionHeader.jsx";

export default function UploadWorkspace({ modules }) {
  return (
    <article className="db-card-light p-5">
      <SectionHeader
        eyebrow="Upload"
        title="Upload Project Files"
        description="Prepare project documents for project performance review. Backend storage can be connected to this flow later."
      />
      <div className="grid gap-4 xl:grid-cols-[1fr_0.85fr]">
        <div className="rounded-3xl border border-dashed border-cyan-300/45 bg-cyan-300/10 p-8 text-center">
          <div className="mx-auto mb-4 grid h-20 w-20 place-items-center rounded-3xl bg-cyan-300/15 text-cyanAccent">
            <UploadCloud size={34} />
          </div>
          <h3 className="text-2xl font-black text-slate-950 dark:text-white">Drag and drop project files</h3>
          <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-600 dark:text-slate-300">
            Supports PDF, XLS, XLSX, DOC, DOCX, CSV, Primavera export placeholder and MS Project export placeholder.
          </p>
          <button className="db-button db-button-primary mt-5" type="button">Select files</button>
        </div>
        <div className="grid gap-3">
          {modules.map((module) => (
            <div className="flex items-center gap-3 rounded-3xl border border-slate-200/80 bg-white/60 p-4 dark:border-white/10 dark:bg-white/[0.045]" key={module}>
              <CheckCircle2 className="text-cyanAccent" size={18} />
              <span className="font-black text-slate-950 dark:text-white">{module}</span>
            </div>
          ))}
        </div>
      </div>
    </article>
  );
}
