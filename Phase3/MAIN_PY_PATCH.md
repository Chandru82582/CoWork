# Phase3/main.py — required edits

Two small, additive changes. Nothing existing needs to move or be deleted.

## 1. Add CORS middleware

The React dev server runs on a different origin (`http://localhost:5173`) than
the API (`http://localhost:8000`), so the browser will block requests without
CORS headers. Add this near the top of `main.py`, right after `app = FastAPI(...)`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:4173",   # Vite preview build
        # add your production dashboard origin here before deploying
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 2. Mount the dashboard router

Add this import near the other local imports (with `auth`, `database`, `rules`, `schemas`):

```python
from dashboard_routes import router as dashboard_router
```

Then, after all existing `@app.get` / `@app.post` route declarations (or right
after `app = FastAPI(...)` — order doesn't matter, routers are registered
independently), add:

```python
app.include_router(dashboard_router)
```

That's it. This adds `/dashboard/kpis`, `/dashboard/customers`,
`/dashboard/customers/{id}/detail`, and `/dashboard/analytics/*` under the
existing OAuth2 bearer auth (`get_current_admin_user`), fully additive to the
current `/token`, `/customers/{id}`, `/churn/summary`,
`/customers/risk-analysis/high-risk`, `/ml/predict-churn`, and `/health`
endpoints — none of which change.

## 3. Files to drop into Phase3/

```
Phase3/
├── main.py                 ← patched (2 changes above)
├── dashboard_schemas.py    ← new
├── dashboard_rules.py      ← new
├── dashboard_routes.py     ← new
├── auth.py                 ← unchanged
├── database.py             ← unchanged
├── schemas.py              ← unchanged
└── rules.py                ← unchanged
```

## 4. Recommended (optional) schema follow-ups

These aren't required for the dashboard to run, but two widgets are running on
proxies because of current schema gaps — see the notes returned inline in the
API responses (`arpu_note`, `trend_methodology_note`, heatmap `note`):

```sql
ALTER TABLE customers ADD COLUMN monthly_revenue DECIMAL(10,2) NULL;   -- enables real ARPU
ALTER TABLE customers ADD COLUMN churn_date DATE NULL;                 -- enables a true
                                                                         -- churn-event heatmap
                                                                         -- and real churn-rate trend
```
