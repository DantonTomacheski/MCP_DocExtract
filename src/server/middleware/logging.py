"""
Logging middleware for the DocExtract AI server.

This module provides a middleware for logging HTTP requests and responses
with detailed information for monitoring and debugging.
"""

import time
from typing import Callable
from fastapi import FastAPI, Request, Response
import json

from src.utils.logging import get_logger

logger = get_logger(__name__)


async def log_request_middleware(request: Request, call_next: Callable) -> Response:
    """
    Log incoming requests and outgoing responses.
    
    Args:
        request: The incoming HTTP request
        call_next: The next middleware or route handler
        
    Returns:
        The HTTP response
    """
    # Record start time
    start_time = time.time()
    
    # Get request details
    method = request.method
    path = request.url.path
    client_host = request.client.host if request.client else "unknown"
    
    # Log the request
    logger.info(
        f"Request: {method} {path}",
        extra={
            "client_ip": client_host,
            "method": method,
            "path": path,
            "query_params": str(request.query_params),
            "request_id": request.headers.get("X-Request-ID", "")
        }
    )
    
    # Process the request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log the response
    logger.info(
        f"Response: {response.status_code} ({duration:.3f}s)",
        extra={
            "status_code": response.status_code,
            "duration": duration,
            "content_type": response.headers.get("Content-Type", ""),
            "content_length": response.headers.get("Content-Length", "")
        }
    )
    
    return response


def add_logging_middleware(app: FastAPI) -> None:
    """
    Add request logging middleware to a FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    app.middleware("http")(log_request_middleware)
