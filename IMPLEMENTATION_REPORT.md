# CoWork Project - Detailed Implementation Report
**Date:** 2026-08-14  
**Status:** Active Development  
**Technology Stack:** Python 3.14 | FastAPI | SQLAlchemy ORM | MySQL 8.0 | Pydantic v2

---

## 1. PROJECT OVERVIEW

### Purpose
Telecom customer churn prediction system with:
- High-performance parallel data ingestion (Phase 2)
- REST API for customer analytics and risk analysis (Phase 3)
- ML-ready architecture for future churn prediction model integration
- Comprehensive logging and observability

### Directory Structure
```
d:\CoWork\
├── preprocessor.py                    # Root-level data preprocessing utility
├── data/
│   ├── telecom_churn.csv             # Original raw dataset
│   ├── telecom_churn_processed.csv   # Processed/cleaned dataset
│   └── WA_Fn-UseC_-Telco-Customer-Churn.csv  # Alternative data source
├── Phase1/                            # Data exploration & analysis notebooks
│   ├── *.ipynb                       # Multiple Jupyter notebooks
│   ├── preprocess.py                 # Python preprocessing scripts
│   └── telecom_preprocessing.py
├── Phase2/                            # Data ingestion layer
│   ├── database.py                   # SQLAlchemy ORM models
│   ├── datainsertion.py              # Parallel data insertion script
│   ├── cvsfile.py                    # CSV utilities
│   ├── telecom_churn.csv             # Local copy of source data
│   ├── data_insertion.log            # Execution logs
│   └── README.md                     # Phase 2 documentation
└── Phase3/                            # API/Query layer
    ├── __init__.py
    ├── main.py                       # FastAPI application (current focus)
    ├── auth.py                       # OAuth2 authentication
    ├── database.py                   # SQLAlchemy models (mirror of Phase2)
    ├── schemas.py                    # Pydantic validation models
    ├── rules.py                      # Business logic & queries
    ├── telecom_churn.csv             # Local copy of data
    └── telecom_api.log               # API execution logs
```

---

## 2. ARCHITECTURE & DESIGN

### Two-Phase Architecture

#### Phase 2: Data Ingestion Layer
**Purpose:** Load CSV data into MySQL with high performance  
**Approach:** Parallel multiprocessing with two-phase strategy

**Phase 2A - Synchronous Parent Pre-population:**
1. Main process reads entire CSV into memory
2. Identifies unique `TelecomPartner` and `Location` records
3. Deduplicates by `pincode` (handles CSV inconsistencies)
4. Bulk inserts new parent records to database
5. Creates `partner_name → partner_id` mapping
6. Enriches in-memory CSV with foreign keys

**Phase 2B - Parallel Child Ingestion:**
1. Splits enriched customer data into chunks (by CPU core count)
2. Spawns worker processes via `multiprocessing.Pool`
3. Each worker creates independent SQLAlchemy session
4. Processes chunk: creates `Customer` and `CustomerUsage` objects
5. Single atomic `session.commit()` per worker
6. **Pre-calculates and stores risk scores during insertion** (performance optimization)

**Key File:** [d:\CoWork\Phase2\datainsertion.py](d:\CoWork\Phase2\datainsertion.py)

#### Phase 3: API/Query Layer
**Purpose:** Expose analytics and risk analysis via REST API  
**Approach:** Read-only fetch layer with pre-calculated values

**Process:**
1. Receives authenticated HTTP requests
2. Queries pre-calculated data from MySQL (no computation)
3. Returns Pydantic-validated responses
4. Logs all activity

**Key File:** [d:\CoWork\Phase3\main.py](d:\CoWork\Phase3\main.py)

---

## 3. DATABASE SCHEMA

### MySQL Database
**Name:** `telecom_updated_db`  
**Host:** localhost  
**User:** root  
**Password:** root

### Table Structure

#### `telecom_partner` Table
```python
partner_id (INT, PK, autoincrement)
partner_name (VARCHAR(50), UNIQUE)
```
**Relationships:** One-to-Many with `customers`

#### `locations` Table
```python
pincode (VARCHAR(10), PK)
city (VARCHAR(100))
state (VARCHAR(100))
```
**Relationships:** One-to-Many with `customers`

#### `customers` Table
```python
customer_id (INT, PK)
telecom_partner_id (INT, FK → telecom_partner.partner_id)
gender (ENUM: Male, Female, Other)
age (INT)
pincode (VARCHAR(10), FK → locations.pincode)
date_of_registration (DATE)
tenure (INT)
num_dependents (INT)
estimated_salary (DECIMAL)
churn (BOOLEAN)
risk_score (INT, default=0, nullable)          ← NEW
risk_category (VARCHAR(20), default='Low Risk', nullable)  ← NEW
```
**Relationships:** Many-to-One with `telecom_partner`, `locations`; One-to-Many with `customer_usage`

#### `customer_usage` Table
```python
customer_id (INT, FK → customers.customer_id)
calls_made (INT)
sms_sent (INT)
data_used (FLOAT)
```
**Relationships:** Many-to-One with `customers`

### SQLAlchemy Models
**Location:** [d:\CoWork\Phase3\database.py](d:\CoWork\Phase3\database.py) (identical to Phase2)

---

## 4. RISK SCORING ALGORITHM

### Implementation Location
**Phase 2:** Calculated during data insertion in [d:\CoWork\Phase2\datainsertion.py](d:\CoWork\Phase2\datainsertion.py#L48)  
**Function:** `calculate_risk_score(customer_data, usage_data)`

### Scoring System (7-Point Scale)
```
Base Score = 0

+2 points if: tenure < 180 days
+1 point  if: age between 18-30
+1 point  if: num_dependents ≤ 1
+1 point  if: calls_made < 10
+1 point  if: sms_sent < 20
+1 point  if: data_used < 1 GB
+1 point  if: (estimated_salary > 75,000) AND (calls_made < 10) AND (data_used < 1)

Maximum Possible Score: 7
```

### Risk Categorization
```
Score ≥ 6  →  HIGH RISK   (action required)
Score 3-5  →  MEDIUM RISK (monitor)
Score < 3  →  LOW RISK    (stable)
```

### Rationale
- **Tenure:** New customers churn more frequently
- **Age:** 18-30 age group has higher churn propensity
- **Dependents:** Fewer dependents = more flexible to switch
- **Engagement:** Low calls/SMS/data = low engagement = churn risk
- **Income Paradox:** High earners with low usage are at risk (likely switching to premium competitors)

### Performance Optimization
- **Moved from query-time to insertion-time:** Initially calculated per-request (slow); now calculated once and stored
- **Stored in database:** Phase 3 API fetches pre-calculated `risk_score` and `risk_category` columns
- **Benefit:** Query response time independent of customer volume

---

## 5. API ENDPOINTS & SECURITY

### Authentication Scheme
**Type:** OAuth2 Password Bearer  
**Credentials:**
- Username: `admin`
- Password: `secret`
- Token: `admin-token` (returned on login)

**Implementation:** [d:\CoWork\Phase3\auth.py](d:\CoWork\Phase3\auth.py)

### Endpoints

#### 1. **Authentication**
```
POST /token
Content-Type: application/x-www-form-urlencoded

username=admin&password=secret

Response:
{
  "access_token": "admin-token",
  "token_type": "bearer"
}
```
**Logging:** Logs login attempts (username only, not password)  
**Status:** ✅ Implemented

---

#### 2. **Get Customer Details**
```
GET /customers/{customer_id}
Authorization: Bearer admin-token

Response: CustomerResponse
{
  "customer_id": 1001,
  "gender": "Male",
  "age": 45,
  "pincode": "12345",
  "date_of_registration": "2020-01-15",
  "num_dependents": 2,
  "estimated_salary": 75000.50,
  "churn": false
}
```
**Logging:** Logs customer ID fetched; warns if 404  
**Status:** ✅ Implemented

---

#### 3. **Get Churn Summary**
```
GET /churn/summary
Authorization: Bearer admin-token

Response: ChurnSummaryResponse
{
  "summary": {
    "total_customers": 7043,
    "churned_customers": 1869,
    "churn_rate": 26.54,
    "retained_customers": 5174,
    "retention_rate": 73.46
  },
  "partner_breakdown": [
    {
      "partner_name": "Partner A",
      "total_customers": 2500,
      "churned_customers": 650,
      "churn_rate": 26.00
    },
    ...
  ]
}
```
**Logging:** Logs churn summary retrieval  
**Status:** ✅ Implemented

---

#### 4. **Get High-Risk Customers**
```
POST /customers/risk-analysis/high-risk
Authorization: Bearer admin-token

Response: HighRiskCustomersListResponse
{
  "total_high_risk_customers": 127,
  "customers": [
    {
      "customer_id": 1001,
      "gender": "Male",
      "age": 28,
      "pincode": "10001",
      "date_of_registration": "2025-02-01",
      "num_dependents": 0,
      "estimated_salary": 45000.00,
      "churn": false,
      "tenure": 100,
      "calls_made": 5,
      "sms_sent": 8,
      "data_used": 0.5,
      "city": "New York",
      "state": "NY",
      "partner_name": "Partner A",
      "risk_category": "High Risk",
      "risk_score": 6
    },
    ...
  ]
}
```
**Filtering:** Fetches ONLY `risk_category == "High Risk"` from database  
**Logging:** Logs total high-risk count retrieved  
**Status:** ✅ Implemented

---

#### 5. **Predict Churn (ML Placeholder)**
```
POST /ml/predict-churn
Authorization: Bearer admin-token
Content-Type: application/json

Request: ChurnPredictionInput (all fields optional)
{
  "customer_id": 1001,
  "age": 28,
  "gender": "Male",
  "tenure": 100,
  "num_dependents": 0,
  "estimated_salary": 45000.00,
  "calls_made": 5,
  "sms_sent": 8,
  "data_used": 0.5,
  "telecom_partner": "Partner A",
  "pincode": "10001"
}

Response: ChurnPredictionOutput
{
  "customer_id": 1001,
  "churn_probability": 0.35,
  "churn_prediction": false,
  "confidence_score": 0.82,
  "risk_level": "Medium",
  "recommendation": "Monitor customer engagement and consider retention offers"
}
```
**Status:** ✅ Skeleton Implemented (returns dummy predictions)  
**TODO:** Replace dummy logic with actual ML model  
**Logging:** Logs request features and prediction results  
**Note:** Designed for future integration with trained sklearn/TensorFlow model

---

#### 6. **Health Check**
```
GET /health
(No authentication required)

Response:
{
  "status": "healthy",
  "timestamp": "2026-08-14T15:30:45.123456"
}
```
**Logging:** Debug-level log on each check  
**Status:** ✅ Implemented  
**Use Case:** Container orchestration, monitoring dashboards, uptime checks

---

## 6. PYDANTIC MODELS & VALIDATION

**Location:** [d:\CoWork\Phase3\schemas.py](d:\CoWork\Phase3\schemas.py)

### Request Models

#### ChurnPredictionInput
```python
class ChurnPredictionInput(BaseModel):
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
    
    model_config = ConfigDict(from_attributes=True)
```
**Purpose:** Flexible feature validation (all optional to support partial feature sets)  
**Use Case:** Future ML model ingestion

### Response Models

#### CustomerResponse
```python
class CustomerResponse(BaseModel):
    customer_id: int
    gender: str
    age: int
    pincode: str
    date_of_registration: str
    num_dependents: int
    estimated_salary: float | None
    churn: bool
```

#### ChurnSummaryResponse
```python
class ChurnSummaryResponse(BaseModel):
    summary: ChurnSummaryMetrics
    partner_breakdown: list[PartnerChurnBreakdown]
```

#### HighRiskCustomerResponse
```python
class HighRiskCustomerResponse(BaseModel):
    customer_id: int
    gender: str
    age: int
    pincode: str
    date_of_registration: str
    num_dependents: int
    estimated_salary: float | None
    churn: bool
    tenure: int
    calls_made: int
    sms_sent: int
    data_used: float
    city: str
    state: str
    partner_name: str
    risk_category: str
    risk_score: int
```

#### ChurnPredictionOutput
```python
class ChurnPredictionOutput(BaseModel):
    customer_id: int | None = None
    churn_probability: float  # 0.0 to 1.0
    churn_prediction: bool    # True = will churn, False = won't
    confidence_score: float   # 0.0 to 1.0
    risk_level: str          # "Low", "Medium", "High"
    recommendation: str      # Action recommendation
```

---

## 7. LOGGING CONFIGURATION

### Setup Location
[d:\CoWork\Phase3\main.py](d:\CoWork\Phase3\main.py) (lines 19-28)

### Configuration
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("telecom_api.log"),  # Persistent disk file
        logging.StreamHandler(),                 # Console output
    ],
)
```

### Log File Location
**Path:** `d:\CoWork\Phase3\telecom_api.log`  
**Format:** `YYYY-MM-DD HH:MM:SS,mmm - module - LEVEL - message`

### Logged Events

| Endpoint | Event | Level | Format |
|----------|-------|-------|--------|
| *Startup* | API starts | INFO | `"Telecom Customer API Starting Up"` + timestamp |
| *Shutdown* | API stops | INFO | `"Telecom Customer API Shutting Down"` + timestamp |
| `/token` | Login attempt | INFO | `"Login attempt for user: {username}"` |
| `/customers/{id}` | Customer fetch | INFO | `"Fetching customer: {id}"` |
| | Not found | WARNING | `"Customer not found: {id}"` |
| | Success | DEBUG | `"Successfully retrieved customer: {id}"` |
| `/churn/summary` | Fetch summary | INFO | `"Fetching churn summary"` |
| | Success | DEBUG | `"Churn summary retrieved successfully"` |
| `/customers/risk-analysis/high-risk` | Fetch high-risk | INFO | `"Fetching high risk customers"` |
| | Complete | INFO | `"Retrieved {count} high risk customers"` |
| `/ml/predict-churn` | Prediction request | INFO | `"Churn prediction request for customer: {id}"` |
| | Features | DEBUG | `"Features provided: {dict}"` |
| | Complete | INFO | `"Churn prediction completed for customer {id}: Risk={level}, Probability={%}"` |
| `/health` | Health check | DEBUG | `"Health check requested"` |

### Sample Log Output
```
2026-08-14 14:55:17,693 - main - INFO - ==================================================
2026-08-14 14:55:17,693 - main - INFO - Telecom Customer API Starting Up
2026-08-14 14:55:17,694 - main - INFO - Timestamp: 2026-08-14 14:55:17.694000
2026-08-14 14:55:17,694 - main - INFO - ==================================================
2026-08-14 14:59:32,566 - main - INFO - Login attempt for user: admin
2026-08-14 15:00:15,123 - main - INFO - Fetching high risk customers
2026-08-14 15:00:15,456 - main - INFO - Retrieved 127 high risk customers
2026-08-14 15:01:30,789 - main - INFO - Churn prediction request for customer: 1001
2026-08-14 15:01:30,890 - main - DEBUG - Features provided: {'customer_id': 1001, 'age': 28, ...}
2026-08-14 15:01:30,950 - main - INFO - Churn prediction completed for customer 1001: Risk=Medium, Probability=35.00%
```

---

## 8. BUSINESS LOGIC LAYER

**Location:** [d:\CoWork\Phase3\rules.py](d:\CoWork\Phase3\rules.py)

### Functions

#### `get_customer_by_id(customer_id: int) → CustomerResponse`
- **Query:** Direct PK lookup on `customers` table
- **Return:** Single customer details
- **Error:** Returns `None` if not found (endpoint returns 404)
- **Performance:** O(1) - indexed primary key

#### `get_churn_summary() → ChurnSummaryResponse`
- **Query 1:** Aggregate totals and churned count across all customers
- **Query 2:** Group-by telecom partner with churn breakdown
- **Calculations:** Churn rate, retention rate, per-partner statistics
- **Performance:** O(n) scan with aggregations, but reasonable for analytics queries
- **Note:** Uses SQLAlchemy `func.count()`, `func.sum()`, `case()` for SQL aggregations

#### `get_high_risk_customers() → HighRiskCustomersListResponse`
- **Query:** Filter `customers` table where `risk_category == "High Risk"`
- **Joins:** Fetches related `telecom_partner`, `location`, `customer_usage` data
- **Performance:** O(k) where k = number of high-risk customers (typically < 300 out of 7000)
- **Optimization:** Pre-calculated risk scores eliminate runtime computation
- **Return:** Full customer details + risk metadata

### Database Session Management
```python
db = next(get_db())  # Generator-based session from database.py
```
**Note:** Each function creates its own session; auto-closes after function

---

## 9. CURRENT IMPLEMENTATION STATUS

### ✅ Completed Features

| Feature | Component | Status | Details |
|---------|-----------|--------|---------|
| **Database Schema** | MySQL with 4 tables | ✅ | Telecom Partner, Locations, Customers, Customer Usage |
| **Risk Scoring Algorithm** | 7-point scale | ✅ | Implemented with 3-tier categorization |
| **Data Insertion Pipeline** | Phase 2 Multiprocessing | ✅ | Parallel ingestion with risk calculation |
| **Authentication** | OAuth2 Bearer | ✅ | Admin credential verification |
| **Customer Lookup** | GET /customers/{id} | ✅ | Single customer retrieval with logging |
| **Churn Summary** | GET /churn/summary | ✅ | Aggregate statistics + partner breakdown |
| **High-Risk Analysis** | POST /customers/risk-analysis/high-risk | ✅ | Fetch pre-calculated high-risk customers |
| **Health Check** | GET /health | ✅ | Uptime monitoring endpoint |
| **Logging Infrastructure** | FileHandler + StreamHandler | ✅ | Persistent file + console logs |
| **Startup/Shutdown Logging** | Lifecycle events | ✅ | Timestamped API lifecycle tracking |
| **Per-Endpoint Logging** | All endpoints | ✅ | INFO/DEBUG/WARNING level logging |
| **Pydantic Models** | Input validation | ✅ | ChurnPredictionInput/Output defined |
| **API Documentation** | FastAPI auto-docs | ✅ | Swagger UI at /docs (auto-generated) |

### 🔄 Partially Complete Features

| Feature | Component | Status | Details |
|---------|-----------|--------|---------|
| **ML Prediction Endpoint** | /ml/predict-churn | 🔄 | Skeleton implemented; returns dummy predictions |
| **Database Migration** | risk_score/risk_category columns | 🔄 | Columns added to ORM models; MySQL ALTER needed |
| **Data Reload** | Phase 2 datainsertion.py | 🔄 | Script ready; blocked on MySQL schema update |

### ⏳ Remaining Tasks

| Task | Priority | Component | Details |
|------|----------|-----------|---------|
| **Execute MySQL Migration** | HIGH | Database | Add risk_score & risk_category columns to existing customers table (ALTER TABLE) |
| **Reload Customer Data** | HIGH | Phase 2 | Re-run datainsertion.py to populate risk scores for all customers |
| **Integrate ML Model** | MEDIUM | Phase 3 | Replace dummy predictions in /ml/predict-churn with actual model |
| **Model Versioning** | MEDIUM | Phase 3 | Add model version tracking to predictions (for A/B testing) |
| **Feature Engineering** | MEDIUM | Phase 2 | Add derived features (e.g., usage_trend, contract_type_risk) |
| **Error Handling** | MEDIUM | Phase 3 | Add graceful degradation for model unavailability |
| **Monitoring Dashboard** | LOW | Observability | Parse telecom_api.log for visualization |
| **API Rate Limiting** | LOW | Security | Add request throttling to /ml/predict-churn |

---

## 10. IMPORTANT ARCHITECTURAL DECISIONS

### 1. **Risk Calculation Moved to Insertion Time**
**Decision:** Pre-calculate and store risk scores during data load  
**Rationale:**
- Initial approach calculated risk per-request (slow with 7000+ customers)
- Moved to insertion pipeline (Phase 2 datainsertion.py)
- Phase 3 only fetches pre-calculated values (fast O(1) lookups)
- Trade-off: Slightly larger database (adds 2 columns) for dramatic query speedup

### 2. **Phase 3 is Read-Only Fetch Layer**
**Decision:** No computation in API; only database queries  
**Rationale:**
- Simplifies API to pure data-retrieval operations
- Enables horizontal scaling (multiple API instances)
- Risk logic centralized in Phase 2 (single source of truth)
- Future ML model predictions return pre-computed results (from batch job, not real-time)

### 3. **Pydantic Model with `from_attributes=True`**
**Decision:** Enable SQLAlchemy ORM model → Pydantic conversion  
**Rationale:**
- Seamless serialization of ORM objects to JSON
- Type safety and validation at API boundary
- Makes future response format changes easy

### 4. **Logging to Both File and Console**
**Decision:** Dual-stream logging configuration  
**Rationale:**
- File logging for persistent audit trail (debugging, compliance)
- Console logging for real-time development/monitoring
- Both streams use same format for consistency

### 5. **All Endpoints Require Authentication Except `/health`**
**Decision:** Admin-only access to analytics endpoints  
**Rationale:**
- Sensitive customer data (high-risk customers, churn info, salary ranges)
- Health check is exception for monitoring systems (requires no auth)
- Simple credentials for POC; upgrade to JWT/AD in production

### 6. **Optional Fields in ChurnPredictionInput**
**Decision:** All customer features marked as optional  
**Rationale:**
- Supports ensemble models (different models use different features)
- Allows feature importance analysis (predicting with/without specific features)
- Future model may not require all fields

---

## 11. CODEBASE CONVENTIONS & STANDARDS

### File Organization
- **Separation of Concerns:** Database (models) | Business Logic (rules) | Presentation (schemas) | API (main)
- **Phase 2 files stay in Phase 2:** Don't modify Phase 2 unless data ingestion changes
- **Phase 3 files stay in Phase 3:** API layer is independent

### Naming Conventions
- **Classes:** PascalCase (e.g., `CustomerResponse`, `ChurnPredictionInput`)
- **Functions:** snake_case (e.g., `get_customer_by_id()`, `calculate_risk_score()`)
- **Constants:** UPPER_SNAKE_CASE (e.g., `ADMIN_USERNAME`, `ADMIN_TOKEN`)
- **Variables:** snake_case

### Logging Usage
```python
# For successful operations
logger.info(f"Action occurred: {details}")

# For debugging/tracing
logger.debug(f"Detailed operation info: {data}")

# For problems that don't stop execution
logger.warning(f"Unexpected condition: {issue}")

# For errors that cause failure
logger.error(f"Operation failed: {exception}")
```

### Error Handling
- **Database Errors:** Caught in Phase 2 datainsertion.py, logged, continue processing
- **API Errors:** Return FastAPI HTTPException with status codes (400, 401, 403, 404, 500)
- **Validation Errors:** Pydantic automatically returns 422 Unprocessable Entity

### Database Transactions
- **Phase 2:** Each worker performs single `session.commit()` per chunk (atomic)
- **Phase 3:** Each query creates new session, auto-closes (no explicit commit needed for reads)

### Testing Approach
- Use `/health` endpoint for basic connectivity
- Use `/customers/1001` (or any valid ID) to test authentication + data retrieval
- Use `/churn/summary` to test aggregation queries
- Use `/ml/predict-churn` with sample input to test prediction pipeline

### Dependency Management
```python
from fastapi import Depends

# Authentication dependency
def get_current_admin_user(current_user: dict = Depends(get_current_user)):
    ...

# Database dependency  
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## 12. DEVELOPMENT WORKFLOW

### Local Setup (for Future Developers)
```bash
# 1. Navigate to workspace
cd d:\CoWork\Phase3

# 2. Activate Python environment (if using venv)
# python -m venv venv
# venv\Scripts\activate

# 3. Install dependencies
pip install fastapi uvicorn sqlalchemy mysql-connector-python pydantic

# 4. Start API server
python -m uvicorn main:app --reload

# Server will start at http://localhost:8000
# Swagger UI at http://localhost:8000/docs
# ReDoc at http://localhost:8000/redoc
```

### API Testing

#### Using Swagger UI
1. Navigate to `http://localhost:8000/docs`
2. Click "Authorize" button
3. Enter username: `admin`, password: `secret`
4. Click "Try it out" on any endpoint

#### Using curl
```bash
# Get token
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=secret"

# Use token
TOKEN="admin-token"
curl -X GET "http://localhost:8000/churn/summary" \
  -H "Authorization: Bearer $TOKEN"
```

#### Using Python requests
```python
import requests

BASE_URL = "http://localhost:8000"
creds = {"username": "admin", "password": "secret"}

# Login
r = requests.post(f"{BASE_URL}/token", data=creds)
token = r.json()["access_token"]

# Fetch data
headers = {"Authorization": f"Bearer {token}"}
summary = requests.get(f"{BASE_URL}/churn/summary", headers=headers).json()
print(summary)
```

### Debugging

**Check logs in real-time:**
```bash
tail -f d:\CoWork\Phase3\telecom_api.log
```

**Check MySQL connection:**
```bash
mysql -u root -p -h localhost -e "USE telecom_updated_db; SELECT COUNT(*) FROM customers;"
```

**Test specific endpoint:**
```bash
# Health check (no auth)
curl http://localhost:8000/health

# With auth token
curl -H "Authorization: Bearer admin-token" \
  http://localhost:8000/customers/1001
```

---

## 13. NEXT STEPS FOR CONTINUATION

### Immediate Priority Tasks

#### 1. **Verify MySQL Database State**
```sql
-- Check if risk columns exist
DESC telecom_updated_db.customers;

-- If missing, run:
ALTER TABLE customers 
ADD COLUMN risk_score INT DEFAULT 0 NULL,
ADD COLUMN risk_category VARCHAR(20) DEFAULT 'Low Risk' NULL;
```

#### 2. **Reload Data with Risk Scores**
```bash
cd d:\CoWork\Phase2
python datainsertion.py
```
**Expected:** All customers will have risk_score and risk_category populated

#### 3. **Test API Endpoints**
```bash
cd d:\CoWork\Phase3
python -m uvicorn main:app --reload

# Then test using Swagger UI or curl
```

#### 4. **Integrate Real ML Model**
**File to modify:** [d:\CoWork\Phase3\main.py](d:\CoWork\Phase3\main.py) (lines 186-220)

**Current code:**
```python
# TODO: Replace with actual ML model prediction
dummy_prediction = ChurnPredictionOutput(...)
```

**What to replace with:**
```python
# Load trained model
import pickle
with open('churn_model.pkl', 'rb') as f:
    model = pickle.load(f)

# Prepare features from input
feature_array = prepare_features(features)

# Get prediction
prob = model.predict_proba(feature_array)[0][1]
prediction = prob > 0.5

# Return real prediction
return ChurnPredictionOutput(
    customer_id=features.customer_id,
    churn_probability=float(prob),
    churn_prediction=bool(prediction),
    confidence_score=max(prob, 1-prob),
    risk_level=categorize_risk(prob),
    recommendation=get_recommendation(prob)
)
```

#### 5. **Add Monitoring/Alerting**
- Parse telecom_api.log for errors
- Track prediction accuracy over time
- Monitor database query performance
- Alert on high error rates

---

## 14. KEY CONTACTS & RESOURCES

### Code Owners
- **Phase 2 (Data Ingestion):** datainsertion.py - Multiprocessing logic
- **Phase 3 (API):** main.py - FastAPI application
- **Database:** database.py (both phases) - ORM models
- **Business Logic:** rules.py - Query logic

### External Dependencies
- **MySQL 8.0** - localhost:3306, database: `telecom_updated_db`
- **Python 3.14** - FastAPI, SQLAlchemy, Pydantic
- **FastAPI Framework** - Web framework with auto-documentation
- **Uvicorn** - ASGI server for running FastAPI

### Documentation
- **Swagger UI:** http://localhost:8000/docs (auto-generated when server runs)
- **ReDoc:** http://localhost:8000/redoc (alternative docs view)
- **Phase 2 README:** [d:\CoWork\Phase2\README.md](d:\CoWork\Phase2\README.md)

---

## 15. RISK ASSESSMENT & MITIGATION

### Known Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| MySQL connection failure | All endpoints down | Add connection pooling; retry logic in datainsertion.py |
| Stale risk scores | Outdated analytics | Schedule daily/weekly data reload from Phase 2 |
| Missing ML model file | /ml/predict-churn returns error | Add fallback to dummy predictions; clear error message |
| Token hardcoded in code | Security vulnerability | Migrate to environment variables or secrets manager |
| No database backups | Data loss risk | Implement automated MySQL backups |
| Performance degradation with large dataset | Slow queries | Add database indexes on risk_category, churn columns |

### Quality Assurance

| Check | Location | Frequency |
|-------|----------|-----------|
| Syntax errors | Run `python -m py_compile *.py` | Before deployment |
| API responsiveness | Use `/health` endpoint | Continuous (via monitoring) |
| Database integrity | Run data validation queries | After data reload |
| Log completeness | Parse telecom_api.log | Weekly review |
| Prediction accuracy | Compare predictions to actual churn | Monthly analysis |

---

**Report Generated:** 2026-08-14  
**Last Updated:** 2026-08-14  
**Next Review:** After ML model integration
