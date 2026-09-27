from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    router_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    hotspot_password = Column(String, nullable=True)   # <-- ADD THIS
    created_at = Column(DateTime, default=datetime.utcnow)
    subscriptions = relationship("Subscription", back_populates="tenant")

class Package(Base):
    __tablename__ = "packages"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    duration_days = Column(Integer, nullable=False)
    duration_type = Column(String, default="days")
    price = Column(Float, nullable=False)
    subscriptions = relationship("Subscription", back_populates="package")

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    package_id = Column(Integer, ForeignKey("packages.id"))
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    tenant = relationship("Tenant", back_populates="subscriptions")
    package = relationship("Package", back_populates="subscriptions")

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    amount = Column(Float, nullable=False)
    mpesa_code = Column(String, nullable=True)
    paid_at = Column(DateTime, default=datetime.utcnow)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)

class PendingPayment(Base):
    __tablename__ = "pending_payments"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    checkout_request_id = Column(String, unique=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"))
    amount = Column(Float)
    status = Column(String, default="pending")
    mpesa_code = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)