from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.database import Base, engine
from app.core.logging_config import configure_logging

from app.models.document import Document

from app.api.routes.documents import (
    router as documents_router,
)


# ============================================================
# Logging
# ============================================================

configure_logging()


# ============================================================
# Paths
# ============================================================

BASE_DIR = Path(
    __file__
).resolve().parents[2]

FRONTEND_DIR = BASE_DIR / "frontend"

STATIC_DIR = FRONTEND_DIR / "static"

TEMPLATE_DIR = FRONTEND_DIR / "templates"


# ============================================================
# Database
# ============================================================

Base.metadata.create_all(
    bind=engine
)


# ============================================================
# FastAPI
# ============================================================

app = FastAPI(
    title="Document Intelligence API",
    description=(
        "AI-powered financial "
        "document processing system"
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://klarix.co.in",
        "https://www.klarix.co.in",
        "https://document-intelligence-1-xmsd.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Static files
# ============================================================

app.mount(
    "/static",
    StaticFiles(
        directory=STATIC_DIR
    ),
    name="static",
)


# ============================================================
# API routes
# ============================================================

app.include_router(
    documents_router,
    prefix="/api/v1/documents",
)


# ============================================================
# Dashboard
# ============================================================

@app.get("/")
def dashboard():

    return FileResponse(
        TEMPLATE_DIR / "dashboard.html"
    )


# ============================================================
# Health
# ============================================================

@app.get("/api/v1/health")
def health_check():

    return {
        "status": "healthy",
        "service": "document-intelligence",
    }



@app.get("/api/v1")
def api_root():
    return {
        "name": "Document Intelligence API",
        "status": "running",
        "version": "v1",
        "docs": "/docs",
    }