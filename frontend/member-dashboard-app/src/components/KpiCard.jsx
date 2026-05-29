import { Activity, AlertTriangle, ArrowDownRight, ArrowRight, ArrowUpRight, CircleDollarSign, Gauge, TimerReset } from "lucide-react";

const iconMap = {
  "Active Projects": Activity,
  "Total Budget": CircleDollarSign,
  "Cost Performance Index": Gauge,
  "Schedule Performance Index": TimerReset,
  "Delayed Activities": AlertTriangle,
  "High Risk Items": AlertTriangle
};

const statusStyles = {
  good: "border-emerald-400/30 bg-emerald-400/10 text-emerald-400",
  watch: "border-yellow-300/35 bg-yellow-300/10 text-yellow-300",
  warning: "border-orange-400/40 bg-orange-400/10 text-orange-300",
  critical: "border-red-400/45 bg-red-400/10 text-red-300"
};

export default function KpiCard({ kpi }) {
  const Icon = iconMap[kpi.label] || Activity;
  const isNegative = kpi.trend.startsWith("-");
  const isNeutral = kpi.trend === "0";

  return (
    <article className="db-card-light group p-5 transition duration-300 hover:-translate-y-1 hover:border-cyan-300/50 hover:shadow-glow">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div className="grid h-12 w-12 place-items-center rounded-2xl bg-cyan-300/12 text-cyanAccent">
          <Icon size={21} />
        </div>
        <span className={`rounded-full border px-2.5 py-1 text-[11px] font-black uppercase ${statusStyles[kpi.status]}`}>
          {kpi.status}
        </span>
      </div>
      <p className="text-sm font-black text-slate-500 dark:text-slate-400">{kpi.label}</p>
      <div className="mt-2 flex items-end justify-between gap-3">
        <strong className="text-3xl font-black tracking-tight text-slate-950 dark:text-white">{kpi.value}</strong>
        <span
          className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-black ${
            isNeutral
              ? "bg-slate-400/10 text-slate-400"
              : isNegative
                ? "bg-red-400/10 text-red-300"
                : "bg-emerald-400/10 text-emerald-400"
          }`}
        >
          {isNeutral ? <ArrowRight size={14} /> : isNegative ? <ArrowDownRight size={14} /> : <ArrowUpRight size={14} />}
          {kpi.trend}
        </span>
      </div>
      <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">{kpi.comparison}</p>
    </article>
  );
}
