from pydantic import BaseModel, ConfigDict


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
