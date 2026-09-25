from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import crud

router = APIRouter(prefix="/packages", tags=["Packages"])

@router.get("/")
def list_packages(db: Session = Depends(get_db)):
    return crud.get_packages(db)

@router.post("/")
def add_package(name: str, duration_days: int, price: float, db: Session = Depends(get_db)):
    return crud.create_package(db, name, duration_days, price)