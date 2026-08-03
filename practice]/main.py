from DataProcessingSql import import_csv_to_mysql


if __name__ == "__main__":


    import_csv_to_mysql(
        csv_file="Phase1/telecom_churn_processed.csv",
        db_user="root",
        db_password="root",
        db_host="localhost",
        db_port=3306,
        db_name="telecom_churn_db",
        table_name="telecom_data",
    )




