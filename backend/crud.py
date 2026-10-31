import os
import logging
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models import Package, Payment, PendingPayment, Subscription, Tenant


def get_tenants(db: Session, organization_id: int):
    return db.query(Tenant).filter(Tenant.organization_id == organization_id).order_by(Tenant.created_at.desc()).all()


def get_tenant(db: Session, tenant_id: int, organization_id: int):
    return db.query(Tenant).filter(Tenant.id == tenant_id, Tenant.organization_id == organization_id).first()


def create_tenant(db: Session, organization_id: int, name: str, phone: str, router_name: str):
    tenant = Tenant(organization_id=organization_id, name=name.strip(), phone=phone.strip(),
                    router_name=router_name.strip(), hotspot_password=secrets.token_urlsafe(8))
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def toggle_tenant(db: Session, tenant_id: int, organization_id: int, status: bool):
    tenant = get_tenant(db, tenant_id, organization_id)
    if not tenant:
        return None
    tenant.is_active = status
    db.commit()
    db.refresh(tenant)
    return tenant


def delete_tenant(db: Session, tenant_id: int, organization_id: int):
    tenant = get_tenant(db, tenant_id, organization_id)
    if not tenant:
        return False
    db.delete(tenant)
    db.commit()
    return True


def get_packages(db: Session, organization_id: int):
    return db.query(Package).filter(Package.organization_id == organization_id).order_by(Package.price).all()


def get_package(db: Session, package_id: int, organization_id: int):
    return db.query(Package).filter(Package.id == package_id, Package.organization_id == organization_id).first()


def create_package(db: Session, organization_id: int, name: str, duration: int, price: float, duration_type: str):
    package = Package(organization_id=organization_id, name=name.strip(), duration_days=duration,
                      price=price, duration_type=duration_type)
    db.add(package)
    db.commit()
    db.refresh(package)
    return package


def update_package(db: Session, package_id: int, organization_id: int, name: str, duration: int, price: float, duration_type: str):
    package = get_package(db, package_id, organization_id)
    if not package:
        return None
    package.name, package.duration_days, package.price, package.duration_type = name.strip(), duration, price, duration_type
    db.commit()
    db.refresh(package)
    return package


def delete_package(db: Session, package_id: int, organization_id: int):
    package = get_package(db, package_id, organization_id)
    if not package:
        return False
    db.delete(package)
    db.commit()
    return True


def create_subscription(db: Session, organization_id: int, tenant_id: int, package_id: int):
    package = get_package(db, package_id, organization_id)
    tenant = get_tenant(db, tenant_id, organization_id)
    if not package or not tenant:
        return None
    now = datetime.utcnow()
    current = db.query(Subscription).filter(Subscription.tenant_id == tenant_id, Subscription.is_active.is_(True)).first()
    start = max(now, current.end_date) if current else now
    end = start + (timedelta(minutes=package.duration_days) if package.duration_type == "minutes"
                   else timedelta(days=package.duration_days))
    subscription = Subscription(organization_id=organization_id, tenant_id=tenant_id, package_id=package_id,
                                start_date=start, end_date=end, is_active=False)
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def get_expiring_soon(db: Session, organization_id: int, days: int = 2):
    now = datetime.utcnow()
    return db.query(Subscription).filter(Subscription.organization_id == organization_id,
        Subscription.is_active.is_(True), Subscription.end_date <= now + timedelta(days=days),
        Subscription.end_date >= now).all()


def expire_subscriptions(db: Session):
    expired = db.query(Subscription).filter(Subscription.is_active.is_(True), Subscription.end_date < datetime.utcnow()).all()
    for subscription in expired:
        subscription.is_active = False
        tenant = db.query(Tenant).filter(Tenant.id == subscription.tenant_id).first()
        if tenant:
            tenant.is_active = False
    db.commit()
    return expired


def create_pending_payment(db: Session, organization_id: int, tenant_id: int, checkout_request_id: str,
                           subscription_id: int, amount: float):
    pending = PendingPayment(organization_id=organization_id, tenant_id=tenant_id,
                             checkout_request_id=checkout_request_id, subscription_id=subscription_id,
                             amount=amount, status="pending")
    db.add(pending)
    db.commit()
    db.refresh(pending)
    return pending


def get_payment_by_checkout(db: Session, checkout_request_id: str):
    return db.query(PendingPayment).filter(PendingPayment.checkout_request_id == checkout_request_id).first()


def confirm_payment(db: Session, checkout_request_id: str, mpesa_code: str):
    pending = get_payment_by_checkout(db, checkout_request_id)
    if not pending or pending.status == "confirmed":
        return pending
    pending.status, pending.mpesa_code = "confirmed", mpesa_code
    subscription = db.query(Subscription).filter(Subscription.id == pending.subscription_id).first()
    if subscription:
        subscription.is_active = True
        tenant = db.query(Tenant).filter(Tenant.id == subscription.tenant_id).first()
        if tenant:
            tenant.is_active = True
    db.add(Payment(organization_id=pending.organization_id, tenant_id=pending.tenant_id,
                   amount=pending.amount, mpesa_code=mpesa_code, subscription_id=pending.subscription_id))
    db.commit()
    if subscription and tenant and os.getenv("MIKROTIK_HOST"):
        try:
            from mikrotik import grant_hotspot_user
            if not grant_hotspot_user(tenant.phone, tenant.hotspot_password or "", subscription.package.duration_days,
                                      subscription.package.duration_type):
                logging.getLogger("hotspot-billing").error("MikroTik provisioning failed after payment confirmation",
                                                           extra={"tenant_id": tenant.id})
        except Exception as exc:
            logging.getLogger("hotspot-billing").exception("MikroTik provisioning error after payment confirmation",
                                                           extra={"tenant_id": tenant.id})
    return pending


def fail_payment(db: Session, checkout_request_id: str):
    pending = get_payment_by_checkout(db, checkout_request_id)
    if pending and pending.status == "pending":
        pending.status = "failed"
        db.commit()
    return pending


def cleanup_stale_payments(db: Session, minutes: int = 15):
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    count = db.query(PendingPayment).filter(PendingPayment.status == "pending",
        PendingPayment.created_at < cutoff).update({"status": "expired"}, synchronize_session=False)
    db.commit()
    return count
