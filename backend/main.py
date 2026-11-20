import os
import logging
import uuid
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

import crud
from database import Base, SessionLocal, engine
from models import Organization, User
from routes import auth, dashboard, organizations, packages, payments, subscriptions, tenants, users
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
        expired = crud.expire_subscriptions(db)
        crud.cleanup_stale_payments(db)
        if expired:
            _send_expiry_reminders(db)
    finally:
        db.close()


def _send_expiry_reminders(db):
    try:
        if not os.getenv("TWILIO_ACCOUNT_SID"):
            return
        from notifications import send_expiry_reminder
        portal_url = os.getenv("PORTAL_URL", "")
        for sub in crud.get_expiring_soon(db, organization_id=None, days=1):
            tenant = db.query(crud.Tenant).filter(crud.Tenant.id == sub.tenant_id).first()
            if tenant:
                send_expiry_reminder(tenant.name, tenant.phone, 1, portal_url)
    except Exception:
        logger.exception("Failed to send expiry reminders")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


RATE_LIMIT_STORE: dict[str, list[float]] = {}


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        import time
        if request.url.path in ("/health", "/docs", "/openapi.json"):
            return await call_next(request)
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = 60
        max_requests = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
        timestamps = RATE_LIMIT_STORE.get(client_ip, [])
        timestamps = [t for t in timestamps if now - t < window]
        if len(timestamps) >= max_requests:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Too many requests"}, status_code=429)
        timestamps.append(now)
        RATE_LIMIT_STORE[client_ip] = timestamps
        return await call_next(request)


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


app = FastAPI(title="Hotspot Billing SaaS", version="2.0.0", lifespan=lifespan)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMiddleware)

origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(tenants.router)
app.include_router(packages.router)
app.include_router(payments.router)
app.include_router(subscriptions.router)
app.include_router(users.router)
app.include_router(organizations.router)


@app.get("/")
def root():
    return {"name": "Hotspot Billing SaaS", "version": "2.0.0", "status": "ok", "docs": "/docs"}


@app.get("/health")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "healthy", "database": "ok"}
