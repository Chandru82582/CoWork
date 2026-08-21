import os
import logging
from datetime import datetime
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    lit, col, when, monotonically_increasing_id, datediff,
    max as F_max, mean as F_mean, stddev as F_stddev, greatest, least
)

# --- Configuration ---
os.environ["HADOOP_HOME"] = r"D:\Training\spark\hadoop"
os.environ["PATH"] = os.environ["PATH"] + r";D:\Training\spark\hadoop\bin"


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pyspark_ingestion.log"),
        logging.StreamHandler()
    ]
)

# Define paths for the data pipeline
LANDING_ZONE = r"d:/CoWork/Phase5/data/landing"
STAGING_ZONE = r"d:/CoWork/Phase5/data/staging"
CLEANED_ZONE = r"d:/CoWork/Phase5/data/cleaned"
CURATED_ZONE = r"d:/CoWork/Phase5/data/curated"

LOG_PATH = os.path.join(STAGING_ZONE, "ingestion_log")
STAGING_TABLE_PATH = os.path.join(STAGING_ZONE, "stg_customer_raw")
CLEANED_TABLE_PATH = os.path.join(CLEANED_ZONE, "cleaned_customers")
FEATURE_TABLE_PATH = os.path.join(CURATED_ZONE, "customer_ml_features")

# Curated paths
DIM_LOCATION_PATH = os.path.join(CURATED_ZONE, "dim_location")
DIM_TELECOM_PARTNER_PATH = os.path.join(CURATED_ZONE, "dim_telecom_partner")
DIM_CUSTOMER_PATH = os.path.join(CURATED_ZONE, "dim_customer")
FACT_USAGE_PATH = os.path.join(CURATED_ZONE, "fact_customer_usage")

# Define the expected schema for the raw CSV files
EXPECTED_COLS = [
    'customer_id', 'gender', 'age', 'pincode', 'date_of_registration',
    'num_dependents', 'estimated_salary', 'churn', 'telecom_partner', 'city',
    'state', 'calls_made', 'sms_sent', 'data_used'
]

# --- Spark Session ---

def get_spark_session():
    """Initializes and returns a SparkSession."""
    return (
        SparkSession.builder
        .appName("CustomerDataIngestion")
        .master("local[*]")  # Use all available local cores
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
        .getOrCreate()
    )

# --- Pipeline Functions ---

def detect_files(path: str) -> list[str]:
    """Scans the landing directory and returns a list of CSV files."""
    logging.info(f"Scanning for CSV files in '{path}'...")
    try:
        if not os.path.exists(path):
            logging.warning(f"Landing directory not found: {path}. Creating it.")
            os.makedirs(path)
            return []
        
        files = [f for f in os.listdir(path) if f.lower().endswith('.csv')]
        logging.info(f"Found {len(files)} CSV files: {files}")
        return [os.path.join(path, f) for f in files]
    except Exception as e:
        logging.error(f"Failed to scan landing directory {path}: {e}")
        return []

def validate_schema(spark: SparkSession, filepath: str) -> tuple[bool, str]:
    """Reads the header row of a CSV and checks if it matches EXPECTED_COLS."""
    logging.info(f"Validating schema for '{os.path.basename(filepath)}'...")
    try:
        # Read only the header from the CSV file
        header = spark.read.option("header", "true").csv(filepath).columns
        
        # Using sets for efficient comparison, ignoring order
        if set(header) == set(EXPECTED_COLS):
            logging.info("Schema validation successful.")
            return True, "Schema valid"
        else:
            missing = set(EXPECTED_COLS) - set(header)
            extra = set(header) - set(EXPECTED_COLS)
            reason = f"Schema mismatch. Missing: {missing or 'None'}. Extra: {extra or 'None'}."
            logging.error(reason)
            return False, reason
    except Exception as e:
        reason = f"Failed to read or validate schema: {e}"
        logging.error(reason)
        return False, reason

def load_to_staging(spark: SparkSession, filepath: str) -> int:
    """Loads a valid CSV into the stg_customer_raw table (Parquet format) and returns row count."""
    logging.info(f"Loading '{os.path.basename(filepath)}' to staging...")
    try:
        df = spark.read.option("header", "true").option("inferSchema", "true").csv(filepath)
        
        # Ensure all expected columns are present before writing
        df_ordered = df.select(*EXPECTED_COLS)

        # Write to Parquet, appending to the existing data
        df_ordered.write.mode("append").parquet(STAGING_TABLE_PATH)
        
        row_count = df.count()
        logging.info(f"Successfully loaded {row_count} rows to {STAGING_TABLE_PATH}.")
        return row_count
    except Exception as e:
        logging.error(f"Failed to load data to staging: {e}")
        return 0

def log_ingestion(spark: SparkSession, filename: str, status: str, rows: int, reason: str = None):
    """Writes the result of an ingestion attempt to the ingestion_log table (Parquet format)."""
    log_entry = {
        "filename": os.path.basename(filename),
        "status": status,
        "rows_processed": rows,
        "reason": reason,
        "timestamp": datetime.now()
    }
    
    try:
        # Create a DataFrame from the log entry
        log_df = spark.createDataFrame([log_entry])
        
        # Write to Parquet, appending to the existing log
        log_df.write.mode("append").parquet(LOG_PATH)
        logging.info(f"Logged ingestion for '{os.path.basename(filename)}': {status}")
    except Exception as e:
        logging.error(f"Failed to write to ingestion_log: {e}")

def run_quality_checks(df: DataFrame, table_name: str) -> bool:
    """Runs a series of data quality checks and prints a report."""
    logging.info(f"--- Running Data Quality Checks on {table_name} ---")
    total_rows = df.count()
    report = []
    all_passed = True

    # 1. No NULLs in customer_id
    null_customer_ids = df.filter(col("customer_id").isNull()).count()
    if null_customer_ids == 0:
        report.append(f"[PASS] No NULLs in 'customer_id' ({total_rows} rows checked).")
    else:
        report.append(f"[FAIL] Found {null_customer_ids} NULLs in 'customer_id'.")
        all_passed = False

    # 2. No NULLs in estimated_salary (as a proxy for monthly_charges)
    if "estimated_salary" in df.columns:
        null_salaries = df.filter(col("estimated_salary").isNull()).count()
        if null_salaries == 0:
            report.append(f"[PASS] No NULLs in 'estimated_salary' ({total_rows} rows checked).")
        else:
            report.append(f"[FAIL] Found {null_salaries} NULLs in 'estimated_salary'.")
            all_passed = False

    # 3. Churn column values are only 0 or 1
    if "churn" in df.columns:
        invalid_churn_values = df.filter(~col("churn").isin([0, 1])).count()
        if invalid_churn_values == 0:
            report.append(f"[PASS] 'churn' column values are all 0 or 1 ({total_rows} rows checked).")
        else:
            report.append(f"[FAIL] Found {invalid_churn_values} rows where 'churn' is not 0 or 1.")
            all_passed = False

    for line in report:
        logging.info(line)
    logging.info("--- Data Quality Checks Finished ---")
    return all_passed

def clean_staging(spark: SparkSession):
    """
    Reads stg_customer_raw, cleans the data based on logic from Phase1, 
    runs quality checks, and writes to a 'cleaned_customers' table.
    """
    logging.info("--- Starting Staging Table Cleaning ---")
    if not os.path.exists(STAGING_TABLE_PATH):
        logging.warning(f"Staging path {STAGING_TABLE_PATH} not found. Skipping cleaning.")
        return

    try:
        stg_df = spark.read.parquet(STAGING_TABLE_PATH)
        stg_row_count = stg_df.count()
        if stg_row_count == 0:
            logging.info("Staging table is empty. Nothing to clean.")
            return
        logging.info(f"Read {stg_row_count} rows from staging table.")

        # Re-implementing cleaning logic from Phase1 using PySpark
        # 1. Clean types and values
        cleaned_df = stg_df.withColumn(
            "churn", col("churn").cast("integer")
        ).withColumn(
            "calls_made", when(col("calls_made") < 0, 0).otherwise(col("calls_made"))
        ).withColumn(
            "sms_sent", when(col("sms_sent") < 0, 0).otherwise(col("sms_sent"))
        ).withColumn(
            "data_used", when(col("data_used") < 0, 0.0).otherwise(col("data_used"))
        )

        # 2. Run data quality checks
        run_quality_checks(cleaned_df, "cleaned_df")

        # 3. Row count check
        cleaned_row_count = cleaned_df.count()
        logging.info(f"Row count after cleaning: {cleaned_row_count}")
        assert cleaned_row_count == stg_row_count, "Row count mismatch after cleaning!"
        logging.info("[PASS] Row count check: Cleaned table has the same number of rows as staging.")

        # 4. Write to cleaned table
        logging.info(f"Writing cleaned data to {CLEANED_TABLE_PATH}...")
        cleaned_df.coalesce(1).write.mode("overwrite").parquet(CLEANED_TABLE_PATH)
        logging.info("Successfully wrote cleaned data.")

        logging.info("--- Staging Table Cleaning Finished ---")

    except Exception as e:
        logging.error(f"An error occurred during staging cleaning: {e}", exc_info=True)

def build_curated_tables(spark: SparkSession):
    """
    Builds curated dimensional and fact tables from the cleaned staging data.
    Populates dim_location, dim_telecom_partner, dim_customer, and fact_customer_usage.
    """
    logging.info("--- Starting Curated Table Build ---")
    if not os.path.exists(CLEANED_TABLE_PATH):
        logging.warning(f"Cleaned data path {CLEANED_TABLE_PATH} not found. Skipping curation.")
        return

    try:
        cleaned_df = spark.read.parquet(CLEANED_TABLE_PATH)
        cleaned_df.cache() # Cache for multiple uses
        
        if cleaned_df.count() == 0:
            logging.info("Cleaned table is empty. Nothing to curate.")
            return
        logging.info(f"Read {cleaned_df.count()} rows from cleaned table.")

        # Note: The request mentioned dim_contract and dim_payment, but the source data
        # does not contain columns for contract or payment details.
        # We will build dimensions that are supported by the available data.
        logging.warning("Note: Building dimensions based on available data. `dim_contract` and `dim_payment` cannot be created.")

        # 1. Build dim_location
        dim_location = cleaned_df.select("pincode", "city", "state").distinct()
        dim_location.write.mode("overwrite").parquet(DIM_LOCATION_PATH)
        logging.info(f"Wrote {dim_location.count()} rows to {DIM_LOCATION_PATH}")

        # 2. Build dim_telecom_partner
        dim_telecom_partner = cleaned_df.select("telecom_partner").distinct() \
            .withColumn("telecom_partner_id", monotonically_increasing_id())
        dim_telecom_partner.write.mode("overwrite").parquet(DIM_TELECOM_PARTNER_PATH)
        logging.info(f"Wrote {dim_telecom_partner.count()} rows to {DIM_TELECOM_PARTNER_PATH}")

        # 3. Build dim_customer
        dim_customer = cleaned_df.select(
            "customer_id", "gender", "age", "date_of_registration", "num_dependents"
        ).distinct()
        dim_customer.write.mode("overwrite").parquet(DIM_CUSTOMER_PATH)
        logging.info(f"Wrote {dim_customer.count()} rows to {DIM_CUSTOMER_PATH}")

        # 4. Build fact_customer_usage
        # Join back to get telecom_partner_id
        df_with_partner_id = cleaned_df.join(
            dim_telecom_partner,
            on="telecom_partner",
            how="left"
        )

        fact_customer_usage = df_with_partner_id.select(
            "customer_id",
            "pincode",
            "telecom_partner_id",
            "estimated_salary",
            "churn",
            "calls_made",
            "sms_sent",
            "data_used"
        )
        fact_customer_usage.write.mode("overwrite").parquet(FACT_USAGE_PATH)
        logging.info(f"Wrote {fact_customer_usage.count()} rows to {FACT_USAGE_PATH}")
        
        cleaned_df.unpersist()
        logging.info("--- Curated Table Build Finished ---")

    except Exception as e:
        logging.error(f"An error occurred during curated table build: {e}", exc_info=True)

def build_features(spark: SparkSession):
    """
    Reads cleaned_customers, computes features based on phase1/preprocessor.py,
    and writes to a customer_ml_features table.
    """
    logging.info("--- Starting Feature Table Build ---")
    if not os.path.exists(CLEANED_TABLE_PATH):
        logging.warning(f"Cleaned data path {CLEANED_TABLE_PATH} not found. Skipping feature build.")
        return

    try:
        df = spark.read.parquet(CLEANED_TABLE_PATH)
        if df.count() == 0:
            logging.info("Cleaned table is empty. Nothing to build features from.")
            return
        logging.info(f"Read {df.count()} rows from cleaned table for feature engineering.")

        # --- 1. Add Tenure Days (from preprocess.add_tenure_days) ---
        logging.info("Calculating tenure_days...")
        max_date = df.agg(F_max("date_of_registration")).collect()[0][0]
        df = df.withColumn("tenure_days", datediff(lit(max_date), col("date_of_registration")))

        # --- 2. Encode Gender (from preprocess.clean_base) ---
        logging.info("Encoding gender...")
        df = df.withColumn("gender", when(col("gender") == "M", 1).when(col("gender") == "F", 0))

        # --- 3. One-Hot Encode Telecom Partner (from preprocess.one_hot_encode) ---
        logging.info("One-hot encoding telecom_partner...")
        partners = [row.telecom_partner for row in df.select("telecom_partner").distinct().collect()]
        for partner in partners:
            df = df.withColumn(f"telecom_partner_{partner}", when(col("telecom_partner") == partner, 1).otherwise(0))

        # --- 4. Cap Outliers (from preprocess.cap_outliers) ---
        logging.info("Capping outliers for numeric columns...")
        numeric_cols = [
            "age", "tenure_days", "num_dependents", "estimated_salary",
            "calls_made", "sms_sent", "data_used"
        ]
        for c in numeric_cols:
            if c not in df.columns: continue
            quantiles = df.approxQuantile(c, [0.25, 0.75], 0.01)
            q1, q3 = quantiles[0], quantiles[1]
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            df = df.withColumn(c, greatest(lit(lower_bound), least(lit(upper_bound), col(c))))
            logging.info(f"Capped '{c}' with bounds [{lower_bound:.2f}, {upper_bound:.2f}]")

        # --- 5. Scale Features (from preprocess.scale_features) ---
        logging.info("Standard scaling numeric features...")
        aggs = []
        for c in numeric_cols:
            if c in df.columns:
                aggs.append(F_mean(c).alias(f"{c}_mean"))
                aggs.append(F_stddev(c).alias(f"{c}_stddev"))

        if aggs:
            stats = df.agg(*aggs).collect()[0]
            for c in numeric_cols:
                if c in df.columns:
                    mean_val = stats[f"{c}_mean"]
                    std_val = stats[f"{c}_stddev"]
                    if std_val and std_val > 0:
                        df = df.withColumn(c, (col(c) - mean_val) / std_val)
                        logging.info(f"Scaled '{c}' with mean={mean_val:.2f}, stddev={std_val:.2f}")
                    else:
                        logging.warning(f"Stddev for '{c}' is 0 or null. Skipping scaling for this column.")

        # --- 6. Final Column Selection and Cleanup ---
        cols_to_drop = ["date_of_registration", "telecom_partner", "pincode", "city", "state"]
        final_df = df.drop(*[c for c in cols_to_drop if c in df.columns])

        # --- 7. Write to Feature Table ---
        logging.info(f"Writing feature data to {FEATURE_TABLE_PATH}...")
        final_df.coalesce(1).write.mode("overwrite").parquet(FEATURE_TABLE_PATH)
        logging.info(f"Successfully wrote {final_df.count()} rows to feature table.")

        logging.info("--- Feature Table Build Finished ---")

    except Exception as e:
        logging.error(f"An error occurred during feature build: {e}", exc_info=True)

def process_landing(spark: SparkSession):
    """Orchestrates the ingestion process: detect -> validate -> load -> log for each file."""
    logging.info("--- Starting Landing Zone Processing ---")

    # 1. Detect files in the landing zone
    files_to_process = detect_files(LANDING_ZONE)
    if not files_to_process:
        logging.info("No new files to process.")
        return

    # 2. Process each file
    for filepath in files_to_process:
        filename = os.path.basename(filepath)
        logging.info(f"--- Processing file: {filename} ---")
        
        is_valid, reason = validate_schema(spark, filepath)
        
        if is_valid:
            row_count = load_to_staging(spark, filepath)
            log_ingestion(spark, filename, 'LOADED', row_count)
        else:
            log_ingestion(spark, filename, 'REJECTED', 0, reason)
    
    logging.info("--- Landing Zone Processing Finished ---")

def verify_logs(spark: SparkSession):
    """Helper function to read and display the ingestion log for verification."""
    try:
        if not os.path.exists(LOG_PATH):
            logging.warning("Ingestion log path does not exist. No logs to show.")
            return
        
        print("\n--- Verifying ingestion_log ---")
        log_df = spark.read.parquet(LOG_PATH)
        log_df.show(truncate=False)
        print("-----------------------------\n")
    except Exception as e:
        logging.error(f"Could not read ingestion log: {e}")

def verify_curated_data(spark: SparkSession):
    """Helper function to read and display counts from curated tables."""
    logging.info("\n--- Verifying Curated Data ---")
    try:
        for name, path in [
            ("dim_location", DIM_LOCATION_PATH),
            ("dim_telecom_partner", DIM_TELECOM_PARTNER_PATH),
            ("dim_customer", DIM_CUSTOMER_PATH),
            ("fact_customer_usage", FACT_USAGE_PATH),
            ("customer_ml_features", FEATURE_TABLE_PATH)
        ]:
            if os.path.exists(path):
                count = spark.read.parquet(path).count()
                logging.info(f"Table '{name}' contains {count} rows.")
                spark.read.parquet(path).show(5, truncate=False)
            else:
                logging.warning(f"Curated table path does not exist: {path}")
    except Exception as e:
        logging.error(f"Could not verify curated data: {e}")
    finally:
        logging.info("--- Curated Data Verification Finished ---\n")

def run_pipeline():
    """Orchestrates the full data pipeline: landing -> staging -> cleaned -> curated."""
    spark = None
    try:
        spark = get_spark_session()
        
        # Phase 1: Landing to Staging
        process_landing(spark)

        # Phase 2: Staging to Cleaned
        clean_staging(spark)

        # Phase 3: Cleaned to Curated
        build_curated_tables(spark)

        # Phase 4: Cleaned to Features
        build_features(spark)

        # Final verification
        verify_logs(spark)
        verify_curated_data(spark)

    except Exception as e:
        logging.error(f"An error occurred during the main pipeline execution: {e}", exc_info=True)
    finally:
        if spark:
            spark.stop()
            logging.info("Spark session stopped.")

if __name__ == '__main__':
    run_pipeline()