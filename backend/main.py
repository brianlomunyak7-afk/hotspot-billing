import os
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from dotenv import load_dotenv

import crud
from database import Base, SessionLocal, engine
from models import Organization, User
from routes import auth, packages, payments, subscriptions, tenants
from routes.auth import hash_password

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("hotspot-billing")


def bootstrap():
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    for table in ("tenants", "packages", "subscriptions", "payments", "pending_payments"):
        if table in inspector.get_table_names() and "organization_id" not in {c["name"] for c in inspector.get_columns(table)}:
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN organization_id INTEGER"))
    db = SessionLocal()
    try:
        slug = os.getenv("DEFAULT_ORGANIZATION_SLUG", "default")
        organization = db.query(Organization).filter(Organization.slug == slug).first()
        if not organization:
            organization = Organization(name=os.getenv("DEFAULT_ORGANIZATION_NAME", "My Hotspot"), slug=slug)
            db.add(organization)
            db.flush()
        for table in ("tenants", "packages", "subscriptions", "payments", "pending_payments"):
            if table in inspect(engine).get_table_names():
                db.execute(text(f"UPDATE {table} SET organization_id = :organization_id WHERE organization_id IS NULL"),
                           {"organization_id": organization.id})
        username, password = os.getenv("ADMIN_USERNAME"), os.getenv("ADMIN_PASSWORD")
        if username and password and not db.query(User).filter(User.username == username).first():
            db.add(User(organization_id=organization.id, username=username, password_hash=hash_password(password)))
        db.commit()
    finally:
        db.close()


def run_jobs():
    db = SessionLocal()
    try:
        crud.expire_subscriptions(db)
        crud.cleanup_stale_payments(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap()
    scheduler = BackgroundScheduler()
    if os.getenv("ENABLE_SCHEDULER", "true").lower() == "true":
        scheduler.add_job(run_jobs, "interval", minutes=5, id="billing-maintenance", replace_existing=True)
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Hotspot Billing SaaS", version="1.0.0", lifespan=lifespan)
origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(tenants.router)
app.include_router(packages.router)
app.include_router(payments.router)
app.include_router(subscriptions.router)


@app.get("/")
def root():
    return {"name": "Hotspot Billing SaaS", "status": "ok", "docs": "/docs"}


@app.get("/health")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "healthy", "database": "ok"}
