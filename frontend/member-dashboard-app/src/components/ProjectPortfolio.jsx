import { ArrowRight, Building2 } from "lucide-react";
import SectionHeader from "./SectionHeader.jsx";

const statusStyles = {
  "On Track": "border-emerald-400/35 bg-emerald-400/10 text-emerald-400",
  Watch: "border-yellow-300/40 bg-yellow-300/10 text-yellow-300",
  Delayed: "border-orange-400/45 bg-orange-400/10 text-orange-300",
  Critical: "border-red-400/50 bg-red-400/10 text-red-300"
};

const riskStyles = {
  Low: "text-emerald-400",
  Medium: "text-yellow-300",
  High: "text-orange-300",
  Critical: "text-red-300"
};

export default function ProjectPortfolio({ projects }) {
  return (
    <article className="db-card-light p-5">
      <SectionHeader
        eyebrow="Projects"
        title="Project Portfolio"
        description="A compact control table for project status, cost index, schedule index and delivery risk."
        action={<button className="db-button db-button-primary" type="button">Open project control</button>}
      />

      <div className="grid gap-4 xl:grid-cols-3">
        {projects.map((project) => (
          <div className="rounded-3xl border border-slate-200/80 bg-white/60 p-4 dark:border-white/10 dark:bg-white/[0.045]" key={project.name}>
            <div className="mb-4 flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="grid h-11 w-11 place-items-center rounded-2xl bg-cyan-300/12 text-cyanAccent">
                  <Building2 size={19} />
                </span>
                <div>
                  <strong className="text-slate-950 dark:text-white">{project.name}</strong>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{project.phase}</p>
                </div>
              </div>
              <span className={`rounded-full border px-2.5 py-1 text-[11px] font-black ${statusStyles[project.status]}`}>
                {project.status}
              </span>
            </div>
            <div className="mb-3 h-2 overflow-hidden rounded-full bg-slate-200/80 dark:bg-white/[0.08]">
              <div className="h-full rounded-full bg-gradient-to-r from-cyanAccent to-purpleAccent" style={{ width: `${project.progress}%` }} />
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <Metric label="Progress" value={`${project.progress}%`} />
              <Metric label="Budget" value={project.budget} />
              <Metric label="CPI" value={project.cpi} />
              <Metric label="SPI" value={project.spi} />
            </div>
            <div className="mt-4 flex items-center justify-between">
              <span className={`text-sm font-black ${riskStyles[project.risk]}`}>{project.risk} risk</span>
              <button className="flex items-center gap-1 text-sm font-black text-cyanAccent" type="button">
                Review <ArrowRight size={15} />
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-5 overflow-x-auto">
        <table className="min-w-[880px] w-full border-separate border-spacing-y-2 text-sm">
          <thead className="text-left text-xs font-black uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
            <tr>
              <th className="px-3 py-2">Project</th>
              <th className="px-3 py-2">Manager</th>
              <th className="px-3 py-2">Phase</th>
              <th className="px-3 py-2">Budget</th>
              <th className="px-3 py-2">CPI</th>
              <th className="px-3 py-2">SPI</th>
              <th className="px-3 py-2">Risk</th>
              <th className="px-3 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((project) => (
              <tr className="bg-slate-100/80 dark:bg-white/[0.045]" key={`${project.name}-row`}>
                <td className="rounded-l-2xl px-3 py-4 font-black text-slate-950 dark:text-white">{project.name}</td>
                <td className="px-3 py-4 text-slate-600 dark:text-slate-300">{project.manager}</td>
                <td className="px-3 py-4 text-slate-600 dark:text-slate-300">{project.phase}</td>
                <td className="px-3 py-4 font-black text-slate-950 dark:text-white">{project.budget}</td>
                <td className="px-3 py-4">{project.cpi}</td>
                <td className="px-3 py-4">{project.spi}</td>
                <td className={`px-3 py-4 font-black ${riskStyles[project.risk]}`}>{project.risk}</td>
                <td className="rounded-r-2xl px-3 py-4">
                  <span className={`rounded-full border px-2.5 py-1 text-[11px] font-black ${statusStyles[project.status]}`}>
                    {project.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-2xl bg-slate-100/80 p-3 dark:bg-white/[0.045]">
      <p className="text-[11px] font-black uppercase tracking-[0.1em] text-slate-500 dark:text-slate-400">{label}</p>
      <strong className="mt-1 block text-slate-950 dark:text-white">{value}</strong>
    </div>
  );
}
