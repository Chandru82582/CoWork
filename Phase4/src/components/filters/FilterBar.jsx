import { useState } from "react";
import SignalBars from "../kpi/SignalBars.jsx";

const RISK_TIERS = ["Low Risk", "Medium Risk", "High Risk"];

export default function FilterBar({ filters, onChange, onReset, partnerOptions, stateOptions }) {
  const [open, setOpen] = useState(false);

  const toggleMulti = (key, value) => {
    const current = filters[key] || [];
    const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value];
    onChange({ [key]: next });
  };

  const activeCount =
    (filters.partner_names?.length || 0) +
    (filters.states?.length || 0) +
    (filters.risk_categories?.length || 0) +
    [filters.tenure_min, filters.tenure_max, filters.salary_min, filters.salary_max, filters.age_min, filters.age_max].filter(
      (v) => v !== undefined
    ).length;

  return (
    <div className="panel" style={{ padding: 14, display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <input
          placeholder="Search by ID or city..."
          value={filters.search || ""}
          onChange={(e) => onChange({ search: e.target.value })}
          style={{
            flex: "1 1 220px",
            background: "var(--bg-panel-raised)",
            border: "1px solid var(--border-hairline)",
            borderRadius: "var(--radius-sm)",
            padding: "8px 10px",
            fontSize: 13,
          }}
        />

        <div style={{ display: "flex", gap: 6 }}>
          {RISK_TIERS.map((tier) => {
            const active = (filters.risk_categories || []).includes(tier);
            return (
              <button
                key={tier}
                onClick={() => toggleMulti("risk_categories", tier)}
                style={{
                  display: "flex", alignItems: "center", gap: 6,
                  padding: "6px 10px", fontSize: 12,
                  borderRadius: "var(--radius-sm)",
                  border: `1px solid ${active ? "var(--text-primary)" : "var(--border-hairline)"}`,
                  background: active ? "var(--bg-panel-raised)" : "transparent",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                }}
              >
                <SignalBars tier={tier} size={11} />
                {tier}
              </button>
            );
          })}
        </div>

        <button
          onClick={() => setOpen((o) => !o)}
          style={{
            padding: "6px 12px", fontSize: 12, borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border-hairline)", background: "transparent",
            color: "var(--text-secondary)", cursor: "pointer",
          }}
        >
          {open ? "Hide filters ▲" : `More filters ▾${activeCount ? ` (${activeCount})` : ""}`}
        </button>

        {activeCount > 0 && (
          <button
            onClick={onReset}
            style={{
              padding: "6px 12px", fontSize: 12, borderRadius: "var(--radius-sm)",
              border: "none", background: "transparent", color: "var(--accent-blue)", cursor: "pointer",
            }}
          >
            Clear all
          </button>
        )}
      </div>

      {open && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: 16,
            paddingTop: 8,
            borderTop: "1px solid var(--border-hairline)",
          }}
        >
          <MultiSelect
            label="Partner"
            options={partnerOptions}
            selected={filters.partner_names || []}
            onToggle={(v) => toggleMulti("partner_names", v)}
          />
          <MultiSelect
            label="State"
            options={stateOptions}
            selected={filters.states || []}
            onToggle={(v) => toggleMulti("states", v)}
          />
          <RangeInputs
            label="Tenure (days)"
            minVal={filters.tenure_min} maxVal={filters.tenure_max}
            onChange={(min, max) => onChange({ tenure_min: min, tenure_max: max })}
            step={10} max={2000}
          />
          <RangeInputs
            label="Age"
            minVal={filters.age_min} maxVal={filters.age_max}
            onChange={(min, max) => onChange({ age_min: min, age_max: max })}
            step={1} max={100}
          />
          <RangeInputs
            label="Salary ($)"
            minVal={filters.salary_min} maxVal={filters.salary_max}
            onChange={(min, max) => onChange({ salary_min: min, salary_max: max })}
            step={5000} max={250000}
          />
        </div>
      )}
    </div>
  );
}

function MultiSelect({ label, options, selected, onToggle }) {
  return (
    <div>
      <div className="eyebrow" style={{ marginBottom: 6 }}>{label}</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, maxHeight: 90, overflowY: "auto" }}>
        {options.map((opt) => {
          const active = selected.includes(opt);
          return (
            <button
              key={opt}
              onClick={() => onToggle(opt)}
              style={{
                padding: "4px 8px", fontSize: 11.5, borderRadius: 999,
                border: `1px solid ${active ? "var(--accent-blue)" : "var(--border-hairline)"}`,
                background: active ? "rgba(79,166,232,0.12)" : "transparent",
                color: active ? "var(--accent-blue)" : "var(--text-secondary)",
                cursor: "pointer",
              }}
            >
              {opt}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function RangeInputs({ label, minVal, maxVal, onChange, step, max }) {
  return (
    <div>
      <div className="eyebrow" style={{ marginBottom: 6 }}>{label}</div>
      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <input
          type="number"
          placeholder="min"
          value={minVal ?? ""}
          step={step}
          onChange={(e) => onChange(e.target.value === "" ? undefined : Number(e.target.value), maxVal)}
          style={numberInputStyle}
        />
        <span style={{ color: "var(--text-tertiary)", fontSize: 12 }}>–</span>
        <input
          type="number"
          placeholder="max"
          value={maxVal ?? ""}
          step={step}
          onChange={(e) => onChange(minVal, e.target.value === "" ? undefined : Number(e.target.value))}
          style={numberInputStyle}
        />
      </div>
      <input
        type="range"
        min={0}
        max={max}
        value={maxVal ?? max}
        onChange={(e) => onChange(minVal, Number(e.target.value))}
        style={{ width: "100%", marginTop: 6 }}
      />
    </div>
  );
}

const numberInputStyle = {
  width: 70,
  background: "var(--bg-panel-raised)",
  border: "1px solid var(--border-hairline)",
  borderRadius: "var(--radius-sm)",
  padding: "5px 6px",
  fontSize: 12,
};
