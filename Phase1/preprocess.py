"""
preprocess.py
==============

Function-based preprocessing pipeline for the telecom churn dataset,
extracted from the `mlfeaturing.ipynb` notebook.

Behaviour
---------
- Pass a path to a CSV file  -> the whole file is preprocessed (fitting
  encoders/scaler/outlier-bounds on it) and the preprocessed CSV is saved
  next to the original file. If a file with that output name already
  exists, a counter is appended (e.g. `data_preprocessed_1.csv`,
  `data_preprocessed_2.csv`, ...) so nothing gets overwritten. The fitted
  artifacts (scaler, IQR bounds, reference date, column layout) are saved
  to an `artifacts/` folder so a single row can later be preprocessed the
  same way for prediction.

- Pass a single row of data (a dict, or a JSON string of a dict) -> it is
  preprocessed using the previously saved artifacts and returned ready to
  feed into the trained model (no file is written).

Usage as a script
------------------
    # Preprocess a whole training/inference CSV file
    python preprocess.py --file data/telecom_churn_processed.csv

    # Preprocess a single row for prediction (uses the saved artifacts)
    python preprocess.py --record '{"gender": "F", "age": 30, ...}'

Usage as a library
-------------------
    from preprocess import preprocess

    # CSV file -> preprocesses & saves a new CSV, returns the DataFrame
    df = preprocess("data/telecom_churn_processed.csv")

    # Single row -> preprocesses using saved artifacts, returns a DataFrame
    row_ready = preprocess({"gender": "F", "age": 30, ...})
    model.predict(row_ready.values)
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import pandas as pd
from sklearn.preprocessing import StandardScaler

DataInput = Union[str, Dict[str, Any], List[Dict[str, Any]], pd.DataFrame]

DROP_COLS = ["customer_id", "pincode"]
POST_ENCODE_DROP_COLS = ["state", "city"]
CATEGORICAL_ONE_HOT_COLS = ["telecom_partner"]
NUMERIC_COLS = [
    "age",
    "tenure_days",
    "num_dependents",
    "estimated_salary",
    "calls_made",
    "sms_sent",
    "data_used",
]
TARGET_COL = "churn"

ARTIFACTS_DIR = "artifacts"


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def load_as_dataframe(data: DataInput) -> pd.DataFrame:
    """Turns a csv path / dict / list of dicts / JSON string / DataFrame into a DataFrame."""
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if isinstance(data, dict):
        return pd.DataFrame([data])
    if isinstance(data, list):
        return pd.DataFrame(data)
    if isinstance(data, str):
        if os.path.exists(data):
            return pd.read_csv(data)
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as exc:
            raise ValueError(f"'{data}' is neither an existing file path nor valid JSON.") from exc
        if isinstance(parsed, dict):
            return pd.DataFrame([parsed])
        if isinstance(parsed, list):
            return pd.DataFrame(parsed)
        raise ValueError("JSON input must decode to an object or a list of objects.")
    raise TypeError(f"Unsupported data type for preprocessing: {type(data)}")


def is_csv_file_path(data: DataInput) -> bool:
    """True when the input refers to an existing CSV file on disk."""
    return isinstance(data, str) and os.path.exists(data)


def get_unique_output_path(path: str) -> str:
    """Returns `path` if it doesn't exist, otherwise appends _1, _2, ... before the extension."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    counter = 1
    new_path = f"{base}_{counter}{ext}"
    while os.path.exists(new_path):
        counter += 1
        new_path = f"{base}_{counter}{ext}"
    return new_path


# --------------------------------------------------------------------------- #
# Pipeline steps (each works in both "fit" and "transform" mode)
# --------------------------------------------------------------------------- #
def clean_base(df: pd.DataFrame) -> pd.DataFrame:
    """Drop id columns, parse dates, encode gender/churn."""
    df = df.copy()

    drop_now = [c for c in DROP_COLS if c in df.columns]
    if drop_now:
        df = df.drop(columns=drop_now)

    if "date_of_registration" in df.columns:
        df["date_of_registration"] = pd.to_datetime(df["date_of_registration"])

    if TARGET_COL in df.columns:
        df[TARGET_COL] = df[TARGET_COL].map({True: 1, False: 0}).fillna(df[TARGET_COL]).astype(int)

    if "gender" in df.columns:
        df["gender"] = df["gender"].map({"M": 1, "F": 0}).fillna(df["gender"])

    return df


def add_tenure_days(
    df: pd.DataFrame, reference_date: Optional[pd.Timestamp] = None
) -> Tuple[pd.DataFrame, Optional[pd.Timestamp]]:
    """Turns date_of_registration into tenure_days (relative to reference_date).
    If reference_date is None, it is computed (fit mode) as the max date in df."""
    if "date_of_registration" not in df.columns:
        return df, reference_date

    if reference_date is None:
        reference_date = df["date_of_registration"].max()

    df["tenure_days"] = (reference_date - df["date_of_registration"]).dt.days
    df = df.drop(columns=["date_of_registration"])
    return df, reference_date


def one_hot_encode(
    df: pd.DataFrame, dummy_columns: Optional[List[str]] = None
) -> Tuple[pd.DataFrame, List[str]]:
    """One-hot encodes CATEGORICAL_ONE_HOT_COLS. If dummy_columns is None (fit mode),
    it is recorded from this data; otherwise the given dummy layout is enforced."""
    cols_present = [c for c in CATEGORICAL_ONE_HOT_COLS if c in df.columns]
    if cols_present:
        df = pd.get_dummies(df, columns=cols_present, dtype=int)

    if dummy_columns is None:
        dummy_columns = [
            c for c in df.columns if any(c.startswith(f"{base}_") for base in CATEGORICAL_ONE_HOT_COLS)
        ]
    else:
        for col in dummy_columns:
            if col not in df.columns:
                df[col] = 0
        unseen = [
            c
            for c in df.columns
            if any(c.startswith(f"{base}_") for base in CATEGORICAL_ONE_HOT_COLS) and c not in dummy_columns
        ]
        if unseen:
            df = df.drop(columns=unseen)

    return df, dummy_columns


def cap_outliers(
    df: pd.DataFrame, bounds: Optional[Dict[str, Dict[str, float]]] = None
) -> Tuple[pd.DataFrame, Dict[str, Dict[str, float]]]:
    """Clips NUMERIC_COLS using IQR bounds. If bounds is None (fit mode), they are computed here."""
    cols_present = [c for c in NUMERIC_COLS if c in df.columns]

    if bounds is None:
        bounds = {}
        for col in cols_present:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            bounds[col] = {"lower": float(q1 - 1.5 * iqr), "upper": float(q3 + 1.5 * iqr)}

    for col in cols_present:
        b = bounds.get(col)
        if b is not None:
            df[col] = df[col].clip(lower=b["lower"], upper=b["upper"])

    return df, bounds


def scale_features(
    df: pd.DataFrame, scaler: Optional[StandardScaler] = None
) -> Tuple[pd.DataFrame, StandardScaler]:
    """Standard-scales NUMERIC_COLS. If scaler is None (fit mode), a new one is fitted here."""
    cols_present = [c for c in NUMERIC_COLS if c in df.columns]
    if not cols_present:
        return df, scaler if scaler is not None else StandardScaler()

    if scaler is None:
        scaler = StandardScaler()
        df[cols_present] = scaler.fit_transform(df[cols_present])
    else:
        df[cols_present] = scaler.transform(df[cols_present])

    return df, scaler


def align_columns(df: pd.DataFrame, feature_columns: List[str]) -> pd.DataFrame:
    """Ensures df has exactly feature_columns (+ target, if present) in the expected order."""
    has_target = TARGET_COL in df.columns
    target = df[TARGET_COL] if has_target else None

    for col in feature_columns:
        if col not in df.columns:
            df[col] = 0
    df = df[feature_columns]

    if has_target:
        df[TARGET_COL] = target.values
    return df


# --------------------------------------------------------------------------- #
# Artifact persistence
# --------------------------------------------------------------------------- #
def save_artifacts(
    artifacts_dir: str,
    scaler: StandardScaler,
    bounds: Dict[str, Dict[str, float]],
    reference_date: Optional[pd.Timestamp],
    dummy_columns: List[str],
    feature_columns: List[str],
) -> None:
    os.makedirs(artifacts_dir, exist_ok=True)
    joblib.dump(scaler, os.path.join(artifacts_dir, "scaler.joblib"))
    meta = {
        "iqr_bounds": bounds,
        "reference_date": reference_date.isoformat() if reference_date is not None else None,
        "dummy_columns": dummy_columns,
        "feature_columns": feature_columns,
    }
    with open(os.path.join(artifacts_dir, "preprocess_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)


def load_artifacts(artifacts_dir: str) -> Tuple[StandardScaler, dict]:
    scaler = joblib.load(os.path.join(artifacts_dir, "scaler.joblib"))
    with open(os.path.join(artifacts_dir, "preprocess_meta.json"), "r") as f:
        meta = json.load(f)
    return scaler, meta


# --------------------------------------------------------------------------- #
# Top level functions
# --------------------------------------------------------------------------- #
def preprocess_csv_file(csv_path: str, artifacts_dir: str = ARTIFACTS_DIR) -> pd.DataFrame:
    """Preprocesses an entire CSV file (fitting the pipeline on it), saves the
    preprocessed CSV next to the original (with a counter if needed), saves the
    fitted artifacts for later single-row use, and returns the preprocessed DataFrame."""
    df = pd.read_csv(csv_path)

    df = clean_base(df)
    df, reference_date = add_tenure_days(df)
    df, dummy_columns = one_hot_encode(df)
    df, bounds = cap_outliers(df)
    df = df.drop(columns=[c for c in POST_ENCODE_DROP_COLS if c in df.columns])
    df, scaler = scale_features(df)

    feature_columns = [c for c in df.columns if c != TARGET_COL]
    save_artifacts(artifacts_dir, scaler, bounds, reference_date, dummy_columns, feature_columns)

    directory, filename = os.path.split(csv_path)
    name, ext = os.path.splitext(filename)
    output_path = os.path.join(directory, f"{name}_preprocessed{ext}")
    output_path = get_unique_output_path(output_path)
    df.to_csv(output_path, index=False)
    print(f"Preprocessed CSV saved to '{output_path}'.")

    return df


def preprocess_record(record: DataInput, artifacts_dir: str = ARTIFACTS_DIR) -> pd.DataFrame:
    """Preprocesses a single row of data (dict / JSON string / 1-row DataFrame)
    using previously saved artifacts, ready to be fed into the model."""
    if not os.path.exists(artifacts_dir):
        raise RuntimeError(
            f"No artifacts found in '{artifacts_dir}'. Run preprocess() on a training "
            "CSV file first so a scaler/encoders can be fitted and saved."
        )

    scaler, meta = load_artifacts(artifacts_dir)
    bounds = meta["iqr_bounds"]
    reference_date = pd.Timestamp(meta["reference_date"]) if meta["reference_date"] else None
    dummy_columns = meta["dummy_columns"]
    feature_columns = meta["feature_columns"]

    df = load_as_dataframe(record)
    df = clean_base(df)
    df, _ = add_tenure_days(df, reference_date=reference_date)
    df, _ = one_hot_encode(df, dummy_columns=dummy_columns)
    df, _ = cap_outliers(df, bounds=bounds)
    df = df.drop(columns=[c for c in POST_ENCODE_DROP_COLS if c in df.columns])
    df, _ = scale_features(df, scaler=scaler)
    df = align_columns(df, feature_columns)

    return df


def preprocess(data: DataInput, artifacts_dir: str = ARTIFACTS_DIR) -> pd.DataFrame:
    """Entry point: if `data` is a path to an existing CSV file, the whole file is
    preprocessed and saved to disk. Otherwise `data` is treated as a single row
    (dict / JSON string / 1-row DataFrame) and preprocessed for prediction."""
    if is_csv_file_path(data):
        return preprocess_csv_file(data, artifacts_dir=artifacts_dir)
    return preprocess_record(data, artifacts_dir=artifacts_dir)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preprocess telecom churn data.")
    parser.add_argument("--file", metavar="CSV_PATH", help="Path to a CSV file to preprocess and save.")
    parser.add_argument(
        "--record",
        metavar="JSON",
        help="A single row of data as a JSON object, to preprocess for prediction.",
    )
    parser.add_argument(
        "--artifacts",
        default=ARTIFACTS_DIR,
        help=f"Directory to save/load fitted preprocessing artifacts (default: ./{ARTIFACTS_DIR}).",
    )
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    if not args.file and not args.record:
        parser.error("Provide --file <csv_path> or --record <json>.")

    if args.file:
        preprocess_csv_file(args.file, artifacts_dir=args.artifacts)

    if args.record:
        result = preprocess_record(args.record, artifacts_dir=args.artifacts)
        print(result.to_string(index=False))


# if __name__ == "__main__":
#     main()