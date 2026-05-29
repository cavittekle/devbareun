import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

const colors = {
  "On Track": "#34d399",
  Watch: "#fde047",
  Delayed: "#fb923c",
  Critical: "#fb7185",
  "No Data": "#94a3b8"
};

export default function StatusDonutChart({ data }) {
  const total = data.reduce((sum, item) => sum + item.value, 0);

  return (
    <article className="db-card-light p-5">
      <div className="mb-5">
        <p className="db-pill mb-2">Project Status</p>
        <h2 className="text-xl font-black text-slate-950 dark:text-white">Portfolio distribution</h2>
      </div>
      <div className="relative h-[260px]">
        <ResponsiveContainer height="100%" width="100%">
          <PieChart>
            <Pie data={data} dataKey="value" innerRadius={72} outerRadius={104} paddingAngle={3}>
              {data.map((entry) => (
                <Cell fill={colors[entry.name]} key={entry.name} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: "rgba(4, 13, 27, 0.94)",
                border: "1px solid rgba(41, 216, 255, 0.25)",
                borderRadius: "18px",
                color: "#fff"
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 grid place-items-center">
          <div className="text-center">
            <strong className="block text-4xl font-black text-slate-950 dark:text-white">{total}</strong>
            <span className="text-xs font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
              projects
            </span>
          </div>
        </div>
      </div>
      <div className="mt-3 grid gap-2">
        {data.map((item) => (
          <div className="flex items-center justify-between text-sm" key={item.name}>
            <span className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
              <i className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: colors[item.name] }} />
              {item.name}
            </span>
            <strong className="text-slate-950 dark:text-white">{item.value}</strong>
          </div>
        ))}
      </div>
    </article>
  );
}
