// import {
//   BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
// } from "recharts";

// const COLORS = ["#4fa6e8", "#f0a868", "#4cb782", "#e2685f", "#9a7fd1", "#5fb8b0"];

// export default function BarChartPanel({
//   title, data, categoryKey, valueKey, layout = "vertical", colorByValue, height = 260,
// }) {
//   return (
//     <div className="panel" style={{ padding: 18 }}>
//       <div className="eyebrow" style={{ marginBottom: 12 }}>{title}</div>
//       <ResponsiveContainer width="100%" height={height}>
//         <BarChart
//           data={data}
//           layout={layout === "horizontal" ? "vertical" : "horizontal"}
//           margin={{ top: 4, right: 12, left: 4, bottom: 4 }}
//         >
//           <CartesianGrid stroke="var(--border-hairline)" strokeDasharray="3 3" />
//           {layout === "horizontal" ? (
//             <>
//               <XAxis type="number" stroke="var(--text-tertiary)" fontSize={11} />
//               <YAxis
//                 dataKey={categoryKey}
//                 type="category"
//                 stroke="var(--text-tertiary)"
//                 fontSize={11}
//                 width={90}
//               />
//             </>
//           ) : (
//             <>
//               <XAxis dataKey={categoryKey} stroke="var(--text-tertiary)" fontSize={11} />
//               <YAxis stroke="var(--text-tertiary)" fontSize={11} />
//             </>
//           )}
//           <Tooltip
//             contentStyle={{
//               background: "var(--bg-panel-raised)",
//               border: "1px solid var(--border-hairline)",
//               borderRadius: 6,
//               fontSize: 12,
//             }}
//           />
//           <Bar dataKey={valueKey} radius={[3, 3, 3, 3]}>
//             {data.map((entry, i) => (
//               <Cell
//                 key={i}
//                 fill={
//                   colorByValue
//                     ? colorByValue(entry)
//                     : COLORS[i % COLORS.length]
//                 }
//               />
//             ))}
//           </Bar>
//         </BarChart>
//       </ResponsiveContainer>
//     </div>
//   );
// }


import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const COLORS = [
  "#60A5FA",
  "#FBBF24",
  "#34D399",
  "#F87171",
  "#A78BFA",
  "#2DD4BF",
];

export default function BarChartPanel({
  title,
  data,
  categoryKey,
  valueKey,
  layout = "vertical",
  colorByValue,
  height = 260,
}) {
  return (
    <div
      className="panel"
      style={{
        padding: 18,
        background: "#1f2937", // panel background
        borderRadius: 12,
      }}
    >
      <div
        className="eyebrow"
        style={{
          marginBottom: 12,
          color: "#93c5fd",
          letterSpacing: "2px",
        }}
      >
        {title}
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={data}
          layout={layout === "horizontal" ? "vertical" : "horizontal"}
          margin={{ top: 4, right: 12, left: 4, bottom: 4 }}
        >
          <CartesianGrid
            stroke="#374151"
            strokeDasharray="3 3"
          />

          {layout === "horizontal" ? (
            <>
              <XAxis
                type="number"
                stroke="#9ca3af"
                fontSize={11}
              />
              <YAxis
                dataKey={categoryKey}
                type="category"
                width={90}
                stroke="#9ca3af"
                fontSize={11}
              />
            </>
          ) : (
            <>
              <XAxis
                dataKey={categoryKey}
                stroke="#9ca3af"
                fontSize={11}
              />
              <YAxis
                stroke="#9ca3af"
                fontSize={11}
              />
            </>
          )}

          <Tooltip
            cursor={{
              fill: "rgba(125, 162, 214, 0.08)",
            }}
            wrapperStyle={{
              outline: "none",
            }}
            
            contentStyle={{
              background: "#182338",
              border: "1px solid #2B3A55",
              borderRadius: "8px",
              padding: "6px 10px",
              fontSize: "11px",
              minWidth: "unset",
              boxShadow: "0 4px 12px rgba(0,0,0,0.25)",
            }}
            labelStyle={{
              color: "#E5E7EB",
              fontSize: "12px",
              fontWeight: 600,
              marginBottom: "2px",
            }}
            itemStyle={{
              color: "#7DA2D6",
              fontSize: "11px",
              padding: 0,
            }}
          />

          <Bar dataKey={valueKey} radius={[8, 8, 0, 0]}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={
                  colorByValue
                    ? colorByValue(entry)
                    : COLORS[i % COLORS.length]
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}