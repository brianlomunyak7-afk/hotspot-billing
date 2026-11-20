from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

import crud
from database import get_db
from models import Package, Subscription, Tenant, User
from routes.auth import get_current_user

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("/")
def list_subscriptions(
    search: str = Query(default="", max_length=100),
    active_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = (
        db.query(Subscription, Tenant.name.label("tenant_name"), Tenant.phone.label("tenant_phone"),
                 Package.name.label("package_name"), Package.price.label("package_price"))
        .outerjoin(Tenant, Tenant.id == Subscription.tenant_id)
        .outerjoin(Package, Package.id == Subscription.package_id)
        .filter(Subscription.organization_id == user.organization_id)
    )
    if active_only:
        q = q.filter(Subscription.is_active.is_(True))
    if search:
        pattern = f"%{search}%"
        q = q.filter(or_(Tenant.name.ilike(pattern), Tenant.phone.ilike(pattern), Package.name.ilike(pattern)))
    total = q.count()
    rows = q.order_by(Subscription.start_date.desc()).offset(offset).limit(limit).all()
    items = []
    for sub, tenant_name, tenant_phone, package_name, package_price in rows:
        items.append({
            "id": sub.id,
            "tenant_id": sub.tenant_id,
            "tenant_name": tenant_name or "Unknown",
            "tenant_phone": tenant_phone or "",
            "package_id": sub.package_id,
            "package_name": package_name or "Unknown",
            "package_price": package_price or 0,
            "start_date": sub.start_date.isoformat() if sub.start_date else None,
            "end_date": sub.end_date.isoformat() if sub.end_date else None,
            "is_active": sub.is_active,
        })
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/")
def create_subscription(tenant_id: int, package_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    subscription = crud.create_subscription(db, user.organization_id, tenant_id, package_id)
    if not subscription:
        raise HTTPException(404, "Tenant or package not found")
    return subscription


@router.get("/expiring")
def expiring_soon(days: int = 2, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return crud.get_expiring_soon(db, user.organization_id, days)
