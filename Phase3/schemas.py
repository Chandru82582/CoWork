from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: int
    gender: str | None = None
    age: int | None = None
    pincode: str | None = None
    date_of_registration: str | None = None
    num_dependents: int | None = None
    estimated_salary: float | None = None
    churn: bool | None = None


class ChurnSummaryMetrics(BaseModel):
    total_customers: int
    churned_customers: int
    churn_rate: float
    retained_customers: int
    retention_rate: float


class PartnerChurnBreakdown(BaseModel):
    partner_name: str
    total_customers: int
    churned_customers: int
    churn_rate: float


class ChurnSummaryResponse(BaseModel):
    summary: ChurnSummaryMetrics
    partner_breakdown: list[PartnerChurnBreakdown] = []


class HighRiskCustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: int
    gender: str | None = None
    age: int | None = None
    pincode: str | None = None
    city: str | None = None
    state: str | None = None
    date_of_registration: str | None = None
    num_dependents: int | None = None
    estimated_salary: float | None = None
    churn: bool | None = None
    tenure: int | None = None
    calls_made: int | None = None
    sms_sent: int | None = None
    data_used: float | None = None
    partner_name: str | None = None
    risk_category: str
    risk_score: int


class HighRiskCustomersListResponse(BaseModel):
    total_high_risk_customers: int
    customers: list[HighRiskCustomerResponse]


class ChurnPredictionInput(BaseModel):
    """Pydantic model for churn prediction features.
    
    This model validates customer features for ML model predictions.
    All fields are optional to allow flexible feature selection.
    """
    model_config = ConfigDict(from_attributes=True)

    customer_id: int | None = None
    age: int | None = None
    gender: str | None = None
    tenure: int | None = None
    num_dependents: int | None = None
    estimated_salary: float | None = None
    calls_made: int | None = None
    sms_sent: int | None = None
    data_used: float | None = None
    telecom_partner: str | None = None
    pincode: str | None = None


class ChurnPredictionOutput(BaseModel):
    """Pydantic model for churn prediction output."""
    customer_id: int | None = None
    churn_probability: float  # 0.0 to 1.0
    churn_prediction: bool  # True = will churn, False = will not churn
    confidence_score: float  # 0.0 to 1.0
    risk_level: str  # "Low", "Medium", "High"
    recommendation: str  # Action to take
    model_votes: dict[str, int] | None = None   # <-- new: {"logistic_regression": 0, "random_forest": 1, "xgboost": 1}


# ---------- KPI cards ----------

class KpiTrend(BaseModel):
    current_period_value: float
    previous_period_value: float
    delta_pct: Optional[float] = None  # None if previous period had no data (avoid div/0)


class KpiSummaryResponse(BaseModel):
    total_customers: int
    churn_rate_pct: float
    high_risk_count: int
    arpu: Optional[float] = None
    arpu_note: Optional[str] = (
        "ARPU is unavailable: the customers table has no revenue/billing column. "
        "Add a monthly_revenue (or plan_cost) field to enable this metric."
    )
    new_customers_trend: KpiTrend
    churn_rate_trend: KpiTrend
    high_risk_trend: KpiTrend
    trend_methodology_note: str = (
        "Trends compare customers registered in the last 30 days vs. the prior 30 days "
        "(cohort proxy). The schema has no churn-event date, so true period-over-period "
        "churn trend requires adding a churn_date column."
    )

    model_config = ConfigDict(from_attributes=True)


# ---------- Paginated / filterable customer list ----------

class CustomerListItem(BaseModel):
    customer_id: int
    gender: str
    age: int
    tenure: int
    num_dependents: int
    estimated_salary: Optional[float]
    churn: bool
    risk_category: str
    risk_score: int
    city: str
    state: str
    partner_name: str


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class PaginatedCustomerResponse(BaseModel):
    meta: PaginationMeta
    items: list[CustomerListItem]


# ---------- Customer detail drawer ----------

class UsageBreakdown(BaseModel):
    calls_made: int
    sms_sent: int
    data_used: float


class RiskFactorBreakdown(BaseModel):
    label: str
    points: int
    triggered: bool


class CustomerDetailResponse(BaseModel):
    customer_id: int
    gender: str
    age: int
    pincode: str
    city: str
    state: str
    date_of_registration: str
    tenure: int
    num_dependents: int
    estimated_salary: Optional[float]
    churn: bool
    partner_name: str
    risk_score: int
    risk_category: str
    usage: UsageBreakdown
    risk_factors: list[RiskFactorBreakdown]


# ---------- Aggregation charts ----------

class ChurnByPartnerItem(BaseModel):
    partner_name: str
    total_customers: int
    churned_customers: int
    churn_rate_pct: float


class ChurnByStateItem(BaseModel):
    state: str
    total_customers: int
    churned_customers: int
    churn_rate_pct: float


class ChurnByAgeBracketItem(BaseModel):
    age_bracket: str
    total_customers: int
    churned_customers: int
    churn_rate_pct: float


class RiskTierSplitItem(BaseModel):
    risk_category: str
    count: int
    pct_of_total: float


class TreemapNode(BaseModel):
    partner_name: str
    state: str
    customer_count: int
    churn_rate_pct: float


class RegistrationHeatmapPoint(BaseModel):
    date: str  # YYYY-MM-DD
    count: int


class RegistrationHeatmapResponse(BaseModel):
    points: list[RegistrationHeatmapPoint]
    note: str = (
        "This heatmap shows new-registration density, not churn events — the schema "
        "has no churn_date column. Add one to enable a true churn-event heatmap."
    )


# ---------- Shared filter params (used by the /dashboard/customers route) ----------

class CustomerFilters(BaseModel):
    partner_names: Optional[list[str]] = None
    states: Optional[list[str]] = None
    cities: Optional[list[str]] = None
    risk_categories: Optional[list[str]] = None
    tenure_min: Optional[int] = None
    tenure_max: Optional[int] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    search: Optional[str] = None  # matches customer_id (exact) or city (partial)
