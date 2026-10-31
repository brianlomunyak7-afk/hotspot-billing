import base64
import os
from datetime import datetime

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import crud
from database import get_db
from models import PendingPayment, User
from routes.auth import get_current_user, get_public_organization

router = APIRouter(prefix="/payments", tags=["Payments"])


class STKRequest(BaseModel):
    tenant_id: int
    package_id: int
    phone: str = Field(min_length=7, max_length=20)


def normalize_phone(phone: str) -> str:
    value = phone.strip().replace(" ", "")
    if value.startswith("+"):
        value = value[1:]
    if value.startswith("0"):
        value = "254" + value[1:]
    if not value.isdigit() or len(value) < 10:
        raise HTTPException(422, "Enter a valid phone number")
    return value


def daraja_base_url() -> str:
    return "https://api.safaricom.co.ke" if os.getenv("MPESA_ENV", "sandbox") == "production" else "https://sandbox.safaricom.co.ke"


def get_mpesa_token() -> str:
    key, secret = os.getenv("MPESA_CONSUMER_KEY"), os.getenv("MPESA_CONSUMER_SECRET")
    if not key or not secret:
        raise HTTPException(503, "M-Pesa is not configured")
    response = requests.get(f"{daraja_base_url()}/oauth/v1/generate?grant_type=client_credentials",
                            auth=(key, secret), timeout=15)
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise HTTPException(503, "M-Pesa authentication failed")
    return token


@router.post("/stk-push")
def stk_push(data: STKRequest, db: Session = Depends(get_db), organization=Depends(get_public_organization)):
    tenant = crud.get_tenant(db, data.tenant_id, organization.id)
    package = crud.get_package(db, data.package_id, organization.id)
    if not tenant or not package:
        raise HTTPException(404, "Tenant or package not found")
    phone = normalize_phone(data.phone)
    shortcode = os.getenv("MPESA_SHORTCODE")
    passkey = os.getenv("MPESA_PASSKEY")
    callback = os.getenv("MPESA_CALLBACK_URL") or os.getenv("CALLBACK_URL")
    if not shortcode or not passkey or not callback:
        raise HTTPException(503, "M-Pesa payment configuration is incomplete")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()
    payload = {"BusinessShortCode": shortcode, "Password": password, "Timestamp": timestamp,
               "TransactionType": "CustomerPayBillOnline", "Amount": int(package.price),
               "PartyA": phone, "PartyB": shortcode, "PhoneNumber": phone,
               "CallBackURL": callback, "AccountReference": f"HB-{organization.slug}",
               "TransactionDesc": f"{package.name} subscription"}
    response = requests.post(f"{daraja_base_url()}/mpesa/stkpush/v1/processrequest", json=payload,
                             headers={"Authorization": f"Bearer {get_mpesa_token()}"}, timeout=20)
    response.raise_for_status()
    result = response.json()
    if result.get("ResponseCode") != "0":
        raise HTTPException(400, result.get("errorMessage") or result.get("ResponseDescription") or "STK push failed")
    subscription = crud.create_subscription(db, organization.id, tenant.id, package.id)
    pending = crud.create_pending_payment(db, organization.id, tenant.id, result["CheckoutRequestID"], subscription.id, package.price)
    return {"checkout_request_id": pending.checkout_request_id, "subscription_id": subscription.id}


@router.post("/callback")
def mpesa_callback(payload: dict, db: Session = Depends(get_db)):
    try:
        body = payload["Body"]["stkCallback"]
        checkout_id, result_code = body["CheckoutRequestID"], body["ResultCode"]
        if result_code == 0:
            receipt = next(item["Value"] for item in body["CallbackMetadata"]["Item"] if item["Name"] == "MpesaReceiptNumber")
            crud.confirm_payment(db, checkout_id, str(receipt))
        else:
            crud.fail_payment(db, checkout_id)
    except (KeyError, StopIteration, TypeError):
        raise HTTPException(400, "Invalid M-Pesa callback")
    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@router.get("/status/{checkout_request_id}")
def payment_status(checkout_request_id: str, db: Session = Depends(get_db)):
    payment = crud.get_payment_by_checkout(db, checkout_request_id)
    return {"status": payment.status if payment else "pending", "mpesa_code": payment.mpesa_code if payment else None}


@router.get("/all")
def all_payments(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(PendingPayment).filter(PendingPayment.organization_id == user.organization_id).order_by(PendingPayment.created_at.desc()).all()
