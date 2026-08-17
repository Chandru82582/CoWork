// function colorFor(count, max) {
//   if (!count) return "var(--bg-panel-raised)";
//   const ratio = max ? count / max : 0;
//   if (ratio > 0.75) return "var(--accent-red)";
//   if (ratio > 0.5) return "var(--accent-amber)";
//   if (ratio > 0.25) return "#c9c25f";
//   return "var(--accent-green)";
// }

// export default function HeatmapCalendar({ title, points, note, cellSize = 12, gap = 3 }) {
//   const byDate = Object.fromEntries((points || []).map((p) => [p.date, p.count]));
//   const max = Math.max(1, ...(points || []).map((p) => p.count));

//   const today = new Date();
//   const days = [];
//   for (let i = 119; i >= 0; i--) {
//     const d = new Date(today);
//     d.setDate(d.getDate() - i);
//     const key = d.toISOString().slice(0, 10);
//     days.push({ key, count: byDate[key] || 0, weekday: d.getDay() });
//   }

//   // group into weeks (columns), starting each column on Sunday
//   const weeks = [];
//   let currentWeek = new Array(7).fill(null);
//   days.forEach((day) => {
//     currentWeek[day.weekday] = day;
//     if (day.weekday === 6) {
//       weeks.push(currentWeek);
//       currentWeek = new Array(7).fill(null);
//     }
//   });
//   if (currentWeek.some((d) => d)) weeks.push(currentWeek);

//   const width = weeks.length * (cellSize + gap);
//   const height = 7 * (cellSize + gap);

//   return (
//     <div className="panel" style={{ padding: 18 }}>
//       <div className="eyebrow" style={{ marginBottom: 12 }}>{title}</div>
//       <svg width={width} height={height}>
//         {weeks.map((week, wi) =>
//           week.map((day, di) =>
//             day ? (
//               <rect
//                 key={`${wi}-${di}`}
//                 x={wi * (cellSize + gap)}
//                 y={di * (cellSize + gap)}
//                 width={cellSize}
//                 height={cellSize}
//                 rx={2}
//                 fill={colorFor(day.count, max)}
//               >
//                 <title>{`${day.key}: ${day.count} new registrations`}</title>
//               </rect>
//             ) : null
//           )
//         )}
//       </svg>
//       {note && (
//         <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 10 }}>{note}</div>
//       )}
//     </div>
//   );
// }
