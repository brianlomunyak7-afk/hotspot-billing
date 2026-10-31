from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import crud
from database import get_db
from models import User
from routes.auth import get_current_user, get_public_organization

router = APIRouter(prefix="/packages", tags=["Packages"])


class PackageInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    duration_days: int = Field(gt=0, le=3650)
    price: float = Field(ge=0, le=1_000_000)
    duration_type: str = Field(default="days", pattern="^(days|minutes)$")


@router.get("/")
def list_packages(db: Session = Depends(get_db), organization=Depends(get_public_organization)):
    return crud.get_packages(db, organization.id)


@router.post("/")
def add_package(data: PackageInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return crud.create_package(db, user.organization_id, data.name, data.duration_days, data.price, data.duration_type)


@router.put("/{package_id}")
def edit_package(package_id: int, data: PackageInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    package = crud.update_package(db, package_id, user.organization_id, data.name, data.duration_days, data.price, data.duration_type)
    if not package:
        raise HTTPException(404, "Package not found")
    return package


@router.delete("/{package_id}")
def delete_package(package_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not crud.delete_package(db, package_id, user.organization_id):
        raise HTTPException(404, "Package not found")
    return {"message": "Package deleted"}
