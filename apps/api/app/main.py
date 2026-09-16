from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers currently implemented in app/api
from app.api import health, policies
from app.api.ocr_extraction import router as ocr_router

# Routers currently implemented in app/routers
from app.routers import audits, auth, claims, dashboard, uploads


app = FastAPI(
    title="AI Expense Audit Assistant API",
    description="Backend API for the AI Expense Audit Assistant.",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# OCR already includes /api/v1 in its router prefix.
app.include_router(ocr_router)

# These routers contain only their resource prefix.
app.include_router(
    health.router,
    prefix="/api/v1",
)
app.include_router(
    auth.router,
    prefix="/api/v1",
)
app.include_router(
    uploads.router,
    prefix="/api/v1",
)
app.include_router(
    policies.router,
    prefix="/api/v1",
)
app.include_router(
    claims.router,
    prefix="/api/v1",
)
app.include_router(
    audits.router,
    prefix="/api/v1",
)
app.include_router(
    dashboard.router,
    prefix="/api/v1",
)


@app.get("/", tags=["Root"])
def root() -> dict[str, str]:
    return {
        "message": "AI Expense Audit Assistant API",
        "docs": "/docs",
        "health": "/api/v1/health",
    }