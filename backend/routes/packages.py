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

@router.put("/{package_id}")
def edit_package(package_id: int, name: str, duration_days: int, price: float, db: Session = Depends(get_db)):
    return crud.update_package(db, package_id, name, duration_days, price)

@router.delete("/{package_id}")
def delete_package(package_id: int, db: Session = Depends(get_db)):
    crud.delete_package(db, package_id)
    return {"message": "Package deleted"}