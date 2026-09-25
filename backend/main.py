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
        expired = crud.expire_subscriptions(db)
        expiring = crud.get_expiring_soon(db, days=2)
        for sub in expiring:
            print(f"Reminder: {sub.tenant.name} {sub.tenant.phone} expires {sub.end_date}")
    finally:
        db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(daily_check, "interval", hours=24)
scheduler.start()

@app.get("/")
def root():
    return {"message": "Hotspot Billing System Running"}