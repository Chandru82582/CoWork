import csv
from pathlib import Path
from typing import List, Sequence, Tuple

from sqlCon import connect_to_mysql


def read_csv_rows(csv_file: str) -> Tuple[List[str], List[List[str]]]:
    """Read the header and rows from a CSV file."""
    with open(csv_file, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = [row for row in reader]
    return header, rows


def create_table_if_not_exists(cursor, table_name: str, columns: Sequence[str]) -> None:
    """Create a table dynamically from the CSV header."""
    columns_with_types = [f"`{column}` TEXT" for column in columns]
    create_table_query = (
        f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns_with_types)})"
    )
    cursor.execute(create_table_query)


def insert_rows(cursor, table_name: str, columns: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    """Insert each CSV row into the target table."""
    placeholders = ", ".join(["%s"] * len(columns))
    column_names = ", ".join([f"`{column}`" for column in columns])
    insert_query = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"

    for row in rows:
        cursor.execute(insert_query, row)


def import_csv_to_mysql(
    csv_file: str,
    db_user: str,
    db_password: str,
    db_host: str,
    db_port: int,
    db_name: str,
    table_name: str = "telecom_data",
):
    """Import a CSV file into a MySQL table using modular helper functions."""
    csv_path = Path(csv_file)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    connection = connect_to_mysql(db_user, db_password, db_host, db_port, db_name)
    cursor = None

    try:
        cursor = connection.cursor()
        header, rows = read_csv_rows(str(csv_path))
        create_table_if_not_exists(cursor, table_name, header)
        insert_rows(cursor, table_name, header, rows)
        connection.commit()
        print(
            f"Data from {csv_path.name} successfully inserted into table '{table_name}' in database {db_name}."
        )
        return {"rows_imported": len(rows), "table_name": table_name}
    except Exception as exc:
        connection.rollback()
        raise RuntimeError(f"An error occurred while importing CSV data: {exc}") from exc
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()