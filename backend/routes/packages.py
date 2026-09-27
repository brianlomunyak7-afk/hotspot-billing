from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from routes.auth import verify_token
import crud

router = APIRouter(prefix="/packages", tags=["Packages"])

# OPEN — used by both admin dashboard AND the client portal to show packages
@router.get("/")
def list_packages(db: Session = Depends(get_db)):
    return crud.get_packages(db)

# LOCKED — only admin should be able to add packages
@router.post("/")
def add_package(name: str, duration_days: int, price: float, duration_type: str = "days",
                 db: Session = Depends(get_db), token: str = Depends(verify_token)):
    return crud.create_package(db, name, duration_days, price, duration_type)

# LOCKED — only admin should be able to edit packages
@router.put("/{package_id}")
def edit_package(package_id: int, name: str, duration_days: int, price: float, duration_type: str = "days",
                  db: Session = Depends(get_db), token: str = Depends(verify_token)):
    return crud.update_package(db, package_id, name, duration_days, price, duration_type)

# LOCKED — only admin should be able to delete packages
@router.delete("/{package_id}")
def delete_package(package_id: int, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    crud.delete_package(db, package_id)
    return {"message": "Package deleted"}