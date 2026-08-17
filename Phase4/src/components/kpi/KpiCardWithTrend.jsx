export default function KpiCardWithTrend({ label, value, trend, unit = "", helpText }) {
  const delta = trend?.delta_pct;
  const isUp = typeof delta === "number" && delta > 0;
  const isDown = typeof delta === "number" && delta < 0;
  const arrow = isUp ? "▲" : isDown ? "▼" : "—";
  const color = isUp ? "var(--accent-red)" : isDown ? "var(--accent-green)" : "var(--text-tertiary)";

  return (
    <div className="panel" style={{ padding: 18, display: "flex", flexDirection: "column", gap: 6 }}>
      <div className="eyebrow">{label}</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
        <div className="mono" style={{ fontSize: 30, fontWeight: 600 }}>
          {value}
          {unit}
        </div>
        <div style={{ fontSize: 12, color, fontFamily: "var(--font-mono)" }}>
          {arrow} {typeof delta === "number" ? `${Math.abs(delta)}%` : "n/a"}
        </div>
      </div>
      <div style={{ display: "flex", gap: 3, alignItems: "flex-end", height: 20 }}>
        <SparkBar value={trend?.previous_period_value ?? 0} max={Math.max(trend?.current_period_value ?? 1, trend?.previous_period_value ?? 1, 1)} muted />
        <SparkBar value={trend?.current_period_value ?? 0} max={Math.max(trend?.current_period_value ?? 1, trend?.previous_period_value ?? 1, 1)} />
      </div>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
        {helpText || "vs. prior 30-day cohort"}
      </div>
    </div>
  );
}

function SparkBar({ value, max, muted }) {
  const pct = max ? Math.max((value / max) * 100, 4) : 4;
  return (
    <div
      style={{
        width: 14,
        height: `${pct}%`,
        background: muted ? "var(--border-hairline)" : "var(--accent-blue)",
        borderRadius: 2,
      }}
    />
  );
}
