import { useState } from "react";

const EMPTY_FORM = {
  customer_id: "",
  age: "",
  gender: "Male",
  tenure: "",
  num_dependents: "",
  estimated_salary: "",
  calls_made: "",
  sms_sent: "",
  data_used: "",
  telecom_partner: "",
  pincode: "",
};

// Fields sent to the model. tenure/customer_id/pincode are accepted by the
// schema but tenure_days was dropped from the retrained models' feature
// set (see Phase3/ml_model.py) — kept here only for context/logging.
const NUMERIC_FIELDS = [
  "age", "tenure", "num_dependents", "estimated_salary", "calls_made", "sms_sent", "data_used",
];

export default function PredictionForm({ onSubmit, loading, prefill }) {
  const [form, setForm] = useState(prefill || EMPTY_FORM);

  const update = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));

  const submit = (e) => {
    e.preventDefault();
    const payload = {};
    Object.entries(form).forEach(([key, val]) => {
      if (val === "" || val === undefined) return;
      payload[key] = NUMERIC_FIELDS.includes(key) || key === "customer_id" ? Number(val) : val;
    });
    onSubmit(payload);
  };

  return (
    <form onSubmit={submit} className="panel" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
      <div className="eyebrow">CUSTOMER FEATURES</div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
        <Field label="Customer ID (optional)" type="number" value={form.customer_id} onChange={(v) => update("customer_id", v)} />
        <Field label="Age" type="number" value={form.age} onChange={(v) => update("age", v)} required />
        <SelectField
          label="Gender"
          value={form.gender}
          onChange={(v) => update("gender", v)}
          options={["Male", "Female", "Other"]}
        />
        <Field label="Tenure (days)" type="number" value={form.tenure} onChange={(v) => update("tenure", v)} />
        <Field label="Dependents" type="number" value={form.num_dependents} onChange={(v) => update("num_dependents", v)} required />
        <Field label="Estimated salary ($)" type="number" value={form.estimated_salary} onChange={(v) => update("estimated_salary", v)} required />
        <Field label="Calls made" type="number" value={form.calls_made} onChange={(v) => update("calls_made", v)} required />
        <Field label="SMS sent" type="number" value={form.sms_sent} onChange={(v) => update("sms_sent", v)} required />
        <Field label="Data used (GB)" type="number" step="0.1" value={form.data_used} onChange={(v) => update("data_used", v)} required />
        <Field label="Telecom partner" value={form.telecom_partner} onChange={(v) => update("telecom_partner", v)} required placeholder="e.g. Partner A" />
        <Field label="Pincode (optional)" value={form.pincode} onChange={(v) => update("pincode", v)} />
      </div>

      <div style={{ display: "flex", gap: 10 }}>
        <button type="submit" disabled={loading} style={submitBtnStyle}>
          {loading ? "Running models…" : "Predict churn"}
        </button>
        <button type="button" onClick={() => setForm(EMPTY_FORM)} style={resetBtnStyle}>
          Reset
        </button>
      </div>
    </form>
  );
}

function Field({ label, value, onChange, type = "text", step, required, placeholder }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 5, fontSize: 12 }}>
      <span style={{ color: "var(--text-secondary)" }}>
        {label}
        {required && <span style={{ color: "var(--accent-red)" }}> *</span>}
      </span>
      <input
        type={type}
        step={step}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        style={inputStyle}
      />
    </label>
  );
}

function SelectField({ label, value, onChange, options }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 5, fontSize: 12 }}>
      <span style={{ color: "var(--text-secondary)" }}>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} style={inputStyle}>
        {options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
    </label>
  );
}

const inputStyle = {
  background: "var(--bg-panel-raised)",
  border: "1px solid var(--border-hairline)",
  borderRadius: "var(--radius-sm)",
  padding: "8px 10px",
  fontSize: 13,
};

const submitBtnStyle = {
  background: "var(--accent-blue)",
  color: "#0c1116",
  fontWeight: 600,
  border: "none",
  borderRadius: "var(--radius-sm)",
  padding: "10px 16px",
  cursor: "pointer",
  fontSize: 13,
};

const resetBtnStyle = {
  background: "transparent",
  border: "1px solid var(--border-hairline)",
  color: "var(--text-secondary)",
  borderRadius: "var(--radius-sm)",
  padding: "10px 16px",
  cursor: "pointer",
  fontSize: 13,
};
