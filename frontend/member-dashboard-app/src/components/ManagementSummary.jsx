import { ClipboardCheck, Gauge, ShieldAlert, TimerReset } from "lucide-react";

export default function ManagementSummary({ summary }) {
  const items = [
    { label: "Overall performance", value: summary.overall, icon: Gauge },
    { label: "Main delay reason", value: summary.delayReason, icon: TimerReset },
    { label: "Cost pressure", value: summary.costPressure, icon: ShieldAlert },
    { label: "Immediate action required", value: summary.action, icon: ClipboardCheck }
  ];

  return (
    <article className="db-card-light overflow-hidden p-5 lg:col-span-2">
      <div className="relative">
        <div className="pointer-events-none absolute -right-16 -top-16 h-44 w-44 rounded-full bg-cyanAccent/15 blur-2xl" />
        <p className="db-pill mb-2">Executive Insight</p>
        <h2 className="text-2xl font-black tracking-tight text-slate-950 dark:text-white">Management Summary</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
          A compact project control view for leadership decisions, cost alignment and recovery planning.
        </p>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <div className="rounded-3xl border border-slate-200/80 bg-white/60 p-4 dark:border-white/10 dark:bg-white/[0.045]" key={item.label}>
              <div className="mb-3 flex items-center gap-2">
                <span className="grid h-9 w-9 place-items-center rounded-2xl bg-cyan-300/12 text-cyanAccent">
                  <Icon size={17} />
                </span>
                <strong className="text-sm text-slate-950 dark:text-white">{item.label}</strong>
              </div>
              <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">{item.value}</p>
            </div>
          );
        })}
      </div>
    </article>
  );
}
