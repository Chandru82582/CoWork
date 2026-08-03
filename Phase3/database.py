from sqlalchemy import Boolean, Column, Date, DECIMAL, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker


DB_CONNECTION_STRING = "mysql+mysqlconnector://root:root@localhost/telecom_db"

Base = declarative_base()
engine = create_engine(DB_CONNECTION_STRING, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TelecomPartner(Base):
    __tablename__ = "telecom_partner"

    partner_id = Column(Integer, primary_key=True, autoincrement=True)
    partner_name = Column(String(50), unique=True, nullable=False)

    customers = relationship("Customer", back_populates="telecom_partner")


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(Integer, primary_key=True)
    telecom_partner_id = Column(Integer, ForeignKey("telecom_partner.partner_id"))
    gender = Column(String(20))
    age = Column(Integer)
    pincode = Column(String(10))
    date_of_registration = Column(Date)
    num_dependents = Column(Integer)
    estimated_salary = Column(DECIMAL(12, 2))
    churn = Column(Boolean)

    telecom_partner = relationship("TelecomPartner", back_populates="customers")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
