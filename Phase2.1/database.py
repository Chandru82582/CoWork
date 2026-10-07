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
from sqlalchemy.orm import declarative_base, relationship

#Hi am GTG

Base = declarative_base()

class TelecomPartner(Base):
    __tablename__ = 'telecom_partner'

    partner_id = Column(Integer, primary_key=True, autoincrement=True)
    partner_name = Column(String(50), unique=True, nullable=False)

    # Relationship to the 'customers' table
    customers = relationship("Customer", back_populates="telecom_partner")

class Location(Base):
    __tablename__ = 'locations'

    pincode = Column(String(10), primary_key=True)
    city = Column(String(100))
    state = Column(String(100))

    # Relationship to the 'customers' table
    customers = relationship("Customer", back_populates="location")

class Customer(Base):
    __tablename__ = 'customers'

    customer_id = Column(Integer, primary_key=True)
    telecom_partner_id = Column(Integer, ForeignKey('telecom_partner.partner_id'))
    gender = Column(Enum('Male', 'Female', 'Other', name='gender_enum'))
    age = Column(Integer)
    pincode = Column(String(10), ForeignKey('locations.pincode'))
    date_of_registration = Column(Date)
    tenure = Column(Integer)
    num_dependents = Column(Integer)
    estimated_salary = Column(DECIMAL(12, 2))
    churn = Column(Boolean)
    risk_score = Column(Integer, nullable=True, default=0)
    risk_category = Column(String(20), nullable=True, default='Low Risk')

    # Relationships to other tables
    telecom_partner = relationship("TelecomPartner", back_populates="customers")
    location = relationship("Location", back_populates="customers")
    usage = relationship("CustomerUsage", back_populates="customer", uselist=False)

class CustomerUsage(Base):
    __tablename__ = 'customer_usage'

    customer_id = Column(Integer, ForeignKey('customers.customer_id'), primary_key=True)
    calls_made = Column(Integer)
    sms_sent = Column(Integer)
    data_used = Column(DECIMAL(10, 2))

    # Relationship to the 'customers' table
    customer = relationship("Customer", back_populates="usage")



