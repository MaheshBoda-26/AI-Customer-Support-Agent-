"""
FastAPI application entrypoint for AI Customer Support Agent.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.api import chat, conversations, tickets, ingest


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    setup_logging()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="AI Customer Support Agent",
        description="24/7 AI-powered customer support with RAG, ticketing, and human handoff",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
    app.include_router(conversations.router, prefix="/api/v1", tags=["conversations"])
    app.include_router(tickets.router, prefix="/api/v1", tags=["tickets"])
    app.include_router(ingest.router, prefix="/api/v1", tags=["ingest"])

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app


app = create_app()