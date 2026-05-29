import SectionHeader from "./SectionHeader.jsx";

const statusStyles = {
  Controlled: "border-emerald-400/35 bg-emerald-400/10 text-emerald-400",
  Watch: "border-yellow-300/40 bg-yellow-300/10 text-yellow-300",
  Pressure: "border-red-400/45 bg-red-400/10 text-red-300"
};

export default function CostPackages({ packages }) {
  return (
    <article className="db-card-light p-5">
      <SectionHeader
        eyebrow="Cost Control"
        title="Cost Package Review"
        description="Package-level budget, committed cost and variance status for executive cost control."
      />
      <div className="grid gap-3">
        {packages.map((item) => (
          <div className="grid gap-3 rounded-3xl border border-slate-200/80 bg-white/60 p-4 dark:border-white/10 dark:bg-white/[0.045] md:grid-cols-[1.2fr_repeat(4,0.75fr)_auto] md:items-center" key={item.package}>
            <strong className="text-slate-950 dark:text-white">{item.package}</strong>
            <Metric label="Budget" value={item.budget} />
            <Metric label="Committed" value={item.committed} />
            <Metric label="Actual" value={item.actual} />
            <Metric label="Variance" value={item.variance} />
            <span className={`w-fit rounded-full border px-3 py-1 text-xs font-black ${statusStyles[item.status]}`}>{item.status}</span>
          </div>
        ))}
      </div>
    </article>
  );
}

function Metric({ label, value }) {
  return (
    <span>
      <small className="block text-[11px] font-black uppercase tracking-[0.1em] text-slate-500 dark:text-slate-400">{label}</small>
      <b className="text-slate-950 dark:text-white">{value}</b>
    </span>
  );
}
