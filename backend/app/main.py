from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import get_db
from app.api.routes import visitors, conversations, messages, websocket, analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up...")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="Portfolio AI Assistant API",
    description="API for Steven's portfolio AI assistant",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
)


@app.get("/")
async def root():
    return {"message": "Portfolio AI Assistant API"}


@app.get("/api/health")
async def health_check():
    """
    Health check endpoint to verify the API is running.

    Returns:
        dict: Status information including API status and version
    """
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "portfolio-ai-assistant",
    }


# Include routers
app.include_router(visitors.router)
app.include_router(conversations.router)
app.include_router(messages.router)
app.include_router(websocket.router)
app.include_router(analytics.router)
