"""
RQSM-Engine FastAPI Application
Main entry point for the web service
"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import sys
from pathlib import Path

from app.config import settings
from app import __version__


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
)
logger.add(
    "logs/rqsm_engine.log",
    rotation="500 MB",
    retention="10 days",
    level=settings.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("=" * 60)
    logger.info(f"Starting RQSM-Engine v{__version__}")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug mode: {settings.app_debug}")
    logger.info(f"LLM Model: {settings.openai_model}")
    logger.info(f"Database: {settings.database_url}")
    logger.info("=" * 60)
    
    # Ensure required directories exist
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    Path("sample_docs").mkdir(exist_ok=True)
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down RQSM-Engine")
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="RQSM-Engine API",
    description="Role Queue State Machine Educational Dialogue System",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - API health check"""
    return {
        "name": "RQSM-Engine API",
        "version": __version__,
        "status": "operational",
        "environment": settings.app_env
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": __version__,
        "environment": settings.app_env
    }


@app.get("/config")
async def get_config():
    """Get current configuration (non-sensitive values only)"""
    return {
        "llm_model": settings.openai_model,
        "llm_temperature": settings.openai_temperature,
        "llm_max_tokens": settings.openai_max_tokens,
        "role_score_weights": {
            "alpha": settings.role_score_alpha,
            "beta": settings.role_score_beta,
            "gamma": settings.role_score_gamma
        },
        "state_machine": {
            "transition_delay_turns": settings.transition_delay_turns,
            "hysteresis_window_turns": settings.hysteresis_window_turns,
            "reallocation_threshold": settings.reallocation_threshold
        },
        "session": {
            "max_context_window": settings.max_context_window,
            "session_timeout_minutes": settings.session_timeout_minutes
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting development server on {settings.host}:{settings.port}")
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.app_debug,
        log_level=settings.log_level.lower()
    )
