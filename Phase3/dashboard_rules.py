"""
dashboard_rules.py
Additive query functions for the Phase4 dashboard. Follows the same convention
as rules.py: each function opens its own session via get_db(), read-only,
no computation beyond aggregation (risk_score/risk_category are still
pre-calculated at insertion time in Phase2 — we never recompute them here).
"""
import logging
from datetime import date, timedelta
from sqlalchemy import func, case, or_, and_
from sqlalchemy.orm import Session

from database import get_db, Customer, TelecomPartner, Location, CustomerUsage
# from dashboard_schemas import (
#     KpiSummaryResponse, KpiTrend,
#     CustomerListItem, PaginationMeta, PaginatedCustomerResponse,
#     CustomerDetailResponse, UsageBreakdown, RiskFactorBreakdown,
#     ChurnByPartnerItem, ChurnByStateItem, ChurnByAgeBracketItem,
#     RiskTierSplitItem, TreemapNode,
#     RegistrationHeatmapPoint, RegistrationHeatmapResponse,
#     CustomerFilters,
# )

from dashboard_schemas import (
    KpiSummaryResponse, KpiTrend,
    CustomerListItem, PaginationMeta, PaginatedCustomerResponse,
    CustomerDetailResponse, UsageBreakdown, RiskFactorBreakdown,
    ChurnByPartnerItem, ChurnByAgeBracketItem,ChurnByStateItem,
    RiskTierSplitItem,
    CustomerFilters,
)
logger = logging.getLogger("main")

AGE_BRACKETS = [(18, 25), (26, 35), (36, 45), (46, 55), (56, 65), (66, 200)]


def _base_customer_query(db: Session):
    return (
        db.query(Customer, Location, TelecomPartner)
        .join(Location, Customer.pincode == Location.pincode)
        .join(TelecomPartner, Customer.telecom_partner_id == TelecomPartner.partner_id)
    )


def _apply_filters(query, filters: CustomerFilters):
    if filters.partner_names:
        query = query.filter(TelecomPartner.partner_name.in_(filters.partner_names))
    if filters.states:
        query = query.filter(Location.state.in_(filters.states))
    if filters.cities:
        query = query.filter(Location.city.in_(filters.cities))
    if filters.risk_categories:
        query = query.filter(Customer.risk_category.in_(filters.risk_categories))
    if filters.tenure_min is not None:
        query = query.filter(Customer.tenure >= filters.tenure_min)
    if filters.tenure_max is not None:
        query = query.filter(Customer.tenure <= filters.tenure_max)
    if filters.salary_min is not None:
        query = query.filter(Customer.estimated_salary >= filters.salary_min)
    if filters.salary_max is not None:
        query = query.filter(Customer.estimated_salary <= filters.salary_max)
    if filters.age_min is not None:
        query = query.filter(Customer.age >= filters.age_min)
    if filters.age_max is not None:
        query = query.filter(Customer.age <= filters.age_max)
    if filters.search:
        search = filters.search.strip()
        conditions = [Location.city.ilike(f"%{search}%")]
        if search.isdigit():
            conditions.append(Customer.customer_id == int(search))
        query = query.filter(or_(*conditions))
    return query


def get_kpi_summary() -> KpiSummaryResponse:
    db = next(get_db())
    try:
        total_customers = db.query(func.count(Customer.customer_id)).scalar() or 0
        churned = db.query(func.count(Customer.customer_id)).filter(Customer.churn.is_(True)).scalar() or 0
        churn_rate = round((churned / total_customers) * 100, 2) if total_customers else 0.0
        high_risk = db.query(func.count(Customer.customer_id)).filter(
            Customer.risk_category == "High Risk"
        ).scalar() or 0

        today = date.today()
        window_start = today - timedelta(days=30)
        prev_window_start = today - timedelta(days=60)

        def cohort_counts(start, end):
            q = db.query(Customer).filter(
                Customer.date_of_registration >= start,
                Customer.date_of_registration < end,
            )
            total = q.count()
            churned_n = q.filter(Customer.churn.is_(True)).count()
            high_risk_n = q.filter(Customer.risk_category == "High Risk").count()
            rate = round((churned_n / total) * 100, 2) if total else 0.0
            return total, rate, high_risk_n

        cur_total, cur_rate, cur_hr = cohort_counts(window_start, today + timedelta(days=1))
        prev_total, prev_rate, prev_hr = cohort_counts(prev_window_start, window_start)

        def pct_delta(cur, prev):
            if prev == 0:
                return None
            return round(((cur - prev) / prev) * 100, 2)

        logger.info("Fetching KPI summary")
        return KpiSummaryResponse(
            total_customers=total_customers,
            churn_rate_pct=churn_rate,
            high_risk_count=high_risk,
            arpu=None,
            new_customers_trend=KpiTrend(
                current_period_value=cur_total, previous_period_value=prev_total,
                delta_pct=pct_delta(cur_total, prev_total),
            ),
            churn_rate_trend=KpiTrend(
                current_period_value=cur_rate, previous_period_value=prev_rate,
                delta_pct=pct_delta(cur_rate, prev_rate),
            ),
            high_risk_trend=KpiTrend(
                current_period_value=cur_hr, previous_period_value=prev_hr,
                delta_pct=pct_delta(cur_hr, prev_hr),
            ),
        )
    finally:
        db.close()


def get_customers_paginated(filters: CustomerFilters, page: int, page_size: int) -> PaginatedCustomerResponse:
    db = next(get_db())
    try:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 200)  # hard cap to protect the API

        query = _apply_filters(_base_customer_query(db), filters)
        total_items = query.count()
        total_pages = max((total_items + page_size - 1) // page_size, 1)

        rows = (
            query.order_by(Customer.customer_id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items = [
            CustomerListItem(
                customer_id=c.customer_id, gender=c.gender, age=c.age, tenure=c.tenure,
                num_dependents=c.num_dependents, estimated_salary=c.estimated_salary,
                churn=c.churn, risk_category=c.risk_category, risk_score=c.risk_score,
                city=loc.city, state=loc.state, partner_name=partner.partner_name,
            )
            for c, loc, partner in rows
        ]
        logger.info(f"Fetched customer page {page}/{total_pages} ({len(items)} rows, filters={filters.model_dump(exclude_none=True)})")
        return PaginatedCustomerResponse(
            meta=PaginationMeta(page=page, page_size=page_size, total_items=total_items, total_pages=total_pages),
            items=items,
        )
    finally:
        db.close()


def get_customer_detail(customer_id: int) -> CustomerDetailResponse | None:
    db = next(get_db())
    try:
        row = (
            _base_customer_query(db)
            .filter(Customer.customer_id == customer_id)
            .first()
        )
        if row is None:
            logger.warning(f"Customer detail not found: {customer_id}")
            return None
        customer, loc, partner = row
        usage = db.query(CustomerUsage).filter(CustomerUsage.customer_id == customer_id).first()

        usage_breakdown = UsageBreakdown(
            calls_made=usage.calls_made if usage else 0,
            sms_sent=usage.sms_sent if usage else 0,
            data_used=usage.data_used if usage else 0.0,
        )

        # Mirrors the scoring rules documented for Phase2 calculate_risk_score()
        risk_factors = [
            RiskFactorBreakdown(label="Tenure < 180 days", points=2, triggered=customer.tenure < 180),
            RiskFactorBreakdown(label="Age between 18-30", points=1, triggered=18 <= customer.age <= 30),
            RiskFactorBreakdown(label="Dependents <= 1", points=1, triggered=customer.num_dependents <= 1),
            RiskFactorBreakdown(label="Calls made < 10", points=1, triggered=usage_breakdown.calls_made < 10),
            RiskFactorBreakdown(label="SMS sent < 20", points=1, triggered=usage_breakdown.sms_sent < 20),
            RiskFactorBreakdown(label="Data used < 1 GB", points=1, triggered=usage_breakdown.data_used < 1),
            RiskFactorBreakdown(
                label="High salary + low usage (income paradox)",
                points=1,
                triggered=bool(
                    customer.estimated_salary and customer.estimated_salary > 75000
                    and usage_breakdown.calls_made < 10 and usage_breakdown.data_used < 1
                ),
            ),
        ]

        logger.info(f"Fetched customer detail: {customer_id}")
        return CustomerDetailResponse(
            customer_id=customer.customer_id, gender=customer.gender, age=customer.age,
            pincode=customer.pincode, city=loc.city, state=loc.state,
            date_of_registration=str(customer.date_of_registration),
            tenure=customer.tenure, num_dependents=customer.num_dependents,
            estimated_salary=customer.estimated_salary, churn=customer.churn,
            partner_name=partner.partner_name, risk_score=customer.risk_score,
            risk_category=customer.risk_category, usage=usage_breakdown, risk_factors=risk_factors,
        )
    finally:
        db.close()


def get_churn_by_partner() -> list[ChurnByPartnerItem]:
    db = next(get_db())
    try:
        rows = (
            db.query(
                TelecomPartner.partner_name,
                func.count(Customer.customer_id).label("total"),
                func.sum(case((Customer.churn.is_(True), 1), else_=0)).label("churned"),
            )
            .join(Customer, Customer.telecom_partner_id == TelecomPartner.partner_id)
            .group_by(TelecomPartner.partner_name)
            .all()
        )
        logger.info("Fetched churn-by-partner aggregation")
        return [
            ChurnByPartnerItem(
                partner_name=r.partner_name, total_customers=r.total, churned_customers=r.churned or 0,
                churn_rate_pct=round(((r.churned or 0) / r.total) * 100, 2) if r.total else 0.0,
            )
            for r in rows
        ]
    finally:
        db.close()


def get_churn_by_state() -> list[ChurnByStateItem]:
    db = next(get_db())
    try:
        rows = (
            db.query(
                Location.state,
                func.count(Customer.customer_id).label("total"),
                func.sum(case((Customer.churn.is_(True), 1), else_=0)).label("churned"),
            )
            .join(Customer, Customer.pincode == Location.pincode)
            .group_by(Location.state)
            .all()
        )
        logger.info("Fetched churn-by-state aggregation")
        return [
            ChurnByStateItem(
                state=r.state, total_customers=r.total, churned_customers=r.churned or 0,
                churn_rate_pct=round(((r.churned or 0) / r.total) * 100, 2) if r.total else 0.0,
            )
            for r in rows
        ]
    finally:
        db.close()


def get_churn_by_age_bracket() -> list[ChurnByAgeBracketItem]:
    db = next(get_db())
    try:
        results = []
        for lo, hi in AGE_BRACKETS:
            q = db.query(Customer).filter(Customer.age >= lo, Customer.age <= hi)
            total = q.count()
            churned = q.filter(Customer.churn.is_(True)).count()
            label = f"{lo}-{hi}" if hi < 200 else "66+"
            results.append(ChurnByAgeBracketItem(
                age_bracket=label, total_customers=total, churned_customers=churned,
                churn_rate_pct=round((churned / total) * 100, 2) if total else 0.0,
            ))
        logger.info("Fetched churn-by-age-bracket aggregation")
        return results
    finally:
        db.close()


def get_risk_tier_split() -> list[RiskTierSplitItem]:
    db = next(get_db())
    try:
        total = db.query(func.count(Customer.customer_id)).scalar() or 0
        rows = (
            db.query(Customer.risk_category, func.count(Customer.customer_id).label("n"))
            .group_by(Customer.risk_category)
            .all()
        )
        logger.info("Fetched risk-tier split")
        return [
            RiskTierSplitItem(
                risk_category=r.risk_category, count=r.n,
                pct_of_total=round((r.n / total) * 100, 2) if total else 0.0,
            )
            for r in rows
        ]
    finally:
        db.close()


# def get_volume_treemap() -> list[TreemapNode]:
#     db = next(get_db())
#     try:
#         rows = (
#             db.query(
#                 TelecomPartner.partner_name,
#                 Location.state,
#                 func.count(Customer.customer_id).label("total"),
#                 func.sum(case((Customer.churn.is_(True), 1), else_=0)).label("churned"),
#             )
#             .join(Customer, Customer.telecom_partner_id == TelecomPartner.partner_id)
#             .join(Location, Customer.pincode == Location.pincode)
#             .group_by(TelecomPartner.partner_name, Location.state)
#             .all()
#         )
#         logger.info("Fetched volume treemap aggregation")
#         return [
#             TreemapNode(
#                 partner_name=r.partner_name, state=r.state, customer_count=r.total,
#                 churn_rate_pct=round(((r.churned or 0) / r.total) * 100, 2) if r.total else 0.0,
#             )
#             for r in rows
#         ]
#     finally:
#         db.close()


# def get_registration_heatmap(days: int = 120) -> RegistrationHeatmapResponse:
#     db = next(get_db())
#     try:
#         start = date.today() - timedelta(days=days)
#         rows = (
#             db.query(Customer.date_of_registration, func.count(Customer.customer_id).label("n"))
#             .filter(Customer.date_of_registration >= start)
#             .group_by(Customer.date_of_registration)
#             .all()
#         )
#         logger.info(f"Fetched registration heatmap ({len(rows)} days with data)")
#         return RegistrationHeatmapResponse(
#             points=[RegistrationHeatmapPoint(date=str(r.date_of_registration), count=r.n) for r in rows]
#         )
#     finally:
#         db.close()
