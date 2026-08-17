// The recurring visual idiom for this app: three vertical bars, like signal
// strength, used everywhere risk tier is shown (KPI cards, table rows, filter
// chips) instead of a generic colored dot.
const TIERS = {
  "Low Risk": { active: 1, color: "var(--signal-low)" },
  "Medium Risk": { active: 2, color: "var(--signal-medium)" },
  "High Risk": { active: 3, color: "var(--signal-high)" },
};

export default function SignalBars({ tier, size = 14 }) {
  const cfg = TIERS[tier] || TIERS["Low Risk"];
  const heights = [size * 0.4, size * 0.7, size];
  return (
    <span style={{ display: "inline-flex", alignItems: "flex-end", gap: 2 }} title={tier}>
      {heights.map((h, i) => (
        <span
          key={i}
          style={{
            width: 3,
            height: h,
            borderRadius: 1,
            background: i < cfg.active ? cfg.color : "var(--border-hairline)",
          }}
        />
      ))}
    </span>
  );
}
