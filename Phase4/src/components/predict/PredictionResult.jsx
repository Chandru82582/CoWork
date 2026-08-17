import SignalBars from "../kpi/SignalBars.jsx";

const RISK_TO_TIER = { Low: "Low Risk", Medium: "Medium Risk", High: "High Risk" };
const RISK_COLOR = {
  Low: "var(--accent-green)",
  Medium: "var(--accent-amber)",
  High: "var(--accent-red)",
};

export default function PredictionResult({ result, error, loading }) {
  if (loading) {
    return (
      <div className="panel" style={{ padding: 20, color: "var(--text-tertiary)" }}>
        Running the 3-model ensemble…
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel" style={{ padding: 20, color: "var(--accent-red)" }}>
        {error}
      </div>
    );
  }

  if (!result) {
    return (
      <div className="panel" style={{ padding: 20, color: "var(--text-tertiary)", fontSize: 13 }}>
        Fill in the customer features and run a prediction to see results here.
      </div>
    );
  }

  const pct = Math.round(result.churn_probability * 100);
  const confidencePct = Math.round(result.confidence_score * 100);

  return (
    <div className="panel" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 18 }}>
      <div>
        <div className="eyebrow">PREDICTION RESULT</div>
        {result.customer_id != null && (
          <div className="mono" style={{ fontSize: 13, color: "var(--text-tertiary)", marginTop: 2 }}>
            Customer #{result.customer_id}
          </div>
        )}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <ProbabilityRing pct={pct} color={RISK_COLOR[result.risk_level] || "var(--accent-blue)"} />
        <div>
          <div className="mono" style={{ fontSize: 26, fontWeight: 600 }}>
            {pct}% churn probability
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
            <SignalBars tier={RISK_TO_TIER[result.risk_level] || "Low Risk"} size={14} />
            <span style={{ fontSize: 13, color: RISK_COLOR[result.risk_level] }}>{result.risk_level} risk</span>
          </div>
          <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 4 }}>
            Prediction: <strong style={{ color: "var(--text-primary)" }}>{result.churn_prediction ? "Will churn" : "Will stay"}</strong>
            {" · "}
            Model agreement: {confidencePct}%
          </div>
        </div>
      </div>

      {result.model_votes && (
        <div>
          <div className="eyebrow" style={{ marginBottom: 8 }}>MODEL VOTES</div>
          <div style={{ display: "flex", gap: 10 }}>
            {Object.entries(result.model_votes).map(([model, vote]) => (
              <div
                key={model}
                className="mono"
                style={{
                  flex: 1, textAlign: "center", padding: "10px 8px",
                  borderRadius: "var(--radius-sm)", border: "1px solid var(--border-hairline)",
                  background: "var(--bg-panel-raised)",
                }}
              >
                <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>
                  {model.replace(/_/g, " ")}
                </div>
                <div style={{ fontSize: 13, color: vote ? "var(--accent-red)" : "var(--accent-green)" }}>
                  {vote ? "Churn" : "Stay"}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <div className="eyebrow" style={{ marginBottom: 6 }}>RECOMMENDATION</div>
        <div style={{ fontSize: 13, color: "var(--text-primary)" }}>{result.recommendation}</div>
      </div>
    </div>
  );
}

function ProbabilityRing({ pct, color, size = 84 }) {
  const stroke = 8;
  const r = (size - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (pct / 100) * circumference;

  return (
    <svg width={size} height={size} style={{ flexShrink: 0 }}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border-hairline)" strokeWidth={stroke} />
      <circle
        cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke}
        strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text x="50%" y="52%" textAnchor="middle" dominantBaseline="middle" fontSize={16} fontFamily="var(--font-mono)" fill="var(--text-primary)">
        {pct}%
      </text>
    </svg>
  );
}
