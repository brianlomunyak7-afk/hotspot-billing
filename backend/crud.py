from sqlalchemy.orm import Session
from models import Tenant, Package, Subscription, Payment
from datetime import datetime, timedelta

# --- TENANTS ---
def get_tenants(db: Session):
    return db.query(Tenant).all()

def get_tenant(db: Session, tenant_id: int):
    return db.query(Tenant).filter(Tenant.id == tenant_id).first()

def create_tenant(db: Session, name: str, phone: str, router_name: str):
    tenant = Tenant(name=name, phone=phone, router_name=router_name)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant

def toggle_tenant(db: Session, tenant_id: int, status: bool):
    tenant = get_tenant(db, tenant_id)
    tenant.is_active = status
    db.commit()
    return tenant

# --- PACKAGES ---
def get_packages(db: Session):
    return db.query(Package).all()

def create_package(db: Session, name: str, duration_days: int, price: float):
    pkg = Package(name=name, duration_days=duration_days, price=price)
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    return pkg

# --- SUBSCRIPTIONS ---
def create_subscription(db: Session, tenant_id: int, package_id: int):
    pkg = db.query(Package).filter(Package.id == package_id).first()
    end_date = datetime.utcnow() + timedelta(days=pkg.duration_days)
    sub = Subscription(tenant_id=tenant_id, package_id=package_id, end_date=end_date)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub

def get_expiring_soon(db: Session, days: int = 2):
    now = datetime.utcnow()
    threshold = now + timedelta(days=days)
    return db.query(Subscription).filter(
        Subscription.is_active == True,
        Subscription.end_date <= threshold,
        Subscription.end_date >= now
    ).all()

def expire_subscriptions(db: Session):
    now = datetime.utcnow()
    expired = db.query(Subscription).filter(
        Subscription.is_active == True,
        Subscription.end_date < now
    ).all()
    for sub in expired:
        sub.is_active = False
        tenant = get_tenant(db, sub.tenant_id)
        if tenant:
            tenant.is_active = False
    db.commit()
    return expired

# --- PAYMENTS ---
def create_payment(db: Session, tenant_id: int, amount: float, mpesa_code: str, subscription_id: int):
    payment = Payment(
        tenant_id=tenant_id,
        amount=amount,
        mpesa_code=mpesa_code,
        subscription_id=subscription_id
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment