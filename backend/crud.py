from sqlalchemy.orm import Session
from models import Tenant, Package, Subscription, Payment, PendingPayment
from datetime import datetime, timedelta

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

def delete_tenant(db: Session, tenant_id: int):
    tenant = get_tenant(db, tenant_id)
    db.delete(tenant)
    db.commit()

def get_packages(db: Session):
    return db.query(Package).all()

def get_package(db: Session, package_id: int):
    return db.query(Package).filter(Package.id == package_id).first()

def create_package(db: Session, name: str, duration_days: int, price: float):
    pkg = Package(name=name, duration_days=duration_days, price=price)
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    return pkg

def delete_package(db: Session, package_id: int):
    pkg = get_package(db, package_id)
    db.delete(pkg)
    db.commit()

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

def create_package(db: Session, name: str, duration_days: int, price: float, duration_type: str = "days"):
    pkg = Package(name=name, duration_days=duration_days, price=price, duration_type=duration_type)
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    return pkg

def update_package(db: Session, package_id: int, name: str, duration_days: int, price: float, duration_type: str = "days"):
    pkg = get_package(db, package_id)
    pkg.name = name
    pkg.duration_days = duration_days
    pkg.price = price
    pkg.duration_type = duration_type
    db.commit()
    db.refresh(pkg)
    return pkg

def create_pending_payment(db: Session, tenant_id: int, checkout_request_id: str, subscription_id: int, amount: float):
    pending = PendingPayment(
        tenant_id=tenant_id,
        checkout_request_id=checkout_request_id,
        subscription_id=subscription_id,
        amount=amount,
        status="pending"
    )
    db.add(pending)
    db.commit()
    db.refresh(pending)
    return pending

def get_payment_by_checkout(db: Session, checkout_request_id: str):
    return db.query(PendingPayment).filter(PendingPayment.checkout_request_id == checkout_request_id).first()

def confirm_payment(db: Session, checkout_request_id: str, mpesa_code: str):
    pending = get_payment_by_checkout(db, checkout_request_id)
    if pending:
        pending.status = "confirmed"
        pending.mpesa_code = mpesa_code
        tenant = get_tenant(db, pending.tenant_id)
        if tenant:
            tenant.is_active = True
        db.commit()
    return pending

def fail_payment(db: Session, checkout_request_id: str):
    pending = get_payment_by_checkout(db, checkout_request_id)
    if pending:
        pending.status = "failed"
        db.commit()
    return pending

def update_package(db: Session, package_id: int, name: str, duration_days: int, price: float):
    pkg = get_package(db, package_id)
    pkg.name = name
    pkg.duration_days = duration_days
    pkg.price = price
    db.commit()
    db.refresh(pkg)
    return pkg