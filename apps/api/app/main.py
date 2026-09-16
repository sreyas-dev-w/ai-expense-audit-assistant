from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.ocr_extraction import router as ocr_router
from app.routers import audits, auth, claims, dashboard, health, policies, uploads

from app.api import health, policies

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
app.include_router(health.router, prefix="/api/v1", tags=["health"])