from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.ocr_extraction import router as ocr_router
from app.api.employee import router as employee_router
from app.api import audits, claims, health, policies, receipts, validation
from app.core.logging import configure_logging
from app.api.project import router as project_router
from app.api import auth
configure_logging()

app = FastAPI(
    title="AI Expense Audit Assistant API",
    description="Backend API for the AI Expense Audit Assistant.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    # `allow_origins=["*"]` combined with `allow_credentials=True` is an
    # invalid combination per the Fetch/CORS spec (a wildcard origin can't be
    # paired with credentialed requests) — Starlette silently drops the
    # `Access-Control-Allow-Origin` header on preflight when it sees this,
    # which is what breaks every browser request. This app has no
    # cookie-based auth, so credentials are not needed.
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router)
app.include_router(ocr_router)
app.include_router(audits.router, prefix="/api/v1")
app.include_router(claims.router, prefix="/api/v1")
app.include_router(claims.employee_claims_router)
app.include_router(policies.router, prefix="/api/v1", tags=["policies"])
app.include_router(validation.router, prefix="/api/v1", tags=["validation"])
app.include_router(receipts.router)
app.include_router(employee_router)
app.include_router(project_router)
app.include_router(auth.router)