from sqlalchemy import create_engine


def connect_to_mysql(db_user, db_password, db_host, db_port, db_name):
    """Create a MySQL connection using SQLAlchemy."""
    try:
        connection_string = (
            f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        )
        engine = create_engine(connection_string)
        return engine.raw_connection()
    except Exception as exc:
        raise RuntimeError(f"Unable to connect to MySQL: {exc}") from exc