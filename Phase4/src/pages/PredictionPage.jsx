import { useState } from "react";
import PredictionForm from "../components/predict/PredictionForm.jsx";
import PredictionResult from "../components/predict/PredictionResult.jsx";
import { predictChurn } from "../api/client.js";

export default function PredictionPage({ prefill }) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (payload) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await predictChurn(payload);
      setResult(data);
    } catch (e) {
      if (e?.response?.status === 503) {
        setError("Prediction models are unavailable right now. Contact an administrator.");
      } else {
        setError(e?.response?.data?.detail || "Prediction failed. Check the inputs and try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <header style={{ marginBottom: 20 }}>
        <div className="eyebrow">ML PREDICTION</div>
        <h1 style={{ margin: "4px 0 0", fontSize: 24 }}>Churn prediction</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 13, marginTop: 6 }}>
          Runs logistic regression, random forest, and xgboost together — the result is a majority vote across all three.
        </p>
      </header>

      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 20, alignItems: "start" }}>
        <PredictionForm onSubmit={handleSubmit} loading={loading} prefill={prefill} />
        <PredictionResult result={result} error={error} loading={loading} />
      </div>
    </div>
  );
}