from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Date,
    Enum,
    Boolean,
    DECIMAL,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DB_CONNECTION_STRING = "mysql+mysqlconnector://root:root@localhost/telecom_updated_db"

Base = declarative_base()
engine = create_engine(DB_CONNECTION_STRING, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TelecomPartner(Base):
    __tablename__ = "telecom_partner"

    partner_id = Column(Integer, primary_key=True, autoincrement=True)
    partner_name = Column(String(50), unique=True, nullable=False)

    customers = relationship("Customer", back_populates="telecom_partner")


class Location(Base):
    __tablename__ = "locations"

    pincode = Column(String(10), primary_key=True)
    city = Column(String(100))
    state = Column(String(100))

    customers = relationship("Customer", back_populates="location")


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(Integer, primary_key=True)
    telecom_partner_id = Column(Integer, ForeignKey("telecom_partner.partner_id"))
    gender = Column(Enum("Male", "Female", "Other", name="gender_enum"))
    age = Column(Integer)
    pincode = Column(String(10), ForeignKey("locations.pincode"))
    date_of_registration = Column(Date)
    tenure = Column(Integer)
    num_dependents = Column(Integer)
    estimated_salary = Column(DECIMAL(12, 2))
    churn = Column(Boolean)
    risk_score = Column(Integer, nullable=True, default=0)
    risk_category = Column(String(20), nullable=True, default="Low Risk")

    telecom_partner = relationship("TelecomPartner", back_populates="customers")
    location = relationship("Location", back_populates="customers")
    usage = relationship("CustomerUsage", back_populates="customer", uselist=False)


class CustomerUsage(Base):
    __tablename__ = "customer_usage"

    customer_id = Column(Integer, ForeignKey("customers.customer_id"), primary_key=True)
    calls_made = Column(Integer)
    sms_sent = Column(Integer)
    data_used = Column(DECIMAL(10, 2))

    customer = relationship("Customer", back_populates="usage")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
