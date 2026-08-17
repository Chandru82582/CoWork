import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts";

const COLORS = ["#4fa6e8", "#f0a868", "#4cb782", "#e2685f", "#9a7fd1", "#5fb8b0"];

export default function BarChartPanel({
  title, data, categoryKey, valueKey, layout = "vertical", colorByValue, height = 260,
}) {
  return (
    <div className="panel" style={{ padding: 18 }}>
      <div className="eyebrow" style={{ marginBottom: 12 }}>{title}</div>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={data}
          layout={layout === "horizontal" ? "vertical" : "horizontal"}
          margin={{ top: 4, right: 12, left: 4, bottom: 4 }}
        >
          <CartesianGrid stroke="var(--border-hairline)" strokeDasharray="3 3" />
          {layout === "horizontal" ? (
            <>
              <XAxis type="number" stroke="var(--text-tertiary)" fontSize={11} />
              <YAxis
                dataKey={categoryKey}
                type="category"
                stroke="var(--text-tertiary)"
                fontSize={11}
                width={90}
              />
            </>
          ) : (
            <>
              <XAxis dataKey={categoryKey} stroke="var(--text-tertiary)" fontSize={11} />
              <YAxis stroke="var(--text-tertiary)" fontSize={11} />
            </>
          )}
          <Tooltip
            contentStyle={{
              background: "var(--bg-panel-raised)",
              border: "1px solid var(--border-hairline)",
              borderRadius: 6,
              fontSize: 12,
            }}
          />
          <Bar dataKey={valueKey} radius={[3, 3, 3, 3]}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={
                  colorByValue
                    ? colorByValue(entry)
                    : COLORS[i % COLORS.length]
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
