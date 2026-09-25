from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import crud

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.post("/")
def record_payment(tenant_id: int, amount: float, mpesa_code: str, subscription_id: int, db: Session = Depends(get_db)):
    return crud.create_payment(db, tenant_id, amount, mpesa_code, subscription_id)