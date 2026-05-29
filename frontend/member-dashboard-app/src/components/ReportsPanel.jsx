import { Download, FileBarChart } from "lucide-react";
import SectionHeader from "./SectionHeader.jsx";

const statusStyles = {
  Ready: "border-emerald-400/35 bg-emerald-400/10 text-emerald-400",
  Review: "border-yellow-300/40 bg-yellow-300/10 text-yellow-300"
};

export default function ReportsPanel({ reports }) {
  return (
    <article className="db-card-light p-5">
      <SectionHeader
        eyebrow="Reporting"
        title="Report Center"
        description="Executive reports, schedule recovery files and document control exports ready for download."
        action={<button className="db-button db-button-primary" type="button">Generate report</button>}
      />
      <div className="grid gap-3">
        {reports.map((report) => (
          <div className="grid gap-3 rounded-3xl border border-slate-200/80 bg-white/60 p-4 dark:border-white/10 dark:bg-white/[0.045] md:grid-cols-[1.4fr_1fr_0.8fr_0.8fr_auto] md:items-center" key={report.name}>
            <div className="flex items-center gap-3">
              <span className="grid h-11 w-11 place-items-center rounded-2xl bg-cyan-300/12 text-cyanAccent">
                <FileBarChart size={18} />
              </span>
              <div>
                <strong className="text-slate-950 dark:text-white">{report.name}</strong>
                <p className="text-sm text-slate-500 dark:text-slate-400">{report.project}</p>
              </div>
            </div>
            <span className="text-sm text-slate-600 dark:text-slate-300">{report.type}</span>
            <span className="text-sm font-bold text-slate-700 dark:text-slate-200">{report.created}</span>
            <span className={`w-fit rounded-full border px-3 py-1 text-xs font-black ${statusStyles[report.status]}`}>{report.status}</span>
            <button className="db-button" type="button">
              <Download size={16} />
              {report.format}
            </button>
          </div>
        ))}
      </div>
    </article>
  );
}
