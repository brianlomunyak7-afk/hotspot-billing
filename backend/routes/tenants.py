from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import crud

router = APIRouter(prefix="/tenants", tags=["Tenants"])

@router.get("/")
def list_tenants(db: Session = Depends(get_db)):
    return crud.get_tenants(db)

@router.post("/")
def add_tenant(name: str, phone: str, router_name: str, db: Session = Depends(get_db)):
    return crud.create_tenant(db, name, phone, router_name)

@router.put("/{tenant_id}/toggle")
def toggle_tenant(tenant_id: int, status: bool, db: Session = Depends(get_db)):
    return crud.toggle_tenant(db, tenant_id, status)