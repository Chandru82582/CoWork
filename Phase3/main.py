import logging
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware

from auth import authenticate_admin, get_current_admin_user
from schemas import (
    ChurnPredictionInput,
    ChurnPredictionOutput,
    ChurnSummaryResponse,
    CustomerResponse,
    HighRiskCustomersListResponse,
)
from rules import get_churn_summary as get_churn_summary_service
from rules import get_customer_by_id, get_high_risk_customers
from ml_model import predict_churn_ensemble

from Phase3.routes import router as dashboard_router

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("telecom_api.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


app = FastAPI(title="Telecom Customer API")
app.include_router(dashboard_router)

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


@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    logger.info("=" * 50)
    logger.info("Telecom Customer API Starting Up")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown."""
    logger.info("=" * 50)
    logger.info("Telecom Customer API Shutting Down")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("=" * 50)


@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """User login endpoint."""
    logger.info(f"Login attempt for user: {form_data.username}")
    return authenticate_admin(form_data.username, form_data.password)


@app.get("/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, current_user: dict = Depends(get_current_admin_user)):
    """Retrieve a customer by ID."""
    logger.info(f"Fetching customer: {customer_id}")
    customer = get_customer_by_id(customer_id)

    if not customer:
        logger.warning(f"Customer not found: {customer_id}")
        raise HTTPException(status_code=404, detail="Customer not found")

    logger.debug(f"Successfully retrieved customer: {customer_id}")
    return customer


@app.get("/churn/summary", response_model=ChurnSummaryResponse)
def get_churn_summary(current_user: dict = Depends(get_current_admin_user)):
    """Retrieve churn summary statistics."""
    logger.info("Fetching churn summary")
    summary = get_churn_summary_service()
    logger.debug("Churn summary retrieved successfully")
    return summary


@app.post("/customers/risk-analysis/high-risk", response_model=HighRiskCustomersListResponse)
def get_high_risk_customers_endpoint(current_user: dict = Depends(get_current_admin_user)):
    """
    Retrieve all customers categorized as High Risk based on churn risk factors.
    
    **Note:** This endpoint fetches pre-calculated risk scores from the database for optimal performance.
    Risk scores are calculated during data insertion using the following factors:
    
    Risk Scoring Factors:
    - Tenure < 180 days: +2 points
    - Age 18-30: +1 point
    - ≤1 dependent: +1 point
    - < 10 calls made: +1 point
    - < 20 SMS sent: +1 point
    - < 1 GB data used: +1 point
    - High salary (>$75k) + low calls + low data: +1 point
    
    Categorization:
    - Score ≥ 6: High Risk
    - Score 3-5: Medium Risk
    - Score < 3: Low Risk
    """
    logger.info("Fetching high risk customers")
    high_risk = get_high_risk_customers()
    logger.info(f"Retrieved {high_risk.total_high_risk_customers} high risk customers")
    return high_risk


@app.post("/ml/predict-churn", response_model=ChurnPredictionOutput)
def predict_churn_endpoint(
    features: ChurnPredictionInput,
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Predict churn probability for a customer using a 3-model majority vote
    (logistic regression, random forest, xgboost).
    """
    logger.info(f"Churn prediction request for customer: {features.customer_id}")
    logger.debug(f"Features provided: {features.dict()}")

    try:
        result = predict_churn_ensemble(features)
    except FileNotFoundError as e:
        logger.error(f"Model artifacts missing: {e}")
        raise HTTPException(status_code=503, detail="Prediction models are unavailable. Contact an administrator.")
    except Exception as e:
        logger.error(f"Prediction failed for customer {features.customer_id}: {e}")
        raise HTTPException(status_code=500, detail="Prediction failed.")

    prediction = ChurnPredictionOutput(
        customer_id=features.customer_id,
        churn_probability=result["churn_probability"],
        churn_prediction=result["churn_prediction"],
        confidence_score=result["confidence_score"],
        risk_level=result["risk_level"],
        recommendation=result["recommendation"],
        model_votes=result["model_votes"],
    )

    logger.info(
        f"Churn prediction completed for customer {features.customer_id}: "
        f"Risk={prediction.risk_level}, "
        f"Probability={prediction.churn_probability:.2%}, "
        f"Votes={result['model_votes']}"
    )

    return prediction


@app.get("/health")
def health_check():
    """Health check endpoint."""
    logger.debug("Health check requested")
    return {"status": "healthy", "timestamp": datetime.now()}
