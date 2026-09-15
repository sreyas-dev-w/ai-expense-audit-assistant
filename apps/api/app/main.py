from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, SessionLocal, engine
from app.routers import claims, employees, health
from app.seed import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        await seed_database(session)

    yield

    await engine.dispose()


app = FastAPI(
    title="AI Expense Audit Assistant API",
    description="Backend API for the AI Expense Audit Assistant.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(employees.router, prefix="/api/v1", tags=["employees"])
app.include_router(claims.router, prefix="/api/v1", tags=["claims"])