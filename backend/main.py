from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routes import tenants, packages, payments, subscriptions
from apscheduler.schedulers.background import BackgroundScheduler
from database import SessionLocal
import crud

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hotspot Billing System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tenants.router)
app.include_router(packages.router)
app.include_router(payments.router)
app.include_router(subscriptions.router)

def daily_check():
    db = SessionLocal()
    try:
        crud.expire_subscriptions(db)
        expiring = crud.get_expiring_soon(db, days=2)
        for sub in expiring:
            tenant = sub.tenant
            if tenant and tenant.phone:
                from notifications import send_expiry_reminder
                send_expiry_reminder(
                    tenant.name,
                    tenant.phone if tenant.phone.startswith("+") else "+" + tenant.phone,
                    2,
                    "http://your-portal-url/portal"
                )
    finally:
        db.close()

@app.get("/")
def root():
    return {"message": "Hotspot Billing System Running"}