from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routes import tenants, packages, payments, subscriptions, auth
from apscheduler.schedulers.background import BackgroundScheduler
from database import SessionLocal
import crud

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Phantech Billing System")

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
app.include_router(auth.router)

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

scheduler = BackgroundScheduler()
scheduler.add_job(daily_check, 'interval', hours=24)

def cleanup_payments_job():
    db = SessionLocal()
    try:
        deleted = crud.cleanup_stale_payments(db, minutes=3)
        print(f"Cleanup: removed {deleted} stale pending/failed payments")
    finally:
        db.close()

scheduler.add_job(cleanup_payments_job, 'interval', minutes=3)
scheduler.start()