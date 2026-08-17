import { useState } from "react";
import { useAuth } from "../hooks/useAuth.js";

export default function LoginPage() {
  const { login, loading, error } = useAuth();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");

  const submit = (e) => {
    e.preventDefault();
    login(username, password);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background:
          "radial-gradient(circle at 20% 20%, rgba(240,168,104,0.06), transparent 40%), var(--bg-canvas)",
      }}
    >
      <form
        onSubmit={submit}
        className="panel"
        style={{ width: 360, padding: 32, display: "flex", flexDirection: "column", gap: 16 }}
      >
        <div>
          <div className="eyebrow">SIGNAL / OPS CONSOLE</div>
          <h1 style={{ margin: "6px 0 0", fontSize: 22 }}>Telecom Churn Dashboard</h1>
          <p style={{ color: "var(--text-secondary)", fontSize: 13, marginTop: 6 }}>
            Sign in with your admin credentials to view live risk and churn data.
          </p>
        </div>

        <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13 }}>
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={inputStyle}
            autoComplete="username"
          />
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13 }}>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={inputStyle}
            autoComplete="current-password"
          />
        </label>

        {error && (
          <div style={{ color: "var(--accent-red)", fontSize: 13 }}>{error}</div>
        )}

        <button type="submit" disabled={loading} style={buttonStyle}>
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}

const inputStyle = {
  background: "var(--bg-panel-raised)",
  border: "1px solid var(--border-hairline)",
  borderRadius: "var(--radius-sm)",
  padding: "10px 12px",
  fontSize: 14,
};

const buttonStyle = {
  background: "var(--accent-blue)",
  color: "#0c1116",
  fontWeight: 600,
  border: "none",
  borderRadius: "var(--radius-sm)",
  padding: "10px 12px",
  cursor: "pointer",
};
