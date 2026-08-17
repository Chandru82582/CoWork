// import { useState } from "react";
// import { ComposableMap, Geographies, Geography } from "react-simple-maps";

// const GEO_URL = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json";

// function colorScale(pct) {
//   if (pct == null) return "#2a3140";
//   if (pct >= 35) return "#e2685f";
//   if (pct >= 25) return "#e08a6b";
//   if (pct >= 15) return "#f0a868";
//   if (pct >= 8) return "#c9c25f";
//   return "#4cb782";
// }

// export default function ChoroplethPanel({ title, data, height = 340 }) {
//   const [hovered, setHovered] = useState(null);
//   const byState = Object.fromEntries(data.map((d) => [d.state, d]));

//   return (
//     <div className="panel" style={{ padding: 18, position: "relative" }}>
//       <div className="eyebrow" style={{ marginBottom: 12 }}>{title}</div>
//       <ComposableMap projection="geoAlbersUsa" style={{ width: "100%", height }}>
//         <Geographies geography={GEO_URL}>
//           {({ geographies }) =>
//             geographies.map((geo) => {
//               const stateName = geo.properties.name;
//               const stat = byState[stateName];
//               return (
//                 <Geography
//                   key={geo.rsmKey}
//                   geography={geo}
//                   onMouseEnter={() => setHovered(stat ? { ...stat } : { state: stateName, total_customers: 0, churn_rate_pct: null })}
//                   onMouseLeave={() => setHovered(null)}
//                   style={{
//                     default: {
//                       fill: colorScale(stat?.churn_rate_pct),
//                       stroke: "var(--bg-canvas)",
//                       strokeWidth: 0.75,
//                       outline: "none",
//                     },
//                     hover: {
//                       fill: colorScale(stat?.churn_rate_pct),
//                       stroke: "var(--text-primary)",
//                       strokeWidth: 1,
//                       outline: "none",
//                     },
//                     pressed: { outline: "none" },
//                   }}
//                 />
//               );
//             })
//           }
//         </Geographies>
//       </ComposableMap>

//       {hovered && (
//         <div
//           className="mono"
//           style={{
//             position: "absolute", top: 16, right: 16, background: "var(--bg-panel-raised)",
//             border: "1px solid var(--border-hairline)", borderRadius: 6, padding: "8px 10px", fontSize: 12,
//           }}
//         >
//           <div style={{ fontWeight: 600 }}>{hovered.state}</div>
//           <div style={{ color: "var(--text-secondary)" }}>
//             {hovered.churn_rate_pct == null ? "No data" : `${hovered.churn_rate_pct}% churn · ${hovered.total_customers} cust.`}
//           </div>
//         </div>
//       )}

//       <div style={{ display: "flex", gap: 12, marginTop: 10, fontSize: 11, color: "var(--text-tertiary)" }}>
//         <span>Churn rate</span>
//         <div style={{ display: "flex", gap: 2, alignItems: "center" }}>
//           {["#4cb782", "#c9c25f", "#f0a868", "#e08a6b", "#e2685f"].map((c) => (
//             <span key={c} style={{ width: 14, height: 8, background: c }} />
//           ))}
//         </div>
//         <span>low → high</span>
//       </div>
//     </div>
//   );
// }
