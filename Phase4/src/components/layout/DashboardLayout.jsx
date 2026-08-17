import Sidebar from "./Sidebar.jsx";

export default function DashboardLayout({ active, onNavigate, children }) {
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar active={active} onNavigate={onNavigate} />
      <main style={{ flex: 1, padding: "24px 28px", maxWidth: "100%", overflowX: "hidden" }}>
        {children}
      </main>
    </div>
  );
}
