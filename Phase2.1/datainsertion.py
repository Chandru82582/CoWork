# import shutil
# path = r"D:\\CoWork\\telecom_churn.csv"
# shutil.copy2(path, "telecom_churn.csv")

import multiprocessing
import csv
import logging
from datetime import datetime
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy_utils import database_exists, create_database

from database import Base, TelecomPartner, Location, Customer, CustomerUsage

# --- Configuration ---
# Replace with your MySQL connection details
# Format: 'mysql+mysqlconnector://<user>:<password>@<host>/<database>'
DB_CONNECTION_STRING = "mysql+mysqlconnector://root:root@localhost/telecom_updated_db"
CSV_FILE_PATH = r"D:\CoWork\data\telecom_churn_processed.csv"

# --- Data Mapping ---
# Maps CSV values to the database ENUM values
GENDER_MAP = {
    'F': 'Female',
    'M': 'Male',
    'O': 'Other'
}

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data_insertion.log"), # Log to a file
        logging.StreamHandler()                     # Log to the console
    ]
)


def calculate_risk_score(customer_data, usage_data):
    """
    Calculate risk score and category for a customer.
    
    Risk Scoring:
    - tenure < 180 days: +2
    - age between 18 and 30: +1
    - num_dependents <= 1: +1
    - calls_made < 10: +1
    - sms_sent < 20: +1
    - data_used < 1: +1
    - high salary + low calls + low data: +1
    
    Categories:
    - Score >= 6: High Risk
    - Score 3-5: Medium Risk
    - Score < 3: Low Risk
    """
    score = 0
    
    # Tenure risk
    tenure = int(customer_data.get('tenure', 0))
    if tenure < 180:
        score += 2
    
    # Age risk
    age = int(customer_data.get('age', 0))
    if 18 <= age <= 30:
        score += 1
    
    # Family risk
    num_dependents = int(customer_data.get('num_dependents', 0))
    if num_dependents <= 1:
        score += 1
    
    # Communication risk
    calls_made = int(usage_data.get('calls_made', 0))
    if calls_made < 10:
        score += 1
    
    sms_sent = int(usage_data.get('sms_sent', 0))
    if sms_sent < 20:
        score += 1
    
    # Data usage risk
    data_used = float(usage_data.get('data_used', 0))
    if data_used < 1:
        score += 1
    
    # High salary but low engagement risk
    estimated_salary = float(customer_data.get('estimated_salary', 0))
    if estimated_salary > 75000 and calls_made < 10 and data_used < 1:
        score += 1
    
    # Determine category
    if score >= 6:
        risk_category = "High Risk"
    elif 3 <= score <= 5:
        risk_category = "Medium Risk"
    else:
        risk_category = "Low Risk"
    
    return score, risk_category



def process_chunk(chunk, max_date):
    """
    Worker function to process a single chunk of rows.
    Each worker creates its own database session.
    
    Args:
        chunk: List of rows to process
        max_date: Maximum registration date to calculate tenure
    """
    worker_pid = multiprocessing.current_process().pid
    logging.info(f"[Worker {worker_pid}] Starting to process a chunk of {len(chunk)} rows.")

    # Each process must create its own engine and session
    engine = create_engine(DB_CONNECTION_STRING)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        for row in chunk:
            try:
                # --- Handle Customer and CustomerUsage ---
                # Parent records (Location, TelecomPartner) are now pre-populated.
                db_gender = GENDER_MAP.get(row['gender'], 'Other')
                reg_date = datetime.strptime(row['date_of_registration'], '%Y-%m-%d').date()
                tenure = (max_date - reg_date).days
                
                # Calculate risk score
                risk_score, risk_category = calculate_risk_score(
                    {'tenure': tenure, 'age': row['age'], 'num_dependents': row['num_dependents'], 'estimated_salary': row['estimated_salary']},
                    {'calls_made': row['calls_made'], 'sms_sent': row['sms_sent'], 'data_used': row['data_used']}
                )
                
                customer = Customer(
                    customer_id=int(row['customer_id']), # This is the PK
                    telecom_partner_id=row['telecom_partner_id'], # We will add this FK in main
                    gender=db_gender,
                    age=int(row['age']), 
                    pincode=row['pincode'],
                    date_of_registration=reg_date,
                    tenure=tenure,
                    num_dependents=int(row['num_dependents']),
                    estimated_salary=Decimal(row['estimated_salary']),
                    churn=row['churn'] == '1' or row['churn'].upper() == 'TRUE',
                    risk_score=risk_score,
                    risk_category=risk_category
                )
                usage = CustomerUsage(
                    customer_id=customer.customer_id,
                    calls_made=int(row['calls_made']),
                    sms_sent=int(row['sms_sent']),
                    data_used=Decimal(row['data_used'])
                )
                session.add(customer)
                session.add(usage)

            except IntegrityError:
                session.rollback()
                logging.warning(f"[Worker {worker_pid}] Skipping duplicate customer ID: {row.get('customer_id')}")
                continue

        session.commit()
        logging.info(f"[Worker {worker_pid}] Successfully committed {len(chunk)} rows.")
    except Exception as e:
        logging.error(f"[Worker {worker_pid}] An error occurred in worker: {e}", exc_info=True)
        session.rollback()
    finally:
        session.close()

def pre_populate_parents(engine, all_rows):
    """Pre-populates the telecom_partner and locations tables to avoid race conditions."""
    Session = sessionmaker(bind=engine)
    session = Session()

    # --- 1. Get all unique partners and locations from the data ---
    # Use a dictionary for locations to enforce unique pincodes, taking the first-seen city/state.
    unique_partners = {row['telecom_partner'] for row in all_rows}
    unique_locations_dict = {}
    for row in all_rows:
        pincode = row['pincode']
        if pincode not in unique_locations_dict:
            unique_locations_dict[pincode] = (row['city'], row['state'])
    unique_locations = {(p, c, s) for p, (c, s) in unique_locations_dict.items()}
    logging.info(f"[Main] Found {len(unique_partners)} unique partners and {len(unique_locations)} unique locations.")

    # --- 2. Get partners that are already in the DB ---
    existing_partners = {p.partner_name for p in session.query(TelecomPartner.partner_name)}
    partners_to_add = [TelecomPartner(partner_name=name) for name in unique_partners if name not in existing_partners]

    # --- 3. Get locations that are already in the DB ---
    existing_locations = {loc.pincode for loc in session.query(Location.pincode)}
    locations_to_add = [Location(pincode=p, city=c, state=s) for p, c, s in unique_locations if p not in existing_locations]

    try:
        if partners_to_add:
            logging.info(f"[Main] Inserting {len(partners_to_add)} new telecom partners...")
            session.bulk_save_objects(partners_to_add)
        if locations_to_add:
            logging.info(f"[Main] Inserting {len(locations_to_add)} new locations...")
            session.bulk_save_objects(locations_to_add)
        
        if partners_to_add or locations_to_add:
            session.commit()
            logging.info("[Main] Finished pre-populating parent tables.")
        else:
            logging.info("[Main] All parent records already exist in the database.")

    except Exception as e:
        logging.error(f"[Main] Error during pre-population: {e}", exc_info=True)
        session.rollback()
        raise # Re-raise the exception to stop the main process
    finally:
        session.close()

    # --- 4. Create a map for FK lookups to pass to workers ---
    partner_map = {p.partner_name: p.partner_id for p in session.query(TelecomPartner)}
    # This session is now closed, so we need a new one for the query.
    session = Session()
    try:
        partner_map = {p.partner_name: p.partner_id for p in session.query(TelecomPartner)}
        for row in all_rows:
            row['telecom_partner_id'] = partner_map[row['telecom_partner']]
    finally:
        session.close()

def main():
    """
    Connects to the database, creates tables, and inserts data from a CSV file.
    """
    engine = create_engine(DB_CONNECTION_STRING)

    # 1. Create the database if it doesn't exist
    if not database_exists(engine.url):
        logging.info(f"[Main] Database '{engine.url.database}' does not exist. Creating it...")
        try:
            create_database(engine.url)
            logging.info("[Main] Database created successfully.")
        except ProgrammingError as e:
            logging.error(f"[Main] Error creating database. Please check your MySQL user permissions. Error: {e}")
            return
    else:
        logging.info(f"[Main] Database '{engine.url.database}' already exists.")

    # 2. Create tables
    logging.info("[Main] Creating tables if they don't exist...")
    Base.metadata.create_all(engine)
    logging.info("[Main] Tables checked/created successfully.")

    try:
        # --- Read all data into memory first ---
        logging.info(f"[Main] Reading all rows from {CSV_FILE_PATH} into memory...")
        with open(CSV_FILE_PATH, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            all_rows = list(reader)
        total_rows = len(all_rows)
        logging.info(f"[Main] Finished reading {total_rows} rows.")

        # --- Calculate maximum registration date for tenure calculation ---
        max_reg_date = max(datetime.strptime(row['date_of_registration'], '%Y-%m-%d').date() for row in all_rows)
        logging.info(f"[Main] Maximum registration date: {max_reg_date}")

        # --- Pre-populate parent tables to prevent deadlocks ---
        pre_populate_parents(engine, all_rows)

        # --- Split data into chunks for workers ---
        num_processes = multiprocessing.cpu_count()  # Use as many processes as CPU cores
        chunk_size = (total_rows // num_processes) + 1
        chunks = [all_rows[i:i + chunk_size] for i in range(0, total_rows, chunk_size)]
        logging.info(f"[Main] Splitting data into {len(chunks)} chunks for {num_processes} worker processes.")

        # --- Start multiprocessing pool ---
        with multiprocessing.Pool(processes=num_processes) as pool:
            pool.starmap(process_chunk, [(chunk, max_reg_date) for chunk in chunks])
        
        logging.info("[Main] All worker processes have finished.")

    except FileNotFoundError:
        logging.error(f"[Main] Error: The file {CSV_FILE_PATH} was not found.")
    except Exception as e:
        logging.error(f"[Main] An unhandled error occurred in the main process: {e}", exc_info=True)

if __name__ == '__main__':
    main()
