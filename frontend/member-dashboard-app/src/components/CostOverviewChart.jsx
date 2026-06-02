import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

const currencyFormatter = (value) => `$${value}M`;

export default function CostOverviewChart({ data }) {
  return (
    <article className="db-card-light p-5 lg:col-span-2">
      <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="db-pill mb-2">Cost Overview</p>
          <h2 className="text-xl font-black text-slate-950 dark:text-white">Budget, actual cost and forecast trend</h2>
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400">Values shown in million USD</p>
      </div>

      <div className="h-[330px]">
        <ResponsiveContainer height="100%" width="100%">
          <LineChart data={data} margin={{ top: 8, right: 18, bottom: 8, left: 0 }}>
            <CartesianGrid strokeDasharray="4 8" stroke="rgba(148, 163, 184, 0.18)" />
            <XAxis dataKey="period" stroke="rgba(148, 163, 184, 0.75)" tickLine={false} />
            <YAxis stroke="rgba(148, 163, 184, 0.75)" tickFormatter={currencyFormatter} tickLine={false} />
            <Tooltip
              formatter={currencyFormatter}
              contentStyle={{
                background: "rgba(4, 13, 27, 0.94)",
                border: "1px solid rgba(41, 216, 255, 0.25)",
                borderRadius: "18px",
                color: "#fff"
              }}
            />
            <Legend />
            <Line type="monotone" dataKey="budget" name="Budget" stroke="#29d8ff" strokeWidth={3} dot={false} />
            <Line type="monotone" dataKey="actualCost" name="Actual Cost" stroke="#8d5dff" strokeWidth={3} dot={false} />
            <Line type="monotone" dataKey="forecast" name="Forecast" stroke="#fb7185" strokeWidth={3} dot={false} />
            <Line type="monotone" dataKey="committedCost" name="Committed Cost" stroke="#34d399" strokeWidth={3} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}
