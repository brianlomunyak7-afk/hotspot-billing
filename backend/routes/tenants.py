from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from routes.auth import verify_token
import crud

router = APIRouter(prefix="/tenants", tags=["Tenants"])

# OPEN — the client portal needs this to check/register itself when paying
@router.get("/")
def list_tenants(db: Session = Depends(get_db)):
    return crud.get_tenants(db)

# OPEN — the client portal registers new tenants when they pay for the first time
@router.post("/")
def add_tenant(name: str, phone: str, router_name: str, db: Session = Depends(get_db)):
    return crud.create_tenant(db, name, phone, router_name)

# LOCKED — only admin should enable/disable tenants manually
@router.put("/{tenant_id}/toggle")
def toggle_tenant(tenant_id: int, status: bool, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    return crud.toggle_tenant(db, tenant_id, status)

# LOCKED — only admin should delete tenants
@router.delete("/{tenant_id}")
def delete_tenant(tenant_id: int, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    crud.delete_tenant(db, tenant_id)
    return {"message": "Tenant deleted"}