from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import crud
from database import get_db
from models import Tenant, User
from routes.auth import get_current_user, get_public_organization

router = APIRouter(prefix="/tenants", tags=["Tenants"])


class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    phone: str = Field(min_length=7, max_length=20)
    router_name: str = Field(default="default", max_length=100)


class PublicTenant(BaseModel):
    id: int
    name: str
    phone: str
    is_active: bool


@router.get("/")
def list_tenants(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return crud.get_tenants(db, user.organization_id)


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
