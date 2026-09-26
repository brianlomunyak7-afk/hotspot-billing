from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

def send_sms(phone: str, message: str):
    try:
        client.messages.create(
            body=message,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            to=phone
        )
    except Exception as e:
        print(f"SMS failed: {e}")

def send_expiry_reminder(tenant_name: str, phone: str, days: int, portal_url: str):
    message = f"Dear {tenant_name}, your internet subscription expires in {days} day(s). Pay now to stay connected: {portal_url}"
    send_sms(phone, message)