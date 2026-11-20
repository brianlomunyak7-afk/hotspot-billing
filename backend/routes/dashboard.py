from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Payment, PendingPayment, Subscription, Tenant, User
from routes.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    org = user.organization_id
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    total_tenants = db.query(func.count(Tenant.id)).filter(Tenant.organization_id == org).scalar() or 0
    active_tenants = db.query(func.count(Tenant.id)).filter(
        Tenant.organization_id == org, Tenant.is_active.is_(True)
    ).scalar() or 0
    active_subs = db.query(func.count(Subscription.id)).filter(
        Subscription.organization_id == org, Subscription.is_active.is_(True)
    ).scalar() or 0
    total_revenue = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.organization_id == org
    ).scalar()
    monthly_revenue = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.organization_id == org, Payment.paid_at >= month_start
    ).scalar()
    weekly_revenue = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.organization_id == org, Payment.paid_at >= week_ago
    ).scalar()
    total_payments = db.query(func.count(Payment.id)).filter(Payment.organization_id == org).scalar() or 0
    pending_payments = db.query(func.count(PendingPayment.id)).filter(
        PendingPayment.organization_id == org, PendingPayment.status == "pending"
    ).scalar() or 0

    daily_revenue = []
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).date()
        day_start = datetime.combine(day, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        amount = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
            Payment.organization_id == org, Payment.paid_at >= day_start, Payment.paid_at < day_end
        ).scalar()
        daily_revenue.append({"date": day.isoformat(), "amount": float(amount)})

    recent = (
        db.query(PendingPayment, Tenant.name)
        .outerjoin(Tenant, Tenant.id == PendingPayment.tenant_id)
        .filter(PendingPayment.organization_id == org)
        .order_by(PendingPayment.created_at.desc())
        .limit(5)
        .all()
    )
    recent_payments = [
        {
            "id": p.id,
            "tenant_name": name or "Unknown",
            "amount": p.amount,
            "status": p.status,
            "mpesa_code": p.mpesa_code,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p, name in recent
    ]

    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "active_subscriptions": active_subs,
        "total_revenue": float(total_revenue),
        "monthly_revenue": float(monthly_revenue),
        "weekly_revenue": float(weekly_revenue),
        "total_payments": total_payments,
        "pending_payments": pending_payments,
        "daily_revenue": daily_revenue,
        "recent_payments": recent_payments,
    }
