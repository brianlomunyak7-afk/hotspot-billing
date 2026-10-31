from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    router_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    hotspot_password = Column(String, nullable=True)   # <-- ADD THIS
    created_at = Column(DateTime, default=datetime.utcnow)
    subscriptions = relationship("Subscription", back_populates="tenant")
    organization = relationship("Organization", back_populates="tenants")

class Package(Base):
    __tablename__ = "packages"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    duration_days = Column(Integer, nullable=False)
    duration_type = Column(String, default="days")
    price = Column(Float, nullable=False)
    subscriptions = relationship("Subscription", back_populates="package")
    organization = relationship("Organization", back_populates="packages")

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
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
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    amount = Column(Float, nullable=False)
    mpesa_code = Column(String, nullable=True)
    paid_at = Column(DateTime, default=datetime.utcnow)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)

class PendingPayment(Base):
    __tablename__ = "pending_payments"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    checkout_request_id = Column(String, unique=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"))
    amount = Column(Float)
    status = Column(String, default="pending")
    mpesa_code = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    tenants = relationship("Tenant", back_populates="organization")
    packages = relationship("Package", back_populates="organization")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    username = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="admin", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("organization_id", "username", name="uq_org_username"),)