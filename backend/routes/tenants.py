from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

import crud
from database import get_db
from models import Subscription, Tenant, User
from routes.auth import get_current_user, get_public_organization

router = APIRouter(prefix="/tenants", tags=["Tenants"])


class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    phone: str = Field(min_length=7, max_length=20)
    router_name: str = Field(default="default", max_length=100)


class TenantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    router_name: str | None = Field(default=None, max_length=100)


class PublicTenant(BaseModel):
    id: int
    name: str
    phone: str
    is_active: bool
    hotspot_password: str | None = None


@router.get("/")
def list_tenants(
    search: str = Query(default="", max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Tenant).filter(Tenant.organization_id == user.organization_id)
    if search:
        pattern = f"%{search}%"
        q = q.filter(or_(Tenant.name.ilike(pattern), Tenant.phone.ilike(pattern)))
    total = q.count()
    tenants = q.order_by(Tenant.created_at.desc()).offset(offset).limit(limit).all()
    items = []
    for t in tenants:
        active_sub = db.query(Subscription).filter(
            Subscription.tenant_id == t.id, Subscription.is_active.is_(True)
        ).first()
        items.append({
            "id": t.id,
            "name": t.name,
            "phone": t.phone,
            "router_name": t.router_name,
            "is_active": t.is_active,
            "hotspot_password": t.hotspot_password,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "subscription_end": active_sub.end_date.isoformat() if active_sub else None,
        })
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/")
def add_tenant(data: TenantCreate, db: Session = Depends(get_db), organization=Depends(get_public_organization)):
    return crud.create_tenant(db, organization.id, data.name, data.phone, data.router_name)


@router.get("/public", response_model=PublicTenant | dict)
def find_public_tenant(phone: str, db: Session = Depends(get_db), organization=Depends(get_public_organization)):
    tenant = db.query(Tenant).filter(
        Tenant.organization_id == organization.id,
        Tenant.phone == phone,
    ).first()
    return tenant if tenant else {}


@router.get("/public/status")
def tenant_status(phone: str, db: Session = Depends(get_db), organization=Depends(get_public_organization)):
    tenant = db.query(Tenant).filter(
        Tenant.organization_id == organization.id, Tenant.phone == phone
    ).first()
    if not tenant:
        return {"found": False}
    active_sub = db.query(Subscription).filter(
        Subscription.tenant_id == tenant.id, Subscription.is_active.is_(True)
    ).first()
    return {
        "found": True,
        "name": tenant.name,
        "is_active": tenant.is_active,
        "subscription_active": active_sub is not None,
        "subscription_end": active_sub.end_date.isoformat() if active_sub else None,
    }


@router.put("/{tenant_id}")
def update_tenant(tenant_id: int, data: TenantUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tenant = crud.get_tenant(db, tenant_id, user.organization_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    if data.name is not None:
        tenant.name = data.name.strip()
    if data.phone is not None:
        tenant.phone = data.phone.strip()
    if data.router_name is not None:
        tenant.router_name = data.router_name.strip()
    db.commit()
    db.refresh(tenant)
    return tenant


@router.put("/{tenant_id}/toggle")
def toggle_tenant(tenant_id: int, status: bool, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tenant = crud.toggle_tenant(db, tenant_id, user.organization_id, status)
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    return tenant


@router.delete("/{tenant_id}")
def delete_tenant(tenant_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not crud.delete_tenant(db, tenant_id, user.organization_id):
        raise HTTPException(404, "Tenant not found")
    return {"message": "Tenant deleted"}
