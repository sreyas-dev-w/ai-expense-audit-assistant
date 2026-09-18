from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.ocr_extraction import router as ocr_router

from app.api import audits, claims, health, policies, validation
from app.core.logging import configure_logging

configure_logging()

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
app.include_router(ocr_router)
app.include_router(audits.router, prefix="/api/v1")
app.include_router(claims.router, prefix="/api/v1")
app.include_router(policies.router, prefix="/api/v1", tags=["policies"])
app.include_router(validation.router, prefix="/api/v1", tags=["validation"])
