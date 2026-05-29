import { FileCheck2, FileClock, FileQuestion } from "lucide-react";
import SectionHeader from "./SectionHeader.jsx";

const statusStyles = {
  Approved: "border-emerald-400/35 bg-emerald-400/10 text-emerald-400",
  "Pending Review": "border-yellow-300/40 bg-yellow-300/10 text-yellow-300",
  Missing: "border-red-400/45 bg-red-400/10 text-red-300"
};

const icons = {
  Approved: FileCheck2,
  "Pending Review": FileClock,
  Missing: FileQuestion
};

export default function DocumentsPanel({ documents }) {
  return (
    <article className="db-card-light p-5">
      <SectionHeader
        eyebrow="Documents"
        title="Document Register"
        description="Track missing, pending and approved documents for project control and handover readiness."
      />
      <div className="grid gap-3">
        {documents.map((document) => {
          const Icon = icons[document.status] || FileClock;
          return (
            <div className="grid gap-3 rounded-3xl border border-slate-200/80 bg-white/60 p-4 dark:border-white/10 dark:bg-white/[0.045] md:grid-cols-[0.6fr_1.4fr_0.8fr_0.9fr_0.9fr_auto] md:items-center" key={document.code}>
              <strong className="text-cyanAccent">{document.code}</strong>
              <div>
                <strong className="text-slate-950 dark:text-white">{document.title}</strong>
                <p className="text-sm text-slate-500 dark:text-slate-400">{document.project}</p>
              </div>
              <span className="text-sm text-slate-600 dark:text-slate-300">{document.discipline}</span>
              <span className="text-sm text-slate-600 dark:text-slate-300">{document.owner}</span>
              <span className={`w-fit rounded-full border px-3 py-1 text-xs font-black ${statusStyles[document.status]}`}>
                {document.status}
              </span>
              <span className="grid h-10 w-10 place-items-center rounded-2xl bg-cyan-300/12 text-cyanAccent">
                <Icon size={17} />
              </span>
            </div>
          );
        })}
      </div>
    </article>
  );
}
