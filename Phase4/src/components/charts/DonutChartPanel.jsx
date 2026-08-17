import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";

export default function DonutChartPanel({ title, data, nameKey, valueKey, colors, height = 260 }) {
  const total = data.reduce((sum, d) => sum + d[valueKey], 0);
  return (
    <div className="panel" style={{ padding: 18 }}>
      <div className="eyebrow" style={{ marginBottom: 12 }}>{title}</div>
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={data}
            dataKey={valueKey}
            nameKey={nameKey}
            innerRadius="55%"
            outerRadius="80%"
            paddingAngle={2}
          >
            {data.map((entry, i) => (
              <Cell key={i} fill={colors[entry[nameKey]] || colors.default || "#4fa6e8"} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: "var(--bg-panel-raised)",
              border: "1px solid var(--border-hairline)",
              borderRadius: 6,
              fontSize: 12,
            }}
            formatter={(value, name) => [`${value} (${((value / total) * 100).toFixed(1)}%)`, name]}
          />
          <Legend
            verticalAlign="bottom"
            height={28}
            formatter={(value) => <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
