import asyncio
import sys

# psycopg's async driver cannot run on the ProactorEventLoop that Windows uses
# by default. This covers importers such as tests and scripts; the server has
# to set it even earlier, which is what run.py is for.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import audits, auth, claims, health, policies, uploads, validation
from app.routers.ocr_extraction import router as ocr_router

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
app.include_router(auth.router, prefix="/api/v1")
app.include_router(claims.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(policies.router, prefix="/api/v1", tags=["policies"])
app.include_router(validation.router, prefix="/api/v1", tags=["validation"])
app.include_router(audits.router, prefix="/api/v1", tags=["audits"])
