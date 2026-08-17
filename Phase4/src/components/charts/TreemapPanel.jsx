// import { Treemap, Tooltip, ResponsiveContainer } from "recharts";

// // Colors nodes on a green -> amber -> red scale by churn_rate_pct
// function churnColor(pct) {
//   if (pct >= 35) return "#e2685f";
//   if (pct >= 20) return "#f0a868";
//   return "#4cb782";
// }

// function CustomNode({ x, y, width, height, name, churn_rate_pct, customer_count }) {
//   if (width < 2 || height < 2) return null;
//   const showLabel = width > 60 && height > 28;
//   return (
//     <g>
//       <rect
//         x={x} y={y} width={width} height={height}
//         fill={churnColor(churn_rate_pct)}
//         fillOpacity={0.85}
//         stroke="var(--bg-canvas)"
//         strokeWidth={2}
//       />
//       {showLabel && (
//         <>
//           <text x={x + 8} y={y + 18} fontSize={12} fill="#0c1116" fontWeight={600}>
//             {name}
//           </text>
//           <text x={x + 8} y={y + 34} fontSize={11} fill="#0c1116">
//             {customer_count} cust · {churn_rate_pct}% churn
//           </text>
//         </>
//       )}
//     </g>
//   );
// }

// export default function TreemapPanel({ title, data, height = 320 }) {
//   // recharts Treemap needs a `name` + `size` field
//   const treeData = data.map((d) => ({
//     name: `${d.partner_name} · ${d.state}`,
//     size: d.customer_count,
//     customer_count: d.customer_count,
//     churn_rate_pct: d.churn_rate_pct,
//   }));

//   return (
//     <div className="panel" style={{ padding: 18 }}>
//       <div className="eyebrow" style={{ marginBottom: 12 }}>{title}</div>
//       <ResponsiveContainer width="100%" height={height}>
//         <Treemap
//           data={treeData}
//           dataKey="size"
//           stroke="var(--bg-canvas)"
//           content={<CustomNode />}
//         >
//           <Tooltip
//             contentStyle={{
//               background: "var(--bg-panel-raised)",
//               border: "1px solid var(--border-hairline)",
//               borderRadius: 6,
//               fontSize: 12,
//             }}
//             formatter={(value, name, props) => [
//               `${props.payload.customer_count} customers, ${props.payload.churn_rate_pct}% churn`,
//               props.payload.name,
//             ]}
//           />
//         </Treemap>
//       </ResponsiveContainer>
//       <div style={{ display: "flex", gap: 16, marginTop: 10, fontSize: 11, color: "var(--text-tertiary)" }}>
//         <LegendSwatch color="#4cb782" label="< 20% churn" />
//         <LegendSwatch color="#f0a868" label="20–35% churn" />
//         <LegendSwatch color="#e2685f" label="≥ 35% churn" />
//       </div>
//     </div>
//   );
// }

// function LegendSwatch({ color, label }) {
//   return (
//     <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
//       <span style={{ width: 10, height: 10, background: color, borderRadius: 2, display: "inline-block" }} />
//       {label}
//     </span>
//   );
// }
