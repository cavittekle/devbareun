import { AlertTriangle, CheckCircle2, Clock3, FileWarning, ListChecks, RadioTower } from "lucide-react";

const reviewStyles = {
  Controlled: "border-emerald-400/35 bg-emerald-400/10 text-emerald-400",
  "Watch closely": "border-yellow-300/40 bg-yellow-300/10 text-yellow-300",
  "Recovery needed": "border-red-400/45 bg-red-400/10 text-red-300"
};

export default function ControlHealthBar({ actionQueue, controlHealth }) {
  const metrics = [
    { label: "Readiness score", value: `${controlHealth.readinessScore}%`, icon: CheckCircle2, tone: "text-emerald-400" },
    { label: "Priority actions", value: controlHealth.highPriorityActions, icon: ListChecks, tone: "text-orange-300" },
    { label: "Delayed milestones", value: controlHealth.delayedMilestones, icon: Clock3, tone: "text-red-300" },
    { label: "Missing documents", value: controlHealth.missingDocuments, icon: FileWarning, tone: "text-yellow-300" }
  ];

  return (
    <section className="mb-6 grid gap-4 xl:grid-cols-[1.1fr_1.9fr]">
      <article className="db-card-light p-5">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <p className="db-pill mb-2">Control Health</p>
            <h2 className="text-xl font-black text-slate-950 dark:text-white">Executive readiness</h2>
          </div>
          <span className={`rounded-full border px-3 py-1 text-xs font-black ${reviewStyles[controlHealth.reviewStatus]}`}>
            {controlHealth.reviewStatus}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {metrics.map((metric) => {
            const Icon = metric.icon;
            return (
              <div className="rounded-3xl border border-slate-200/80 bg-white/60 p-4 dark:border-white/10 dark:bg-white/[0.045]" key={metric.label}>
                <Icon className={metric.tone} size={18} />
                <strong className="mt-2 block text-2xl font-black text-slate-950 dark:text-white">{metric.value}</strong>
                <p className="mt-1 text-[11px] font-black uppercase tracking-[0.1em] text-slate-500 dark:text-slate-400">{metric.label}</p>
              </div>
            );
          })}
        </div>
        <div className="mt-4 flex items-center gap-2 text-sm font-bold text-slate-500 dark:text-slate-400">
          <RadioTower size={16} className="text-cyanAccent" />
          Last sync: {controlHealth.lastSync}
        </div>
      </article>

      <article className="db-card-light p-5">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <p className="db-pill mb-2">Action Queue</p>
            <h2 className="text-xl font-black text-slate-950 dark:text-white">Do-not-miss items</h2>
          </div>
          <AlertTriangle className="text-orange-300" size={22} />
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {actionQueue.map((item) => (
            <div className="rounded-3xl border border-slate-200/80 bg-white/60 p-4 dark:border-white/10 dark:bg-white/[0.045]" key={`${item.label}-${item.detail}`}>
              <div className="mb-2 flex items-center justify-between gap-2">
                <strong className="text-slate-950 dark:text-white">{item.label}</strong>
                <span className="rounded-full border border-cyan-300/30 bg-cyan-300/10 px-2 py-0.5 text-[10px] font-black text-cyanAccent">
                  {item.priority}
                </span>
              </div>
              <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">{item.detail}</p>
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}
