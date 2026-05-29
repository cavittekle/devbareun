const stageStyles = {
  Completed: "bg-emerald-400 text-emerald-950",
  "In Progress": "bg-cyanAccent text-slate-950",
  Delayed: "bg-red-400 text-red-950",
  "Not Started": "bg-slate-500 text-white"
};

export default function ScheduleTimeline({ schedule, stages }) {
  const progressCards = [
    { label: "Planned Progress", value: `${schedule.planned}%`, tone: "text-cyanAccent" },
    { label: "Actual Progress", value: `${schedule.actual}%`, tone: "text-purpleAccent" },
    { label: "Variance", value: `${schedule.variance}%`, tone: schedule.variance < 0 ? "text-red-300" : "text-emerald-400" },
    { label: "Delay Days", value: schedule.delayDays, tone: schedule.delayDays > 14 ? "text-red-300" : "text-yellow-300" }
  ];

  return (
    <article className="db-card-light p-5 lg:col-span-2">
      <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="db-pill mb-2">Schedule Performance</p>
          <h2 className="text-xl font-black text-slate-950 dark:text-white">Progress and phase timeline</h2>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {progressCards.map((card) => (
          <div className="rounded-3xl border border-slate-200/80 bg-white/60 p-4 dark:border-white/10 dark:bg-white/[0.045]" key={card.label}>
            <p className="text-xs font-black uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">{card.label}</p>
            <strong className={`mt-2 block text-3xl font-black ${card.tone}`}>{card.value}</strong>
          </div>
        ))}
      </div>

      <div className="space-y-4">
        {stages.map((stage) => (
          <div className="grid gap-2 lg:grid-cols-[130px_1fr_110px]" key={stage.name}>
            <div className="text-sm font-black text-slate-700 dark:text-slate-200">{stage.name}</div>
            <div className="relative h-8 overflow-hidden rounded-full bg-slate-200/80 dark:bg-white/[0.07]">
              <div
                className={`absolute top-1 h-6 rounded-full ${stageStyles[stage.status]}`}
                style={{ left: `${stage.start}%`, width: `${stage.width}%` }}
              />
              <div
                className="absolute inset-y-0 left-0 rounded-full bg-cyanAccent/15"
                style={{ width: `${stage.progress}%` }}
              />
            </div>
            <span className="text-sm font-bold text-slate-500 dark:text-slate-400">{stage.status}</span>
          </div>
        ))}
      </div>
    </article>
  );
}
