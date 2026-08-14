from pathlib import Path

import pandas as pd
from sklearn.preprocessing import StandardScaler


DEFAULT_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "telecom_churn_processed.csv"


class TelecomPreprocessor:
    """Simple preprocessing pipeline for batch training data and single-record prediction."""

    def __init__(self):
        self.numeric_cols = [
            "age",
            "num_dependents",
            "estimated_salary",
            "calls_made",
            "sms_sent",
            "data_used",
            "tenure_days",
        ]
        self.scale_cols = [
            "age",
            "tenure_days",
            "num_dependents",
            "calls_made",
            "sms_sent",
            "data_used",
            "estimated_salary",
        ]
        self.scaler = StandardScaler()
        self.partner_columns_ = []
        self.features_ = []
        self.max_registration_date_ = None
        self.iqr_bounds_ = {}

    def _prepare_dataframe(self, df):
        if isinstance(df, dict):
            df = pd.DataFrame([df])
        elif isinstance(df, pd.Series):
            df = df.to_frame().T
        elif not isinstance(df, pd.DataFrame):
            raise TypeError("Input must be a pandas DataFrame, Series, or dict.")

        df = df.copy()
        df = df.drop(columns=["customer_id", "pincode"], errors="ignore")

        if "date_of_registration" in df.columns:
            df["date_of_registration"] = pd.to_datetime(df["date_of_registration"], errors="coerce")

        if "gender" in df.columns:
            df["gender"] = df["gender"].map({"M": 1, "F": 0})

        if "churn" in df.columns:
            df["churn"] = df["churn"].map({True: 1, False: 0})

        return df

    def _add_tenure(self, df, reference_date=None):
        df = df.copy()
        if "date_of_registration" not in df.columns:
            return df

        if reference_date is None:
            reference_date = df["date_of_registration"].max()

        df["tenure_days"] = (reference_date - df["date_of_registration"]).dt.days
        df = df.drop(columns=["date_of_registration"])
        return df

    def _cap_outliers(self, df):
        df_capped = df.copy()

        for col in self.numeric_cols:
            if col not in df_capped.columns:
                continue

            q1 = df_capped[col].quantile(0.25)
            q3 = df_capped[col].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            self.iqr_bounds_.setdefault(col, (lower_bound, upper_bound))
            df_capped[col] = df_capped[col].clip(lower=lower_bound, upper=upper_bound)

        return df_capped

    def fit(self, df):
        """Fit the transformer on training data."""
        df = self._prepare_dataframe(df)

        if "date_of_registration" in df.columns:
            self.max_registration_date_ = df["date_of_registration"].max()
            df = self._add_tenure(df, reference_date=self.max_registration_date_)

        df = pd.get_dummies(df, columns=["telecom_partner"], dtype=int)
        df = df.drop(columns=["state", "city"], errors="ignore")

        self.partner_columns_ = [col for col in df.columns if col.startswith("telecom_partner_")]
        self.partner_columns_.sort()

        df = self._cap_outliers(df)

        for col in self.scale_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        self.scaler.fit(df[self.scale_cols])
        df[self.scale_cols] = self.scaler.transform(df[self.scale_cols])

        self.features_ = [col for col in df.columns if col != "churn"]
        return self

    def transform(self, df):
        """Apply fitted preprocessing to a dataframe or single record."""
        df = self._prepare_dataframe(df)

        reference_date = self.max_registration_date_
        if reference_date is None and "date_of_registration" in df.columns:
            reference_date = df["date_of_registration"].max()

        if "date_of_registration" in df.columns:
            df = self._add_tenure(df, reference_date=reference_date)

        df = pd.get_dummies(df, columns=["telecom_partner"], dtype=int)
        df = df.drop(columns=["state", "city"], errors="ignore")

        for col in self.partner_columns_:
            if col not in df.columns:
                df[col] = 0

        for col, (lower_bound, upper_bound) in self.iqr_bounds_.items():
            if col in df.columns:
                df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)

        scaling_columns = [col for col in self.scale_cols if col in df.columns]
        if scaling_columns:
            scale_df = df[scaling_columns].copy()
            for col in scaling_columns:
                scale_df[col] = pd.to_numeric(scale_df[col], errors="coerce")
            scaled_values = self.scaler.transform(scale_df)
            for idx, col in enumerate(scaling_columns):
                df[col] = scaled_values[:, idx]

        for col in self.features_:
            if col not in df.columns:
                df[col] = 0

        final_columns = [col for col in self.features_ if col in df.columns]
        result = df[final_columns].copy()

        extra_columns = [col for col in df.columns if col not in final_columns and col != "churn"]
        if extra_columns:
            for col in extra_columns:
                result[col] = df[col]

        return result

    def fit_transform(self, df):
        self.fit(df)
        return self.transform(df)

    def preprocess_record(self, record):
        """Convenience method for a single prediction record."""
        transformed = self.transform(record)
        return transformed.iloc[0] if len(transformed) == 1 else transformed


def cap_outliers_iqr(df, columns):
    """Simple helper compatible with the notebook-style function name."""
    preprocessor = TelecomPreprocessor()
    temp = df.copy()
    for col in columns:
        if col not in temp.columns:
            continue
        q1 = temp[col].quantile(0.25)
        q3 = temp[col].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        temp[col] = temp[col].clip(lower=lower, upper=upper)
    return temp


def preprocess_telecom_data(csv_path=None):
    """Training preprocessing: returns the model-ready feature matrix and target series."""
    if csv_path is None:
        csv_path = DEFAULT_DATA_PATH

    telecom_df = pd.read_csv(csv_path)
    preprocessor = TelecomPreprocessor().fit(telecom_df)
    X = preprocessor.transform(telecom_df)
    y = telecom_df["churn"].map({True: 1, False: 0}) if "churn" in telecom_df.columns else None
    return X, y


def preprocess_record_for_prediction(record, fitted_preprocessor=None):
    """Prepare one incoming record for prediction using a fitted preprocessor."""
    if fitted_preprocessor is None:
        raise ValueError("Pass a fitted TelecomPreprocessor instance to preprocess_record_for_prediction().")

    return fitted_preprocessor.preprocess_record(record)


if __name__ == "__main__":
    train_df = pd.read_csv(DEFAULT_DATA_PATH)
    preprocessor = TelecomPreprocessor().fit(train_df)
    sample_record = train_df.iloc[0].to_dict()

    X = preprocessor.transform(train_df)
    y = train_df["churn"].map({True: 1, False: 0}) if "churn" in train_df.columns else None
    prediction_input = preprocessor.preprocess_record(sample_record)

    print("Training feature shape:", X.shape)
    print("Prediction input shape:", prediction_input.shape)
    print("Target head:", y.head().tolist())
