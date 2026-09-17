import { useState, useRef, useEffect } from "react";
import { sendAssistantChat } from "../api/client.js";

// Helper to render markdown-like formatting (tables, bold, bullets, quotes) cleanly
function FormattedMessage({ content }) {
  if (!content) return null;

  const lines = content.split("\n");
  const elements = [];
  let inTable = false;
  let tableRows = [];
  let keyIdx = 0;

  const flushTable = () => {
    if (tableRows.length > 0) {
      const header = tableRows[0];
      const dataRows = tableRows.slice(1).filter((r) => !r.every((c) => c.match(/^:?-+:?$/)));
      elements.push(
        <div key={`table-${keyIdx++}`} style={{ overflowX: "auto", margin: "12px 0" }}>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: 13,
              fontFamily: "var(--font-mono)",
            }}
          >
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-hairline)", background: "var(--bg-panel-raised)" }}>
                {header.map((col, cIdx) => (
                  <th key={cIdx} style={{ padding: "8px 12px", textAlign: "left", color: "var(--text-secondary)" }}>
                    {col.trim()}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dataRows.map((row, rIdx) => (
                <tr
                  key={rIdx}
                  style={{
                    borderBottom: "1px solid var(--border-hairline)",
                    background: rIdx % 2 === 0 ? "transparent" : "rgba(255,255,255,0.02)",
                  }}
                >
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} style={{ padding: "8px 12px", color: "var(--text-primary)" }}>
                      {cell.trim()}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      tableRows = [];
      inTable = false;
    }
  };

  const renderInline = (text) => {
    // Handle bold: **text**
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, pIdx) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={pIdx} style={{ color: "var(--text-primary)", fontWeight: 600 }}>
            {part.slice(2, -2)}
          </strong>
        );
      }
      return part;
    });
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Detect markdown table rows
    if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
      inTable = true;
      const cells = line
        .trim()
        .slice(1, -1)
        .split("|")
        .map((c) => c.trim());
      tableRows.push(cells);
      continue;
    } else if (inTable) {
      flushTable();
    }

    // Detect Blockquote
    if (line.trim().startsWith("> ")) {
      elements.push(
        <div
          key={`quote-${keyIdx++}`}
          style={{
            borderLeft: "3px solid var(--accent-blue)",
            padding: "6px 12px",
            margin: "8px 0",
            background: "rgba(79, 166, 232, 0.08)",
            borderRadius: "0 var(--radius-sm) var(--radius-sm) 0",
            fontSize: 13,
            color: "var(--text-secondary)",
          }}
        >
          {renderInline(line.trim().slice(2))}
        </div>
      );
      continue;
    }

    // Detect bullet points
    if (line.trim().startsWith("- ") || line.trim().startsWith("* ")) {
      elements.push(
        <div
          key={`bullet-${keyIdx++}`}
          style={{
            display: "flex",
            gap: 8,
            margin: "4px 0 4px 12px",
            fontSize: 14,
            lineHeight: 1.5,
          }}
        >
          <span style={{ color: "var(--accent-blue)" }}>•</span>
          <div>{renderInline(line.trim().slice(2))}</div>
        </div>
      );
      continue;
    }

    // Detect numbered lists
    const numMatch = line.trim().match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      elements.push(
        <div
          key={`num-${keyIdx++}`}
          style={{
            display: "flex",
            gap: 8,
            margin: "4px 0 4px 12px",
            fontSize: 14,
            lineHeight: 1.5,
          }}
        >
          <span style={{ color: "var(--accent-blue)", fontFamily: "var(--font-mono)", fontSize: 12 }}>
            {numMatch[1]}.
          </span>
          <div>{renderInline(numMatch[2])}</div>
        </div>
      );
      continue;
    }

    // Empty line / paragraph break
    if (!line.trim()) {
      elements.push(<div key={`spacer-${keyIdx++}`} style={{ height: 8 }} />);
      continue;
    }

    // Normal text line
    elements.push(
      <p key={`p-${keyIdx++}`} style={{ margin: "4px 0", fontSize: 14, lineHeight: 1.5 }}>
        {renderInline(line)}
      </p>
    );
  }

  if (inTable) flushTable();

  return <div>{elements}</div>;
}

// Tool call trail component to display data origin and parameters
function ToolCallTrail({ toolCalls }) {
  const [expanded, setExpanded] = useState(false);

  if (!toolCalls || toolCalls.length === 0) return null;

  return (
    <div
      style={{
        marginTop: 14,
        paddingTop: 10,
        borderTop: "1px solid var(--border-hairline)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          cursor: "pointer",
        }}
        onClick={() => setExpanded(!expanded)}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <span
            className="mono"
            style={{
              fontSize: 11,
              padding: "2px 6px",
              background: "rgba(79, 166, 232, 0.15)",
              color: "var(--accent-blue)",
              borderRadius: "var(--radius-sm)",
              border: "1px solid rgba(79, 166, 232, 0.3)",
              fontWeight: 600,
            }}
          >
            TOOL TRAIL ({toolCalls.length})
          </span>
          {toolCalls.map((tc, idx) => (
            <span
              key={idx}
              className="mono"
              style={{
                fontSize: 11,
                color: "var(--text-tertiary)",
                background: "var(--bg-panel-raised)",
                padding: "2px 6px",
                borderRadius: "var(--radius-sm)",
              }}
            >
              {tc.tool}
            </span>
          ))}
        </div>

        <button
          type="button"
          style={{
            background: "none",
            border: "none",
            color: "var(--text-tertiary)",
            fontSize: 12,
            cursor: "pointer",
          }}
        >
          {expanded ? "Hide Details ▲" : "Inspect Tools ▼"}
        </button>
      </div>

      {expanded && (
        <div
          style={{
            marginTop: 10,
            display: "flex",
            flexDirection: "column",
            gap: 8,
          }}
        >
          {toolCalls.map((tc, idx) => (
            <div
              key={idx}
              style={{
                background: "var(--bg-canvas)",
                border: "1px solid var(--border-hairline)",
                borderRadius: "var(--radius-sm)",
                padding: "8px 12px",
                fontSize: 12,
                fontFamily: "var(--font-mono)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ color: "var(--accent-blue)", fontWeight: 600 }}>{tc.tool}</span>
                <span style={{ color: "var(--text-tertiary)" }}>Step {idx + 1}</span>
              </div>
              {tc.arguments && Object.keys(tc.arguments).length > 0 && (
                <div style={{ color: "var(--text-secondary)", marginBottom: 4 }}>
                  <span style={{ color: "var(--text-tertiary)" }}>Arguments: </span>
                  {JSON.stringify(tc.arguments)}
                </div>
              )}
              <details style={{ cursor: "pointer", marginTop: 4 }}>
                <summary style={{ color: "var(--text-tertiary)" }}>View Raw Tool Result</summary>
                <pre
                  style={{
                    marginTop: 6,
                    padding: 8,
                    background: "rgba(0,0,0,0.3)",
                    borderRadius: "var(--radius-sm)",
                    overflowX: "auto",
                    maxHeight: 180,
                    whiteSpace: "pre-wrap",
                    color: "var(--text-primary)",
                  }}
                >
                  {JSON.stringify(tc.result, null, 2)}
                </pre>
              </details>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const STARTER_PROMPTS = [
  { label: "Overall Churn KPIs", prompt: "What is our overall churn rate and total customer count?" },
  { label: "Top Feature Drivers", prompt: "What are the production model's top feature drivers?" },
  { label: "High Risk Customers", prompt: "Show me high-risk customers needing immediate outreach" },
  { label: "Tricky: Entire Customer List", prompt: "Can you provide the entire customer list?" },
  { label: "Tricky: CSAT Score", prompt: "What is our customer satisfaction CSAT score?" },
  { label: "Tricky: Price Hike Cause", prompt: "Why did churn increase? Did our recent price hike cause it?" },
];

export default function AssistantPage() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "**Welcome to Signal Churn Ops Assistant.**\n\n" +
        "I can answer operational queries regarding churn statistics, risk scores, partner breakdowns, and ML model predictions.\n\n" +
        "> **Operational Guardrails Active:**\n" +
        "> • **No Unverified Numbers:** Every metric comes directly from executed database tools.\n" +
        "> • **Capped Listings:** Customer lists are capped at 5 records to prevent data dumps.\n" +
        "> • **No Causal Speculation:** Explanations rely strictly on supported model feature drivers and usage correlations.",
      tool_calls: [],
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastFailedMessage, setLastFailedMessage] = useState(null);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, error]);

  const handleSend = async (messageText = input) => {
    const textToSend = messageText.trim();
    if (!textToSend || loading) return;

    setError(null);
    setLastFailedMessage(null);

    const userMessage = {
      role: "user",
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInput("");
    setLoading(true);

    try {
      // Send bounded slice of conversation history (last 8 turns) for predictable cost and context
      const boundedHistory = updatedMessages.slice(-8).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res = await sendAssistantChat(boundedHistory);

      const assistantReply = {
        role: "assistant",
        content: res.content,
        tool_calls: res.tool_calls || [],
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantReply]);
    } catch (err) {
      console.error("Assistant chat error:", err);
      setError("Failed to get response from the assistant. Server or network issue.");
      setLastFailedMessage(textToSend);
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = () => {
    if (!lastFailedMessage) return;
    handleSend(lastFailedMessage);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 80px)",
        maxWidth: 1080,
        margin: "0 auto",
        width: "100%",
        gap: 16,
      }}
    >
      {/* Header */}
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
          paddingBottom: 12,
          borderBottom: "1px solid var(--border-hairline)",
        }}
      >
        <div>
          <div className="eyebrow">INTELLIGENCE</div>
          <h1 style={{ margin: "4px 0 0", fontSize: 24, fontWeight: 600 }}>Operations Assistant</h1>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span
            className="mono"
            style={{
              fontSize: 11,
              color: "var(--signal-low)",
              background: "rgba(76, 183, 130, 0.12)",
              padding: "4px 8px",
              borderRadius: 9999,
              border: "1px solid rgba(76, 183, 130, 0.3)",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--signal-low)" }} />
            Guardrails Enforced • 8-Turn History Bound
          </span>
        </div>
      </header>

      {/* Starter Prompts */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {STARTER_PROMPTS.map((item, idx) => (
          <button
            key={idx}
            type="button"
            disabled={loading}
            onClick={() => handleSend(item.prompt)}
            style={{
              background: "var(--bg-panel)",
              border: "1px solid var(--border-hairline)",
              color: "var(--text-secondary)",
              padding: "6px 12px",
              borderRadius: 9999,
              fontSize: 12,
              cursor: loading ? "not-allowed" : "pointer",
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => {
              if (!loading) {
                e.currentTarget.style.borderColor = "var(--accent-blue)";
                e.currentTarget.style.color = "var(--text-primary)";
              }
            }}
            onMouseLeave={(e) => {
              if (!loading) {
                e.currentTarget.style.borderColor = "var(--border-hairline)";
                e.currentTarget.style.color = "var(--text-secondary)";
              }
            }}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* Message List Panel */}
      <div
        className="panel"
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "20px 24px",
          display: "flex",
          flexDirection: "column",
          gap: 20,
        }}
      >
        {messages.map((msg, index) => {
          const isUser = msg.role === "user";
          return (
            <div
              key={index}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: isUser ? "flex-end" : "flex-start",
              }}
            >
              {/* Role & Timestamp */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  marginBottom: 6,
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  color: "var(--text-tertiary)",
                }}
              >
                <span>{isUser ? "OPERATOR" : "ASSISTANT"}</span>
                <span>•</span>
                <span>{msg.timestamp}</span>
              </div>

              {/* Message Bubble */}
              <div
                style={{
                  maxWidth: "85%",
                  background: isUser ? "var(--bg-panel-raised)" : "rgba(26, 31, 39, 0.7)",
                  border: `1px solid ${isUser ? "var(--accent-blue)" : "var(--border-hairline)"}`,
                  borderRadius: "var(--radius-md)",
                  padding: "14px 18px",
                  color: "var(--text-primary)",
                  boxShadow: isUser ? "0 2px 8px rgba(79, 166, 232, 0.1)" : "none",
                }}
              >
                <FormattedMessage content={msg.content} />
                {!isUser && <ToolCallTrail toolCalls={msg.tool_calls} />}
              </div>
            </div>
          );
        })}

        {/* Loading Indicator */}
        {loading && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
            <div
              style={{
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                color: "var(--text-tertiary)",
                marginBottom: 6,
              }}
            >
              ASSISTANT • PROCESSING
            </div>
            <div
              style={{
                background: "var(--bg-panel)",
                border: "1px solid var(--border-hairline)",
                borderRadius: "var(--radius-md)",
                padding: "12px 18px",
                display: "flex",
                alignItems: "center",
                gap: 10,
                color: "var(--text-secondary)",
                fontSize: 13,
              }}
            >
              <span
                style={{
                  display: "inline-block",
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: "var(--accent-blue)",
                  animation: "pulse 1.2s infinite ease-in-out",
                }}
              />
              Executing tools & synthesizing verified response...
            </div>
          </div>
        )}

        {/* Error State with Retry Path */}
        {error && (
          <div
            style={{
              background: "rgba(226, 104, 95, 0.12)",
              border: "1px solid var(--accent-red)",
              borderRadius: "var(--radius-md)",
              padding: "12px 16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 12,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ color: "var(--accent-red)", fontSize: 16 }}>⚠️</span>
              <div>
                <div style={{ color: "var(--accent-red)", fontSize: 13, fontWeight: 600 }}>
                  Operation Failed
                </div>
                <div style={{ color: "var(--text-secondary)", fontSize: 12 }}>{error}</div>
              </div>
            </div>

            <button
              type="button"
              onClick={handleRetry}
              style={{
                background: "var(--accent-red)",
                color: "#fff",
                border: "none",
                borderRadius: "var(--radius-sm)",
                padding: "6px 14px",
                fontSize: 12,
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              ↻ Retry Request
            </button>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Box Panel */}
      <div
        className="panel"
        style={{
          padding: "12px 16px",
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <input
          type="text"
          value={input}
          disabled={loading}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            loading
              ? "Waiting for assistant..."
              : "Ask about churn rate, feature drivers, risk tiers, or customer status..."
          }
          style={{
            flex: 1,
            background: "transparent",
            border: "none",
            outline: "none",
            color: "var(--text-primary)",
            fontSize: 14,
          }}
        />

        <button
          type="button"
          disabled={loading || !input.trim()}
          onClick={() => handleSend()}
          style={{
            background: input.trim() && !loading ? "var(--accent-blue)" : "var(--bg-panel-raised)",
            color: input.trim() && !loading ? "#fff" : "var(--text-tertiary)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            padding: "8px 16px",
            fontSize: 13,
            fontWeight: 600,
            cursor: input.trim() && !loading ? "pointer" : "not-allowed",
            transition: "all 0.15s ease",
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}
