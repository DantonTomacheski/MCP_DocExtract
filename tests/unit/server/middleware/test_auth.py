"""
Unit tests for authentication middleware.

These tests verify that the authentication middleware correctly validates
API keys and allows or denies requests based on the authentication rules.
"""

import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.server.middleware.auth import ApiKeyAuth, add_auth_middleware


class TestApiKeyAuth:
    """Tests for the ApiKeyAuth middleware."""
    
    def test_init_with_api_keys(self):
        """Test initialization with API keys provided as arguments."""
        auth = ApiKeyAuth(api_keys=["test_key1", "test_key2"])
        
        assert len(auth.api_keys) == 2
        assert "test_key1" in auth.api_keys
        assert "test_key2" in auth.api_keys
    
    @patch.dict(os.environ, {"DOC_EXTRACT_API_KEY": "env_test_key"})
    def test_init_with_env_variable(self):
        """Test initialization with API key from environment variable."""
        auth = ApiKeyAuth()
        
        assert len(auth.api_keys) == 1
        assert "env_test_key" in auth.api_keys
    
    def test_custom_exempt_paths(self):
        """Test initialization with custom exempt paths."""
        custom_paths = ["/custom", "/api/public"]
        auth = ApiKeyAuth(exempt_paths=custom_paths)
        
        assert auth.exempt_paths == custom_paths
    
    @pytest.mark.asyncio
    async def test_exempt_path_allowed(self):
        """Test that exempt paths are allowed without authentication."""
        auth = ApiKeyAuth(api_keys=["test_key"])
        
        # Create mock request with exempt path
        mock_request = MagicMock()
        mock_request.url.path = "/docs"
        
        # Create mock for the next middleware
        mock_call_next = AsyncMock()
        mock_response = MagicMock()
        mock_call_next.return_value = mock_response
        
        # Call the middleware
        response = await auth(mock_request, mock_call_next)
        
        # Check that the request was passed through
        mock_call_next.assert_called_once_with(mock_request)
        assert response == mock_response
    
    @pytest.mark.asyncio
    async def test_valid_api_key(self):
        """Test that requests with valid API key are allowed."""
        auth = ApiKeyAuth(api_keys=["valid_key"])
        
        # Create mock request with valid API key
        mock_request = MagicMock()
        mock_request.url.path = "/api/extract"
        mock_request.headers = {"X-API-Key": "valid_key"}
        
        # Create mock for the next middleware
        mock_call_next = AsyncMock()
        mock_response = MagicMock()
        mock_call_next.return_value = mock_response
        
        # Call the middleware
        response = await auth(mock_request, mock_call_next)
        
        # Check that the request was passed through
        mock_call_next.assert_called_once_with(mock_request)
        assert response == mock_response
        
        # Check that the API key ID was added to the request state
        assert mock_request.state.api_key_id == 0
    
    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        """Test that requests with invalid API key are rejected."""
        auth = ApiKeyAuth(api_keys=["valid_key"])
        
        # Create mock request with invalid API key
        mock_request = MagicMock()
        mock_request.url.path = "/api/extract"
        mock_request.headers = {"X-API-Key": "invalid_key"}
        mock_request.client.host = "127.0.0.1"
        mock_request.method = "GET"
        
        # Create mock for the next middleware
        mock_call_next = AsyncMock()
        
        # Call the middleware
        response = await auth(mock_request, mock_call_next)
        
        # Check that the next middleware was not called
        mock_call_next.assert_not_called()
        
        # Check the response
        assert response.status_code == 401
        assert "error" in response.body.decode()
        assert "Unauthorized" in response.body.decode()
    
    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        """Test that requests with missing API key are rejected."""
        auth = ApiKeyAuth(api_keys=["valid_key"])
        
        # Create mock request with no API key
        mock_request = MagicMock()
        mock_request.url.path = "/api/extract"
        mock_request.headers = {}
        mock_request.client.host = "127.0.0.1"
        mock_request.method = "GET"
        
        # Create mock for the next middleware
        mock_call_next = AsyncMock()
        
        # Call the middleware
        response = await auth(mock_request, mock_call_next)
        
        # Check that the next middleware was not called
        mock_call_next.assert_not_called()
        
        # Check the response
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_no_api_keys_configured(self):
        """Test behavior when no API keys are configured."""
        auth = ApiKeyAuth(api_keys=[])
        
        # Create mock request
        mock_request = MagicMock()
        mock_request.url.path = "/api/extract"
        mock_request.headers = {}
        
        # Create mock for the next middleware
        mock_call_next = AsyncMock()
        mock_response = MagicMock()
        mock_call_next.return_value = mock_response
        
        # Call the middleware
        response = await auth(mock_request, mock_call_next)
        
        # Check that the request was passed through (auth bypassed)
        mock_call_next.assert_called_once_with(mock_request)
        assert response == mock_response


class TestAddAuthMiddleware:
    """Tests for the add_auth_middleware function."""
    
    def test_adds_middleware_to_app(self):
        """Test that middleware is added to the FastAPI app."""
        # Create mock FastAPI app
        mock_app = MagicMock()
        
        # Call the function
        add_auth_middleware(mock_app, api_keys=["test_key"])
        
        # Check that the middleware was added
        mock_app.middleware.assert_called_once_with("http")
        
        # Get the middleware function
        middleware_decorator = mock_app.middleware.return_value
        middleware_decorator.assert_called_once()
        
        # Check that the middleware function is an ApiKeyAuth instance
        middleware_func = middleware_decorator.call_args[0][0]
        assert isinstance(middleware_func, ApiKeyAuth)
