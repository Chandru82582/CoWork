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
