from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from auth import authenticate_admin, get_current_admin_user
from schemas import ChurnSummaryResponse, CustomerResponse
from services import get_churn_summary as get_churn_summary_service
from services import get_customer_by_id


app = FastAPI(title="Telecom Customer API")


@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    return authenticate_admin(form_data.username, form_data.password)


@app.get("/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, current_user: dict = Depends(get_current_admin_user)):
    customer = get_customer_by_id(customer_id)

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return customer


@app.get("/churn/summary", response_model=ChurnSummaryResponse)
def get_churn_summary(current_user: dict = Depends(get_current_admin_user)):
    return get_churn_summary_service()
