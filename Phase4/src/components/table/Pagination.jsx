export default function Pagination({ meta, page, onPageChange }) {
  if (!meta) return null;
  const { total_pages, total_items, page_size } = meta;

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 4px" }}>
      <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
        {total_items} customers · page {page} of {total_pages} · {page_size}/page
      </div>
      <div style={{ display: "flex", gap: 6 }}>
        <button disabled={page <= 1} onClick={() => onPageChange(page - 1)} style={btnStyle(page <= 1)}>
          Prev
        </button>
        <button disabled={page >= total_pages} onClick={() => onPageChange(page + 1)} style={btnStyle(page >= total_pages)}>
          Next
        </button>
      </div>
    </div>
  );
}

const btnStyle = (disabled) => ({
  padding: "6px 12px",
  fontSize: 12,
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--border-hairline)",
  background: "transparent",
  color: disabled ? "var(--text-tertiary)" : "var(--text-primary)",
  cursor: disabled ? "not-allowed" : "pointer",
});
