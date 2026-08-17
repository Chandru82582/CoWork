import SignalBars from "../kpi/SignalBars.jsx";
import Pagination from "./Pagination.jsx";

const COLUMNS = [
  { key: "customer_id", label: "ID" },
  { key: "risk_category", label: "Risk" },
  { key: "partner_name", label: "Partner" },
  { key: "city", label: "City" },
  { key: "state", label: "State" },
  { key: "age", label: "Age" },
  { key: "tenure", label: "Tenure (d)" },
  { key: "estimated_salary", label: "Salary" },
  { key: "churn", label: "Churned" },
];

export default function CustomerTable({ data, loading, error, page, onPageChange, onRowClick }) {
  return (
    <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border-hairline)" }}>
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  style={{
                    textAlign: "left", padding: "10px 14px", color: "var(--text-tertiary)",
                    fontWeight: 500, fontSize: 11, letterSpacing: "0.04em", textTransform: "uppercase",
                  }}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={COLUMNS.length} style={emptyCellStyle}>Loading customers…</td></tr>
            )}
            {!loading && error && (
              <tr><td colSpan={COLUMNS.length} style={{ ...emptyCellStyle, color: "var(--accent-red)" }}>{error}</td></tr>
            )}
            {!loading && !error && data.items.length === 0 && (
              <tr><td colSpan={COLUMNS.length} style={emptyCellStyle}>No customers match these filters.</td></tr>
            )}
            {!loading && !error && data.items.map((c) => (
              <tr
                key={c.customer_id}
                onClick={() => onRowClick(c.customer_id)}
                style={{ borderBottom: "1px solid var(--border-hairline)", cursor: "pointer" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-panel-raised)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <td style={{ ...cellStyle, fontFamily: "var(--font-mono)" }}>{c.customer_id}</td>
                <td style={cellStyle}>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                    <SignalBars tier={c.risk_category} />
                    {c.risk_category}
                  </span>
                </td>
                <td style={cellStyle}>{c.partner_name}</td>
                <td style={cellStyle}>{c.city}</td>
                <td style={cellStyle}>{c.state}</td>
                <td style={cellStyle}>{c.age}</td>
                <td style={cellStyle}>{c.tenure}</td>
                <td style={{ ...cellStyle, fontFamily: "var(--font-mono)" }}>
                  {c.estimated_salary != null ? `$${c.estimated_salary.toLocaleString()}` : "—"}
                </td>
                <td style={cellStyle}>
                  <span style={{ color: c.churn ? "var(--accent-red)" : "var(--accent-green)" }}>
                    {c.churn ? "Yes" : "No"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ padding: "0 14px", borderTop: "1px solid var(--border-hairline)" }}>
        <Pagination meta={data.meta} page={page} onPageChange={onPageChange} />
      </div>
    </div>
  );
}

const cellStyle = { padding: "10px 14px", color: "var(--text-primary)" };
const emptyCellStyle = { padding: "28px 14px", textAlign: "center", color: "var(--text-tertiary)" };
