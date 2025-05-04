"""
Authentication middleware for the DocExtract AI server.

This module provides authentication middleware that validates API keys
against configured values, ensuring secure access to the API endpoints.
"""

import os
from typing import Callable, Dict, List, Optional
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import logging

from src.utils.logging import get_logger

logger = get_logger(__name__)


class ApiKeyAuth:
    """
    API key authentication middleware.
    
    This middleware validates that incoming requests contain a valid API key
    in the X-API-Key header. API keys are loaded from environment variables
    or a configuration file.
    """
    
    def __init__(
        self, 
        api_keys: Optional[List[str]] = None,
        env_key: str = "DOC_EXTRACT_API_KEY",
        exempt_paths: Optional[List[str]] = None
    ):
        """
        Initialize the API key authentication middleware.
        
        Args:
            api_keys: Optional list of valid API keys
            env_key: Environment variable name for the API key
            exempt_paths: List of paths exempt from authentication
        """
        self.api_keys: List[str] = []
        
        # Load API keys from parameters
        if api_keys:
            self.api_keys.extend(api_keys)
        
        # Load API key from environment
        env_api_key = os.environ.get(env_key)
        if env_api_key:
            self.api_keys.append(env_api_key)
            
        # Default exempt paths
        self.exempt_paths = exempt_paths or [
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/metrics"
        ]
        
        logger.info(f"API Key authentication configured with {len(self.api_keys)} keys")
        logger.debug(f"Exempt paths: {', '.join(self.exempt_paths)}")
    
    async def __call__(
        self, 
        request: Request, 
        call_next: Callable
    ) -> Response:
        """
        Process the request through the authentication middleware.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler
            
        Returns:
            The HTTP response
        """
        # Check if the path is exempt
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Check for API key
        api_key = request.headers.get("X-API-Key")
        
        # If no API keys are configured, bypass authentication
        if not self.api_keys:
            logger.warning("No API keys configured, authentication bypassed")
            return await call_next(request)
            
        # Check if the API key is valid
        if api_key in self.api_keys:
            # Add the key ID to the request state for audit logging
            request.state.api_key_id = self.api_keys.index(api_key)
            return await call_next(request)
        
        # Log the failed authentication attempt
        client_host = request.client.host if request.client else "unknown"
        logger.warning(
            f"Authentication failed: invalid API key",
            context={
                "client_ip": client_host,
                "path": request.url.path,
                "method": request.method
            }
        )
        
        # Return an unauthorized response
        return JSONResponse(
            status_code=401,
            content={
                "error": "Unauthorized",
                "message": "Invalid or missing API key"
            }
        )


def add_auth_middleware(
    app: FastAPI,
    api_keys: Optional[List[str]] = None,
    env_key: str = "DOC_EXTRACT_API_KEY",
    exempt_paths: Optional[List[str]] = None
) -> None:
    """
    Add authentication middleware to a FastAPI application.
    
    Args:
        app: FastAPI application instance
        api_keys: Optional list of valid API keys
        env_key: Environment variable name for the API key
        exempt_paths: List of paths exempt from authentication
    """
    auth_middleware = ApiKeyAuth(api_keys, env_key, exempt_paths)
    app.middleware("http")(auth_middleware)


def api_key_auth(api_key: str = None):
    """
    FastAPI dependency for API key authentication.
    
    This function is used as a dependency in FastAPI routes to validate
    that the request contains a valid API key in the X-API-Key header.
    
    Args:
        api_key: API key passed as a header parameter
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: If the API key is invalid or missing
    """
    from fastapi import HTTPException, Security, Depends
    from fastapi.security import APIKeyHeader
    
    # If no API key passed as parameter, use header
    if not api_key:
        # Setup API key security scheme
        api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
        
        # Check if the API key is provided
        api_key = Depends(api_key_header)
    
    # Load API key from environment
    env_api_key = os.environ.get("DOC_EXTRACT_API_KEY")
    
    # If no API key is configured, bypass authentication
    if not env_api_key:
        logger.warning("No API key configured, authentication bypassed")
        return api_key
    
    # Check if the API key is valid
    if api_key != env_api_key:
        logger.warning("Authentication failed: invalid API key")
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )
    
    return api_key
