import { useEffect, useState } from "react";
import SignalBars from "../kpi/SignalBars.jsx";
import { fetchCustomerDetail } from "../../api/client.js";

export default function CustomerDetailDrawer({ customerId, onClose, onPredict }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!customerId) return;
    setLoading(true);
    setError(null);
    fetchCustomerDetail(customerId)
      .then(setDetail)
      .catch((e) => setError(e?.response?.data?.detail || "Failed to load customer detail."))
      .finally(() => setLoading(false));
  }, [customerId]);

  if (!customerId) return null;

  return (
    <div
      style={{ position: "fixed", inset: 0, zIndex: 50, display: "flex", justifyContent: "flex-end" }}
    >
      <div
        onClick={onClose}
        style={{ position: "absolute", inset: 0, background: "rgba(9,11,15,0.6)" }}
      />
      <div
        className="panel"
        style={{
          position: "relative", width: 420, maxWidth: "100%", height: "100%",
          borderRadius: 0, borderLeft: "1px solid var(--border-hairline)",
          padding: 24, overflowY: "auto", display: "flex", flexDirection: "column", gap: 20,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div className="eyebrow">CUSTOMER DETAIL</div>
            <div className="mono" style={{ fontSize: 22, fontWeight: 600 }}>#{customerId}</div>
          </div>
          <button onClick={onClose} style={closeBtnStyle}>Close ✕</button>
        </div>

        {loading && <div style={{ color: "var(--text-tertiary)" }}>Loading…</div>}
        {error && <div style={{ color: "var(--accent-red)" }}>{error}</div>}

        {detail && (
          <>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <SignalBars tier={detail.risk_category} size={18} />
              <div>
                <div style={{ fontWeight: 600 }}>{detail.risk_category}</div>
                <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                  Risk score {detail.risk_score} / 7
                </div>
              </div>
            </div>

            <Section title="Profile">
              <Field label="Gender" value={detail.gender} />
              <Field label="Age" value={detail.age} />
              <Field label="Registered" value={detail.date_of_registration} />
              <Field label="Tenure" value={`${detail.tenure} days`} />
              <Field label="Dependents" value={detail.num_dependents} />
              <Field
                label="Est. salary"
                value={detail.estimated_salary != null ? `$${detail.estimated_salary.toLocaleString()}` : "—"}
              />
              <Field label="Churned" value={detail.churn ? "Yes" : "No"} />
            </Section>

            <Section title="Account">
              <Field label="Partner" value={detail.partner_name} />
              <Field label="Location" value={`${detail.city}, ${detail.state} (${detail.pincode})`} />
            </Section>

            <Section title="Usage">
              <Field label="Calls made" value={detail.usage.calls_made} />
              <Field label="SMS sent" value={detail.usage.sms_sent} />
              <Field label="Data used" value={`${detail.usage.data_used} GB`} />
            </Section>

            <Section title="Risk breakdown">
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {detail.risk_factors.map((f) => (
                  <div
                    key={f.label}
                    style={{
                      display: "flex", justifyContent: "space-between", fontSize: 12.5,
                      color: f.triggered ? "var(--text-primary)" : "var(--text-tertiary)",
                    }}
                  >
                    <span>{f.triggered ? "●" : "○"} {f.label}</span>
                    <span className="mono">{f.triggered ? `+${f.points}` : "0"}</span>
                  </div>
                ))}
              </div>
            </Section>

            {onPredict && (
              <button
                onClick={() =>
                  onPredict({
                    customer_id: String(detail.customer_id),
                    age: String(detail.age),
                    gender: detail.gender,
                    tenure: String(detail.tenure),
                    num_dependents: String(detail.num_dependents),
                    estimated_salary: String(detail.estimated_salary ?? ""),
                    calls_made: String(detail.usage.calls_made),
                    sms_sent: String(detail.usage.sms_sent),
                    data_used: String(detail.usage.data_used),
                    telecom_partner: detail.partner_name,
                    pincode: detail.pincode,
                  })
                }
                style={predictBtnStyle}
              >
                Run churn prediction for this customer →
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}

const predictBtnStyle = {
  background: "var(--accent-blue)",
  color: "#0c1116",
  fontWeight: 600,
  border: "none",
  borderRadius: "var(--radius-sm)",
  padding: "10px 14px",
  cursor: "pointer",
  fontSize: 13,
};

function Section({ title, children }) {
  return (
    <div>
      <div className="eyebrow" style={{ marginBottom: 8 }}>{title}</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>{children}</div>
    </div>
  );
}

function Field({ label, value }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
      <span style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span>{value}</span>
    </div>
  );
}

const closeBtnStyle = {
  background: "transparent",
  border: "1px solid var(--border-hairline)",
  borderRadius: "var(--radius-sm)",
  color: "var(--text-secondary)",
  padding: "4px 10px",
  fontSize: 12,
  cursor: "pointer",
};
