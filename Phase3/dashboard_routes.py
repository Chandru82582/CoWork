"""
dashboard_routes.py
APIRouter for the Phase4 React dashboard. Mounted in main.py with:

    from dashboard_routes import router as dashboard_router
    app.include_router(dashboard_router)

Reuses the existing auth dependency (get_current_admin_user) so these
endpoints inherit the same OAuth2 bearer-token protection as the rest
of Phase3. Every route is a read-only fetch, consistent with the
"Phase 3 is a read-only fetch layer" architectural decision.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query

from auth import get_current_admin_user
# from dashboard_schemas import (
#     KpiSummaryResponse, PaginatedCustomerResponse, CustomerDetailResponse,
#     ChurnByPartnerItem, ChurnByStateItem, ChurnByAgeBracketItem,
#     RiskTierSplitItem, TreemapNode, RegistrationHeatmapResponse, CustomerFilters,
# )

from dashboard_schemas import (
    KpiSummaryResponse, PaginatedCustomerResponse, CustomerDetailResponse,
    ChurnByPartnerItem, ChurnByAgeBracketItem,ChurnByStateItem,
    RiskTierSplitItem, CustomerFilters,
)

import dashboard_rules as rules

logger = logging.getLogger("main")

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/kpis", response_model=KpiSummaryResponse)
def kpi_summary(current_user: dict = Depends(get_current_admin_user)):
    return rules.get_kpi_summary()


@router.get("/customers", response_model=PaginatedCustomerResponse)
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    partner_names: list[str] | None = Query(None),
    states: list[str] | None = Query(None),
    cities: list[str] | None = Query(None),
    risk_categories: list[str] | None = Query(None),
    tenure_min: int | None = None,
    tenure_max: int | None = None,
    salary_min: float | None = None,
    salary_max: float | None = None,
    age_min: int | None = None,
    age_max: int | None = None,
    search: str | None = None,
    current_user: dict = Depends(get_current_admin_user),
):
    filters = CustomerFilters(
        partner_names=partner_names, states=states, cities=cities,
        risk_categories=risk_categories, tenure_min=tenure_min, tenure_max=tenure_max,
        salary_min=salary_min, salary_max=salary_max, age_min=age_min, age_max=age_max,
        search=search,
    )
    return rules.get_customers_paginated(filters, page, page_size)


@router.get("/customers/{customer_id}/detail", response_model=CustomerDetailResponse)
def customer_detail(customer_id: int, current_user: dict = Depends(get_current_admin_user)):
    result = rules.get_customer_detail(customer_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return result


@router.get("/analytics/churn-by-partner", response_model=list[ChurnByPartnerItem])
def churn_by_partner(current_user: dict = Depends(get_current_admin_user)):
    return rules.get_churn_by_partner()


@router.get("/analytics/churn-by-state", response_model=list[ChurnByStateItem])
def churn_by_state(current_user: dict = Depends(get_current_admin_user)):
    return rules.get_churn_by_state()


@router.get("/analytics/churn-by-age-bracket", response_model=list[ChurnByAgeBracketItem])
def churn_by_age_bracket(current_user: dict = Depends(get_current_admin_user)):
    return rules.get_churn_by_age_bracket()


@router.get("/analytics/risk-tier-split", response_model=list[RiskTierSplitItem])
def risk_tier_split(current_user: dict = Depends(get_current_admin_user)):
    return rules.get_risk_tier_split()


# @router.get("/analytics/volume-treemap", response_model=list[TreemapNode])
# def volume_treemap(current_user: dict = Depends(get_current_admin_user)):
#     return rules.get_volume_treemap()


# @router.get("/analytics/registration-heatmap", response_model=RegistrationHeatmapResponse)
# def registration_heatmap(days: int = Query(120, ge=1, le=730), current_user: dict = Depends(get_current_admin_user)):
#     return rules.get_registration_heatmap(days)
