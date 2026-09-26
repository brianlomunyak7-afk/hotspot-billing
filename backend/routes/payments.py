from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from pydantic import BaseModel
import crud
import requests
import base64
import os
from datetime import datetime
from dotenv import load_dotenv
from models import PendingPayment

load_dotenv()

router = APIRouter(prefix="/payments", tags=["Payments"])

class STKRequest(BaseModel):
    tenant_id: int
    package_id: int
    phone: str
    amount: float

def get_mpesa_token():
    consumer_key = os.getenv("MPESA_CONSUMER_KEY")
    consumer_secret = os.getenv("MPESA_CONSUMER_SECRET")
    credentials = base64.b64encode(f"{consumer_key}:{consumer_secret}".encode()).decode()
    res = requests.get(
        "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
        headers={"Authorization": f"Basic {credentials}"}
    )
    return res.json().get("access_token")

def generate_password():
    shortcode = os.getenv("MPESA_SHORTCODE")
    passkey = os.getenv("MPESA_PASSKEY")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    raw = f"{shortcode}{passkey}{timestamp}"
    password = base64.b64encode(raw.encode()).decode()
    return password, timestamp

@router.post("/")
def record_payment(tenant_id: int, amount: float, mpesa_code: str, subscription_id: int, db: Session = Depends(get_db)):
    return crud.create_payment(db, tenant_id, amount, mpesa_code, subscription_id)

@router.post("/stk-push")
def stk_push(data: STKRequest, db: Session = Depends(get_db)):
    token = get_mpesa_token()
    password, timestamp = generate_password()
    shortcode = os.getenv("MPESA_SHORTCODE")
    callback_url = os.getenv("CALLBACK_URL")
    phone = data.phone.strip()
    if phone.startswitch("0"):
        phone = "254" + phone[1:]
    elif phone.startswith("+"):
        phonr = phone[1:]

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(data.amount),
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": "HotspotBilling",
        "TransactionDesc": "Internet Payment"
    }

    res = requests.post(
        "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    result = res.json()

    if result.get("ResponseCode") == "0":
        sub = crud.create_subscription(db, data.tenant_id, data.package_id)
        pending = crud.create_pending_payment(db, data.tenant_id, result["CheckoutRequestID"], sub.id, data.amount)
        return {"checkout_request_id": result["CheckoutRequestID"], "subscription_id": sub.id}
    else:
        raise HTTPException(status_code=400, detail=result.get("errorMessage", "STK Push failed"))

@router.post("/callback")
def mpesa_callback(payload: dict, db: Session = Depends(get_db)):
    try:
        body = payload["Body"]["stkCallback"]
        checkout_id = body["CheckoutRequestID"]
        result_code = body["ResultCode"]
        if result_code == 0:
            items = body["CallbackMetadata"]["Item"]
            mpesa_code = next(i["Value"] for i in items if i["Name"] == "MpesaReceiptNumber")
            crud.confirm_payment(db, checkout_id, mpesa_code)
        else:
            crud.fail_payment(db, checkout_id)
    except Exception:
        pass
    return {"ResultCode": 0, "ResultDesc": "Accepted"}

@router.get("/status/{checkout_request_id}")
def payment_status(checkout_request_id: str, db: Session = Depends(get_db)):
    payment = crud.get_payment_by_checkout(db, checkout_request_id)
    if not payment:
        return {"status": "pending"}
    return {"status": payment.status, "mpesa_code": payment.mpesa_code}

@router.get("/all")
def all_payments(db: Session = Depends(get_db)):
    payments = db.query(PendingPayment).all()
    result = []
    for p in payments:
        tenant = crud.get_tenant(db, p.tenant_id)
        result.append({
            "tenant_name": tenant.name if tenant else "Unknown",
            "amount": p.amount,
            "mpesa_code": p.mpesa_code,
            "status": p.status,
            "created_at": p.created_at
        })
    return result