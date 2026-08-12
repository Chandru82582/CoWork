import typing as _t
from dataclasses import dataclass, field

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import joblib


def cap_outliers_iqr(df: pd.DataFrame, columns: _t.List[str]) -> pd.DataFrame:
    df_c = df.copy()
    for col in columns:
        if col not in df_c.columns:
            continue
        Q1 = df_c[col].quantile(0.25)
        Q3 = df_c[col].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        df_c[col] = df_c[col].clip(lower=lower, upper=upper)
    return df_c


@dataclass
class Preprocessor:
    numeric_cols: _t.List[str] = field(default_factory=lambda: [
        'age', 'tenure_days', 'num_dependents', 'calls_made', 'sms_sent', 'data_used', 'estimated_salary'
    ])
    drop_cols: _t.List[str] = field(default_factory=lambda: ['customer_id', 'pincode', 'state', 'city'])
    partner_col: str = 'telecom_partner'
    date_col: str = 'date_of_registration'

    scaler: _t.Optional[StandardScaler] = None
    partner_dummies: _t.List[str] = field(default_factory=list)
    fitted: bool = False

    def _ensure_date(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.date_col in df.columns:
            df[self.date_col] = pd.to_datetime(df[self.date_col])
            df['tenure_days'] = (df[self.date_col].max() - df[self.date_col]).dt.days
        return df

    def _map_basic(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if 'churn' in df.columns:
            df['churn'] = df['churn'].map({True: 1, False: 0}).fillna(df['churn'])
        if 'gender' in df.columns:
            df['gender'] = df['gender'].map({'M': 1, 'F': 0}).fillna(df['gender'])
        return df

    def fit(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit preprocessing artifacts from a DataFrame and return transformed DataFrame.

        Use this for training-phase preprocessing.
        """
        df = df.copy()
        df = self._ensure_date(df)
        df = self._map_basic(df)

        # one-hot telecom partner
        if self.partner_col in df.columns:
            partner_dummies_df = pd.get_dummies(df[[self.partner_col]], prefix=self.partner_col, dtype=int)
            df = pd.concat([df.drop(columns=[self.partner_col]), partner_dummies_df], axis=1)
            self.partner_dummies = list(partner_dummies_df.columns)

        # cap outliers
        df = cap_outliers_iqr(df, [c for c in self.numeric_cols if c in df.columns])

        # fit scaler
        existing_numeric = [c for c in self.numeric_cols if c in df.columns]
        if existing_numeric:
            self.scaler = StandardScaler()
            df[existing_numeric] = self.scaler.fit_transform(df[existing_numeric])

        # drop unwanted
        df = df.drop(columns=[c for c in self.drop_cols if c in df.columns], errors='ignore')

        self.fitted = True
        return df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply fitted preprocessing to a DataFrame (prediction-time).

        Raises ValueError if `fit` has not been called.
        """
        if not self.fitted:
            raise ValueError('Preprocessor not fitted. Call `fit` first or use `fit` on training data.')

        df = df.copy()
        df = self._ensure_date(df)
        df = self._map_basic(df)

        # partner dummies: create same columns as training
        if self.partner_col in df.columns:
            partner_dummies_df = pd.get_dummies(df[[self.partner_col]], prefix=self.partner_col, dtype=int)
            df = pd.concat([df.drop(columns=[self.partner_col]), partner_dummies_df], axis=1)

        # add missing partner dummy columns with 0
        for col in self.partner_dummies:
            if col not in df.columns:
                df[col] = 0

        # cap outliers using same numeric column set
        df = cap_outliers_iqr(df, [c for c in self.numeric_cols if c in df.columns])

        # scale numeric using stored scaler
        existing_numeric = [c for c in self.numeric_cols if c in df.columns]
        if existing_numeric and self.scaler is not None:
            df[existing_numeric] = self.scaler.transform(df[existing_numeric])

        df = df.drop(columns=[c for c in self.drop_cols if c in df.columns], errors='ignore')
        return df

    def fit_from_csv(self, csv_path: str) -> pd.DataFrame:
        df = pd.read_csv(csv_path)
        return self.fit(df)

    def transform_record(self, record: _t.Dict[str, _t.Any]) -> _t.Dict[str, _t.Any]:
        df = pd.DataFrame([record])
        out = self.transform(df)
        # return as dict of scalars
        return {k: (float(v) if np.isscalar(v) and not isinstance(v, (str, bool)) else v) for k, v in out.iloc[0].to_dict().items()}

    def save(self, path: str) -> None:
        joblib.dump({
            'scaler': self.scaler,
            'partner_dummies': self.partner_dummies,
            'numeric_cols': self.numeric_cols,
            'drop_cols': self.drop_cols,
            'partner_col': self.partner_col,
            'date_col': self.date_col,
        }, path)

    @classmethod
    def load(cls, path: str) -> 'Preprocessor':
        data = joblib.load(path)
        p = cls()
        p.scaler = data.get('scaler')
        p.partner_dummies = data.get('partner_dummies', [])
        p.numeric_cols = data.get('numeric_cols', p.numeric_cols)
        p.drop_cols = data.get('drop_cols', p.drop_cols)
        p.partner_col = data.get('partner_col', p.partner_col)
        p.date_col = data.get('date_col', p.date_col)
        p.fitted = True
        return p


def preprocess_csv_to_artifacts(csv_path: str, artifact_path: str) -> pd.DataFrame:
    """Convenience helper: fit preprocessor on CSV and save artifacts."""
    p = Preprocessor()
    df = p.fit_from_csv(csv_path)
    p.save(artifact_path)
    return df
