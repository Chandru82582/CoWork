"""
ml_model.py
Loads the three trained churn models (logistic regression, random forest,
xgboost) plus the fitted scaler + preprocessing metadata from Phase1/models,
and exposes predict_churn_ensemble() which runs all three and returns a
majority-vote prediction. Models load once at process startup and are
reused across requests.
"""
import sys
import json
import logging
from pathlib import Path

import joblib
import pandas as pd

# Phase3/ -> project root -> Phase1/models
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = PROJECT_ROOT / "Phase1" / "models"
# MODELS_DIR = r"D:\CoWork\Phase1\models"

# preprocessor.py lives at the project root (see IMPLEMENTATION_REPORT.md)
sys.path.insert(0, str(PROJECT_ROOT))
from Phase1.preprocessor  import TelecomPreprocessor # noqa: E402

logger = logging.getLogger("main")

_MODELS = {}
_PREPROCESSOR = None


def _load_preprocessor():
    """Rebuild a fitted TelecomPreprocessor from the saved scaler + metadata
    instead of re-fitting (we don't have training data at request time).

    preprocessing_meta.json only stores {cols_to_scale, feature_columns,
    target_column} — it does NOT store iqr_bounds_ (outlier-capping
    thresholds) or partner_columns_ explicitly. So:
      - partner_columns_ is derived from feature_columns (anything
        starting with "telecom_partner_").
      - iqr_bounds_ is left empty, which means TelecomPreprocessor.transform()
        skips outlier capping at inference time. That's the correct
        behavior here — capping bounds are training-set quartile
        statistics, and reapplying invented bounds would be worse than
        skipping the step.
    """
    global _PREPROCESSOR
    if _PREPROCESSOR is not None:
        return _PREPROCESSOR

    meta_path = MODELS_DIR / "preprocessing_meta.json"
    scaler_path = MODELS_DIR / "scaler.joblib"

    if not meta_path.exists() or not scaler_path.exists():
        raise FileNotFoundError(
            f"Missing preprocessing artifacts in {MODELS_DIR}. "
            f"Expected preprocessing_meta.json and scaler.joblib."
        )

    with open(meta_path) as f:
        meta = json.load(f)

    target_column = meta.get("target_column", "churn")
    feature_columns = [c for c in meta["feature_columns"] if c != target_column]

    preprocessor = TelecomPreprocessor()
    preprocessor.scaler = joblib.load(scaler_path)
    preprocessor.features_ = feature_columns
    preprocessor.partner_columns_ = sorted(
        c for c in feature_columns if c.startswith("telecom_partner_")
    )
    # Must match the exact column order the scaler was fit on.
    preprocessor.scale_cols = meta["cols_to_scale"]
    preprocessor.iqr_bounds_ = {}  # not persisted — capping skipped at inference, see docstring
    preprocessor.max_registration_date_ = None  # unused: we pass tenure_days directly, not a date

    _PREPROCESSOR = preprocessor
    logger.info(
        f"Loaded fitted preprocessor: {len(feature_columns)} features, "
        f"{len(preprocessor.partner_columns_)} partner dummy columns, "
        f"{len(preprocessor.scale_cols)} scaled columns"
    )
    return _PREPROCESSOR


def _load_models():
    """Load the three voting models once and cache them."""
    global _MODELS
    if _MODELS:
        return _MODELS

    model_files = {
        "logistic_regression": "logistic_regression.joblib",
        "random_forest": "random_forest.joblib",
        "xgboost": "xgboost_model.joblib",
    }

    for name, filename in model_files.items():
        path = MODELS_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")
        _MODELS[name] = joblib.load(path)
        logger.info(f"Loaded model: {name} ({path.name})")

    return _MODELS


def _features_to_dataframe(features) -> pd.DataFrame:
    """Map a ChurnPredictionInput into the raw column shape TelecomPreprocessor expects.

    Note: tenure_days was dropped from the retrained models' feature set,
    so it's intentionally excluded here even though ChurnPredictionInput
    still accepts `tenure` for logging/context purposes.
    """
    gender_map = {"Male": "M", "Female": "F", "Other": "F"}  # preprocessor only maps M/F
    record = {
        "age": features.age,
        "gender": gender_map.get(features.gender, features.gender),
        "num_dependents": features.num_dependents,
        "estimated_salary": features.estimated_salary,
        "calls_made": features.calls_made,
        "sms_sent": features.sms_sent,
        "data_used": features.data_used,
        "telecom_partner": features.telecom_partner,
    }
    return pd.DataFrame([record])


def predict_churn_ensemble(features) -> dict:
    """Runs all three models and returns a majority-vote prediction."""
    preprocessor = _load_preprocessor()
    models = _load_models()

    raw_df = _features_to_dataframe(features)
    X = preprocessor.transform(raw_df)

    votes, probabilities = {}, {}
    for name, model in models.items():
        proba = model.predict_proba(X)[0][1]  # P(churn = 1)
        probabilities[name] = float(proba)
        votes[name] = int(proba > 0.5)

    churn_votes = sum(votes.values())
    churn_prediction = churn_votes >= 2  # majority of 3
    agreement = max(churn_votes, 3 - churn_votes) / 3  # how unanimous the vote was
    avg_probability = sum(probabilities.values()) / len(probabilities)

    if avg_probability >= 0.66:
        risk_level = "High"
        recommendation = "Immediate retention outreach recommended — high churn likelihood."
    elif avg_probability >= 0.33:
        risk_level = "Medium"
        recommendation = "Monitor customer engagement and consider retention offers."
    else:
        risk_level = "Low"
        recommendation = "No action needed — customer shows low churn risk."

    logger.debug(f"Model votes: {votes}, probabilities: {probabilities}")

    return {
        "churn_probability": round(avg_probability, 4),
        "churn_prediction": churn_prediction,
        "confidence_score": round(agreement, 4),
        "risk_level": risk_level,
        "recommendation": recommendation,
        "model_votes": votes,
    }