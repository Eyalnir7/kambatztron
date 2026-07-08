"""FastAPI app entry point: python -m uvicorn api.main:app --reload"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.session import Base, engine
from db import models  # noqa: F401 -- registers tables on Base.metadata
from api import auth
from api.routers import manager, cadet

app = FastAPI(title="Kambatztron API")

cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    # Convenience for local/dev use; in a real deployment `alembic upgrade head`
    # is the source of truth for schema changes.
    Base.metadata.create_all(engine)


app.include_router(auth.router)
app.include_router(manager.router)
app.include_router(cadet.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
