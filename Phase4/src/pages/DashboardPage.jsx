import { useMemo, useState } from "react";
import DashboardLayout from "../components/layout/DashboardLayout.jsx";
import KpiCard from "../components/kpi/KpiCard.jsx";
import KpiCardWithTrend from "../components/kpi/KpiCardWithTrend.jsx";
import BarChartPanel from "../components/charts/BarChartPanel.jsx";
import DonutChartPanel from "../components/charts/DonutChartPanel.jsx";
// import TreemapPanel from "../components/charts/TreemapPanel.jsx";
// import ChoroplethPanel from "../components/charts/ChoroplethPanel.jsx";
// import HeatmapCalendar from "../components/charts/HeatmapCalendar.jsx";
import FilterBar from "../components/filters/FilterBar.jsx";
import CustomerTable from "../components/table/CustomerTable.jsx";
import CustomerDetailDrawer from "../components/drawer/CustomerDetailDrawer.jsx";
import PredictionPage from "./PredictionPage.jsx";
import { useAnalytics } from "../hooks/useAnalytics.js";
import { useCustomers } from "../hooks/useCustomers.js";

const RISK_COLORS = {
  "Low Risk": "var(--signal-low)",
  "Medium Risk": "var(--signal-medium)",
  "High Risk": "var(--signal-high)",
};

export default function DashboardPage() {
  const [active, setActive] = useState("overview");
  const [selectedCustomerId, setSelectedCustomerId] = useState(null);

  const [predictPrefill, setPredictPrefill] = useState(null);

  const jumpToPredict = (prefillValues) => {
    setPredictPrefill(prefillValues);
    setSelectedCustomerId(null);
    setActive("predict");
  };

  const analytics = useAnalytics();
  const customers = useCustomers();

  const [barChartType, setBarChartType] = useState("partner");
  const [pieChartType, setPieChartType] = useState("risk");

 

  const partnerOptions = useMemo(
    () => analytics.churnByPartner.map((d) => d.partner_name),
    [analytics.churnByPartner]
  );
  const stateOptions = useMemo(
    () => analytics.churnByState.map((d) => d.state),
    [analytics.churnByState]
  );

  const retainedVsChurned = analytics.kpis
    ? [
        { label: "Retained", value: analytics.kpis.total_customers - Math.round((analytics.kpis.churn_rate_pct / 100) * analytics.kpis.total_customers) },
        { label: "Churned", value: Math.round((analytics.kpis.churn_rate_pct / 100) * analytics.kpis.total_customers) },
      ]
    : [];

const barChartConfig = {
  partner: {
    title: "CHURN RATE BY PARTNER",
    data: analytics.churnByPartner,
    categoryKey: "partner_name",
    valueKey: "churn_rate_pct",
  },
  ageBracket: {
    title: "CHURN RATE BY AGE BRACKET",
    data: analytics.churnByAgeBracket,
    categoryKey: "age_bracket",
    valueKey: "churn_rate_pct",
  },
};

const pieChartConfig = {
  risk: {
    title: "RISK TIER SPLIT",
    data: analytics.riskTierSplit,
    nameKey: "risk_category",
    valueKey: "count",
    colors: RISK_COLORS,
  },
  retention: {
    title: "RETAINED VS. CHURNED",
    data: retainedVsChurned,
    nameKey: "label",
    valueKey: "value",
    colors: {
      Retained: "var(--accent-green)",
      Churned: "var(--accent-red)",
    },
  },
};
  return (
    <DashboardLayout active={active} onNavigate={setActive}>
      {active !== "predict" && (
        <header style={{ marginBottom: 20 }}>
          <div className="eyebrow">OVERVIEW</div>
          <h1 style={{ margin: "4px 0 0", fontSize: 24 }}>Churn & risk console</h1>
        </header>
      )}

      {active === "predict" && <PredictionPage prefill={predictPrefill} />}
      
      {/* <header style={{ marginBottom: 20 }}>
        <div className="eyebrow">OVERVIEW</div>
        <h1 style={{ margin: "4px 0 0", fontSize: 24 }}>Churn & risk console</h1>
      </header> */}

      {active === "overview" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* KPI row */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 14 }}>
            <KpiCard
              label="Total customers"
              value={analytics.kpis?.total_customers?.toLocaleString() ?? "—"}
            />
            {/* <KpiCard
              label="ARPU"
              value={analytics.kpis?.arpu != null ? `$${analytics.kpis.arpu}` : "n/a"}
              sublabel={analytics.kpis?.arpu == null ? analytics.kpis?.arpu_note : undefined}
              accent="var(--text-tertiary)"
            /> */}
            <KpiCardWithTrend
              label="Churn rate"
              value={analytics.kpis?.churn_rate_pct ?? "—"}
              unit="%"
              trend={analytics.kpis?.churn_rate_trend}
            />
            <KpiCardWithTrend
              label="High-risk customers"
              value={analytics.kpis?.high_risk_count ?? "—"}
              trend={analytics.kpis?.high_risk_trend}
            />
          </div>

          {analytics.error && <div style={{ color: "var(--accent-red)" }}>{analytics.error}</div>}

          {/* Charts grid */}
          {/* <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }}>
            <BarChartPanel
              title="CHURN RATE BY PARTNER"
              data={analytics.churnByPartner}
              categoryKey="partner_name"
              valueKey="churn_rate_pct"
              layout="vertical"
            />
            <DonutChartPanel
              title="RISK TIER SPLIT"
              data={analytics.riskTierSplit}
              nameKey="risk_category"
              valueKey="count"
              colors={RISK_COLORS}
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <BarChartPanel
              title="CHURN RATE BY AGE BRACKET"
              data={analytics.churnByAgeBracket}
              categoryKey="age_bracket"
              valueKey="churn_rate_pct"
              layout="vertical"
            />
            <DonutChartPanel
              title="RETAINED VS. CHURNED"
              data={retainedVsChurned}
              nameKey="label"
              valueKey="value"
              colors={{ Retained: "var(--accent-green)", Churned: "var(--accent-red)" }}
            />
          </div> */}
          <div
  style={{
    display: "grid",
    gridTemplateColumns: "2fr 1fr",
    gap: 16,
  }}
>
  {/* Dynamic Bar Chart */}
  <div>
    <div
  style={{
    display: "inline-flex",
    background: "#424448",
    borderRadius: 9999,
    padding: 4,
    marginBottom: 12,
    gap: 4,
  }}
>
  <button
    onClick={() => setBarChartType("partner")}
    style={{
      background: barChartType === "partner" ? "#4b5563" : "transparent",
      color: "#fff",
      border: "none",
      padding: "8px 14px",
      borderRadius: 9999,
      cursor: "pointer",
      fontWeight: 500,
      transition: "all 0.2s ease",
    }}
  >
    By Partner
  </button>

  <button
    onClick={() => setBarChartType("ageBracket")}
    style={{
      background: barChartType === "ageBracket" ? "#4b5563" : "transparent",
      color: "#fff",
      border: "none",
      padding: "8px 14px",
      borderRadius: 9999,
      cursor: "pointer",
      fontWeight: 500,
      transition: "all 0.2s ease",
    }}
  >
    By Age Bracket
  </button>
</div>


    <BarChartPanel
      title={barChartConfig[barChartType].title}
      data={barChartConfig[barChartType].data}
      categoryKey={barChartConfig[barChartType].categoryKey}
      valueKey={barChartConfig[barChartType].valueKey}
      layout="vertical"
    />
  </div>

  {/* Dynamic Pie Chart */}
  <div>
    <div
  style={{
    display: "inline-flex",
    background: "#424448",
    borderRadius: 9999,
    padding: 4,
    marginBottom: 12,
    gap: 4,
  }}
>
  <button
    onClick={() => setPieChartType("risk")}
    style={{
      background: pieChartType === "risk" ? "#4b5563" : "transparent",
      color: "#fff",
      border: "none",
      padding: "8px 14px",
      borderRadius: 9999,
      cursor: "pointer",
      fontWeight: 500,
      transition: "all 0.2s ease",
    }}
  >
    Risk Tier
  </button>

  <button
    onClick={() => setPieChartType("retention")}
    style={{
      background: pieChartType === "retention" ? "#4b5563" : "transparent",
      color: "#fff",
      border: "none",
      padding: "8px 14px",
      borderRadius: 9999,
      cursor: "pointer",
      fontWeight: 500,
      transition: "all 0.2s ease",
    }}
  >
    Retained vs Churned
  </button>
</div>

    <DonutChartPanel
      title={pieChartConfig[pieChartType].title}
      data={pieChartConfig[pieChartType].data}
      nameKey={pieChartConfig[pieChartType].nameKey}
      valueKey={pieChartConfig[pieChartType].valueKey}
      colors={pieChartConfig[pieChartType].colors}
    />
  </div>
</div>

          {/* <ChoroplethPanel title="CHURN RATE BY STATE" data={analytics.churnByState} />

          <TreemapPanel title="CUSTOMER VOLUME BY PARTNER × STATE (COLOR = CHURN RATE)" data={analytics.volumeTreemap} />

          <HeatmapCalendar
            title="NEW REGISTRATIONS — LAST 120 DAYS"
            points={analytics.registrationHeatmap?.points}
            note={analytics.registrationHeatmap?.note}
          /> */}
        </div>
      )}

      {active === "customers" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <FilterBar
            filters={customers.filters}
            onChange={customers.updateFilters}
            onReset={customers.resetFilters}
            partnerOptions={partnerOptions}
            stateOptions={stateOptions}
          />
          <CustomerTable
            data={customers.data}
            loading={customers.loading}
            error={customers.error}
            page={customers.page}
            onPageChange={customers.setPage}
            onRowClick={setSelectedCustomerId}
          />
        </div>
      )}

      <CustomerDetailDrawer
        customerId={selectedCustomerId}
        onClose={() => setSelectedCustomerId(null)}
        onPredict={jumpToPredict}
      />    </DashboardLayout>
  );
}
