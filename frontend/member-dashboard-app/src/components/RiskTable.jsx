const severityStyles = {
  Low: "border-emerald-400/35 bg-emerald-400/10 text-emerald-400",
  Medium: "border-yellow-300/40 bg-yellow-300/10 text-yellow-300",
  High: "border-orange-400/45 bg-orange-400/10 text-orange-300",
  Critical: "border-red-400/50 bg-red-400/10 text-red-300"
};

const severities = ["All", "Low", "Medium", "High", "Critical"];

export default function RiskTable({ risks, severityFilter, onSeverityFilterChange }) {
  const filteredRisks =
    severityFilter === "All" ? risks : risks.filter((risk) => risk.severity === severityFilter);

  return (
    <article className="db-card-light p-5 lg:col-span-2">
      <div className="mb-5 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="db-pill mb-2">Top Risks</p>
          <h2 className="text-xl font-black text-slate-950 dark:text-white">Leadership risk register</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          {severities.map((severity) => (
            <button
              className={`rounded-2xl border px-3 py-2 text-xs font-black transition ${
                severityFilter === severity
                  ? "border-cyan-300/50 bg-cyan-300/15 text-slate-950 shadow-glow dark:text-white"
                  : "border-slate-300/70 bg-white/70 text-slate-600 dark:border-white/10 dark:bg-white/[0.055] dark:text-slate-300"
              }`}
              key={severity}
              type="button"
              onClick={() => onSeverityFilterChange(severity)}
            >
              {severity}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[860px] w-full border-separate border-spacing-y-2">
          <thead>
            <tr className="text-left text-xs font-black uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
              <th className="px-3 py-2">Risk Title</th>
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2">Severity</th>
              <th className="px-3 py-2">Impact</th>
              <th className="px-3 py-2">Recommended Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredRisks.map((risk) => (
              <tr className="rounded-2xl bg-slate-100/80 text-sm dark:bg-white/[0.045]" key={risk.title}>
                <td className="rounded-l-2xl px-3 py-4 font-black text-slate-950 dark:text-white">{risk.title}</td>
                <td className="px-3 py-4 text-slate-600 dark:text-slate-300">{risk.category}</td>
                <td className="px-3 py-4">
                  <span className={`rounded-full border px-3 py-1 text-xs font-black ${severityStyles[risk.severity]}`}>
                    {risk.severity}
                  </span>
                </td>
                <td className="px-3 py-4 text-slate-600 dark:text-slate-300">{risk.impact}</td>
                <td className="rounded-r-2xl px-3 py-4 text-slate-600 dark:text-slate-300">{risk.action}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
