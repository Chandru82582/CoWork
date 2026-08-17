import { useAuth } from "../../hooks/useAuth.js";

const NAV_ITEMS = [
  { key: "overview", label: "Overview" },
  { key: "customers", label: "Customers" },
  { key: "predict", label: "Predict churn" },
];

export default function Sidebar({ active, onNavigate }) {
  const { logout } = useAuth();
  return (
    <aside
      style={{
        width: 220,
        flexShrink: 0,
        borderRight: "1px solid var(--border-hairline)",
        display: "flex",
        flexDirection: "column",
        padding: "20px 16px",
        gap: 24,
      }}
    >
      <div>
        <div className="eyebrow">SIGNAL</div>
        <div style={{ fontSize: 15, fontWeight: 600, marginTop: 2 }}>Churn Ops Console</div>
      </div>

      <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {NAV_ITEMS.map((item) => (
          <button
            key={item.key}
            onClick={() => onNavigate(item.key)}
            style={{
              textAlign: "left",
              padding: "8px 10px",
              borderRadius: "var(--radius-sm)",
              border: "none",
              background: active === item.key ? "var(--bg-panel-raised)" : "transparent",
              color: active === item.key ? "var(--text-primary)" : "var(--text-secondary)",
              cursor: "pointer",
              fontSize: 14,
            }}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div style={{ marginTop: "auto" }}>
        <button
          onClick={logout}
          style={{
            width: "100%",
            padding: "8px 10px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border-hairline)",
            background: "transparent",
            color: "var(--text-secondary)",
            cursor: "pointer",
            fontSize: 13,
          }}
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}
