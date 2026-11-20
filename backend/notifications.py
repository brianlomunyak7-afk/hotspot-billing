import logging
import os

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("hotspot-billing.notifications")

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        return None
    try:
        from twilio.rest import Client
        _client = Client(sid, token)
        return _client
    except Exception:
        logger.exception("Failed to initialize Twilio client")
        return None


def send_sms(phone: str, message: str) -> bool:
    client = _get_client()
    if not client:
        logger.debug("SMS skipped — Twilio not configured")
        return False
    try:
        client.messages.create(
            body=message,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            to=phone,
        )
        return True
    except Exception:
        logger.exception("SMS send failed to %s", phone)
        return False


def send_payment_receipt(tenant_name: str, phone: str, amount: float, mpesa_code: str, package_name: str):
    message = (
        f"Hi {tenant_name}, your payment of KES {amount:.0f} for {package_name} has been received. "
        f"M-Pesa receipt: {mpesa_code}. You are now connected. Enjoy!"
    )
    send_sms(phone, message)


def send_expiry_reminder(tenant_name: str, phone: str, days: int, portal_url: str):
    message = (
        f"Dear {tenant_name}, your internet subscription expires in {days} day(s). "
        f"Pay now to stay connected: {portal_url}"
    )
    send_sms(phone, message)
