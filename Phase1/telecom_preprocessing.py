import pandas as pd


class Preprocessing:

    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None

    def load_data(self):
        """Load the CSV file into a DataFrame."""
        self.df = pd.read_csv(self.file_path)
        return self.df

    def clean_types(self):
        """Convert columns to the appropriate data types."""
        if self.df is None:
            self.load_data()

        self.df = self.df.copy()
        self.df["pincode"] = self.df["pincode"].astype(str)
        self.df["date_of_registration"] = pd.to_datetime(
            self.df["date_of_registration"], errors="coerce"
        )
        self.df["churn"] = self.df["churn"].astype(bool)
        return self.df

    def handle_negative_values(self):
        """Clip negative numeric values for usage columns to zero."""
        if self.df is None:
            self.clean_types()

        for col in ["calls_made", "sms_sent", "data_used"]:
            self.df[col] = pd.to_numeric(self.df[col], errors="coerce")
            self.df[col] = self.df[col].clip(lower=0)
        return self.df

    def clean_data(self):
        """Run the full cleaning workflow."""
        self.clean_types()
        self.handle_negative_values()
        return self.df

    def save_clean_data(self, output_path, index=False):
        """Save the cleaned data to a CSV file."""
        if self.df is None:
            self.clean_data()

        self.df.to_csv(output_path, index=index)
        return output_path


if __name__ == "__main__":
    processor = Preprocessing(r"D:\CoWork\data\telecom_churn.csv")
    cleaned_df = processor.clean_data()
    save_path = processor.save_clean_data(r"D:\CoWork\data\telecom_churn_cleaned.csv")
    print(cleaned_df.head())
    print(cleaned_df.dtypes)
