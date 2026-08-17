# Phase4 — Churn & Risk Dashboard (React)

React + Vite frontend for the telecom churn system. Consumes the existing
Phase3 FastAPI, extended with a new `/dashboard/*` router (see
`Phase3/MAIN_PY_PATCH.md` in this delivery).

## Setup

```bash
cd Phase4
npm install
cp .env.example .env    # points at http://localhost:8000 by default
npm run dev             # http://localhost:5173
```

Make sure Phase3 is running with the dashboard router mounted and CORS
enabled (see `Phase3/MAIN_PY_PATCH.md`), then log in with the existing admin
credentials (`admin` / `secret`).

## Structure

```
Phase4/
├── src/
│   ├── api/client.js              # axios instance, token injection, all endpoint calls
│   ├── context/AuthContext.jsx    # token state, login/logout
│   ├── hooks/
│   │   ├── useAuth.js
│   │   ├── useCustomers.js        # paginated + filtered customer list state
│   │   └── useAnalytics.js        # loads all KPI/chart endpoints in parallel
│   ├── components/
│   │   ├── layout/                # Sidebar, DashboardLayout
│   │   ├── kpi/                   # KpiCard, KpiCardWithTrend, SignalBars (signature motif)
│   │   ├── charts/                # Bar, Donut, Treemap, Choropleth, Calendar heatmap
│   │   ├── filters/FilterBar.jsx  # combined dropdown/range/toggle filter menu
│   │   ├── table/                 # CustomerTable, Pagination
│   │   └── drawer/                # CustomerDetailDrawer
│   └── pages/
│       ├── LoginPage.jsx
│       └── DashboardPage.jsx      # assembles everything
```

## Widget → endpoint map

| Widget                                            | Endpoint                                                                                        |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| KPI cards (total customers, high-risk count)      | `GET /dashboard/kpis`                                                                         |
| KPI card with trend (churn rate, high-risk count) | `GET /dashboard/kpis` (`*_trend` fields — 30-day cohort proxy, see note below)             |
| ARPU KPI                                          | `GET /dashboard/kpis` (`arpu: null` until a revenue column exists)                          |
| Bar chart — churn by partner / age bracket       | `GET /dashboard/analytics/churn-by-partner`, `.../churn-by-age-bracket`                     |
| Donut — retained vs. churned, risk tier split    | derived from`/dashboard/kpis` and `GET /dashboard/analytics/risk-tier-split`                |
| Treemap — volume by partner/state                | `GET /dashboard/analytics/volume-treemap`                                                     |
| Choropleth — churn rate by state                 | `GET /dashboard/analytics/churn-by-state`                                                     |
| Calendar heatmap                                  | `GET /dashboard/analytics/registration-heatmap` (registrations, not churn events — see note) |
| Paginated table + combined filters + search       | `GET /dashboard/customers`                                                                    |
| Detail drawer                                     | `GET /dashboard/customers/{id}/detail`                                                        |

## Known data-model limitations (surfaced in the API, not hidden)

1. **ARPU** — the `customers` table has no revenue/billing field. The KPI
   endpoint returns `arpu: null` with an explanatory `arpu_note`; the frontend
   renders "n/a" rather than a fabricated number.
2. **True churn-event heatmap / trend** — `churn` is a boolean with no event
   date, so trends and the heatmap use `date_of_registration` as a proxy and
   say so explicitly (`trend_methodology_note`, heatmap `note`). Add a
   `churn_date` column to Phase2/Phase3 `database.py` to replace the proxy
   with real data — see `Phase3/MAIN_PY_PATCH.md` §4 for the migration SQL.

## Notes

- All widths/columns are responsive down to a single column on narrow
  viewports via CSS grid `auto-fit`/`minmax`.
- Risk tier is represented consistently everywhere via the `SignalBars`
  component (three bars, like signal strength) — used in KPI context, table
  rows, and filter chips instead of ad hoc colored dots.
- `page_size` is capped server-side at 200 (see `dashboard_routes.py`) to
  protect the API from unbounded table exports.
