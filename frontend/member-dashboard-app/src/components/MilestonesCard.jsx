const statusStyles = {
  Upcoming: "border-cyan-300/35 bg-cyan-300/10 text-cyan-300",
  "Due Soon": "border-yellow-300/40 bg-yellow-300/10 text-yellow-300",
  Delayed: "border-red-400/45 bg-red-400/10 text-red-300",
  Completed: "border-emerald-400/35 bg-emerald-400/10 text-emerald-400"
};

export default function MilestonesCard({ milestones }) {
  return (
    <article className="db-card-light p-5">
      <div className="mb-5">
        <p className="db-pill mb-2">Upcoming Milestones</p>
        <h2 className="text-xl font-black text-slate-950 dark:text-white">Next delivery targets</h2>
      </div>
      <div className="grid gap-3">
        {milestones.map((milestone) => (
          <div className="rounded-3xl border border-slate-200/80 bg-white/60 p-4 dark:border-white/10 dark:bg-white/[0.045]" key={`${milestone.project}-${milestone.name}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <strong className="text-slate-950 dark:text-white">{milestone.name}</strong>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{milestone.project}</p>
              </div>
              <span className={`rounded-full border px-2.5 py-1 text-[11px] font-black ${statusStyles[milestone.status]}`}>
                {milestone.status}
              </span>
            </div>
            <div className="mt-4 flex items-center justify-between text-sm">
              <span className="text-slate-500 dark:text-slate-400">{milestone.dueDate}</span>
              <span className="font-black text-slate-700 dark:text-slate-200">
                {milestone.status === "Completed"
                  ? "Closed"
                  : milestone.daysRemaining < 0
                    ? `${Math.abs(milestone.daysRemaining)} days late`
                    : `${milestone.daysRemaining} days left`}
              </span>
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}
