"""
main.py
--------
FastAPI application entry point for the Backoffice AI Chatbot Demo.

This is a sanitized, independently implemented demonstration of a modern
Backoffice AI Chatbot architecture. It does NOT contain proprietary source
code, credentials, production data, or confidential company information.

Run locally:
    uvicorn main:app --reload

Then open: http://localhost:8000/docs  (Swagger UI)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    On startup:
      - Seed the SQLite mock database (creates demo_data.db if missing)
      - Pre-build the FAISS RAG index from sample FAQ documents

    On shutdown:
      - Nothing special needed for the demo
    """
    logger.info("[Startup] Initializing Backoffice AI Chatbot Demo...")

    # Seed the mock database
    try:
        from demo.mock_database import DB_PATH, create_database
        if not DB_PATH.exists():
            logger.info("[Startup] Creating mock SQLite database...")
            create_database()
        else:
            logger.info("[Startup] Mock database already exists at: %s", DB_PATH)
    except Exception as exc:
        logger.error("[Startup] Failed to initialize mock database: %s", exc)

    # Pre-build the RAG FAISS index
    try:
        from app.rag.pipeline import rag_pipeline
        logger.info("[Startup] Building FAISS RAG index...")
        rag_pipeline.build_index()
    except Exception as exc:
        logger.warning("[Startup] RAG index build failed (will retry on first query): %s", exc)

    logger.info("[Startup] Ready. Visit http://localhost:8000/docs")
    yield

    logger.info("[Shutdown] Backoffice AI Chatbot Demo shutting down.")


# ── FastAPI app ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Backoffice AI Chatbot — Demo",
    description=(
        "A sanitized portfolio demonstration of a Backoffice AI Chatbot architecture.\n\n"
        "Showcases: LangGraph orchestration, Intent Classification, RAG (FAISS), "
        "Text-to-SQL (SQLite), Tool Routing, Redis session context, "
        "and multilingual (English + Arabic) query handling.\n\n"
        "**This demo uses entirely fictional data and no production connections.**"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS middleware ────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ───────────────────────────────────────────────────────────
app.include_router(router)


# ── Root redirect to docs ──────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

