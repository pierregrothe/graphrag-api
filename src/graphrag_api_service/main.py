# src/graphrag_api_service/main.py
# Main FastAPI application for GraphRAG API Service
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Main FastAPI application module for GraphRAG API service."""

from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    yield
    logger.info("Shutting down application")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A FastAPI-based API for the microsoft/graphrag library",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.error(f"HTTP error {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors."""
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"error": "Validation error", "details": exc.errors()},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    logger.exception(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": str(exc) if settings.debug else "An unexpected error occurred"},
    )


@app.get("/", tags=["Health"])
async def read_root() -> Dict[str, Any]:
    """Root endpoint providing basic API information.
    
    Returns:
        Dict containing API name, version, and status
    """
    logger.info("Root endpoint accessed")
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """Health check endpoint.
    
    Returns:
        Dict containing health status
    """
    logger.debug("Health check accessed")
    return {"status": "healthy"}


@app.get("/info", tags=["Information"])
async def get_info() -> Dict[str, Any]:
    """Get application information and configuration.
    
    Returns:
        Dict containing application information
    """
    logger.info("Info endpoint accessed")
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
        "log_level": settings.log_level,
        "graphrag_config_path": settings.graphrag_config_path,
        "graphrag_data_path": settings.graphrag_data_path,
    }
