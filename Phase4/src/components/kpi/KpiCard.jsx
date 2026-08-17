export default function KpiCard({ label, value, sublabel, accent }) {
  return (
    <div className="panel" style={{ padding: 18, display: "flex", flexDirection: "column", gap: 6, background: "#182338" }}>
      <div className="eyebrow">{label}</div>
      <div
        className="mono"
        style={{ fontSize: 30, fontWeight: 600, color: accent || "var(--text-primary)" }}
      >
        {value}
      </div>
      {sublabel && <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>{sublabel}</div>}
    </div>
  );
}
