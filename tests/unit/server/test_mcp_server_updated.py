"""
Unit tests for the updated MCP server implementation.

These tests verify that the new FastAPI-based MCP server routes and handlers work correctly.
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from src.server.mcp_server import app, controller, scrape_tool, status_tool, mcp_tools_handler
from src.server.schemas.requests import ScrapeRequest, OperationStatusRequest


@pytest.fixture
def client():
    """Create a TestClient for the FastAPI app."""
    return TestClient(app)


class TestMCPServerEndpoints:
    """Tests for the MCP server endpoints."""
    
    def test_default_endpoint(self, client):
        """Test the default endpoint returns the correct message."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "DocExtract AI MCP Server"}
    
    def test_health_check(self, client):
        """Test the health check endpoint returns the correct status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert "timestamp" in response.json()
    
    @patch("src.controllers.main_controller.MainController.async_run")
    def test_scrape_tool(self, mock_async_run, client):
        """Test the scrape endpoint processes requests correctly."""
        # Mock the controller's async_run method
        mock_async_run.return_value = {
            "operation_id": "test_op_123",
            "status": "running",
            "message": "Scraping operation started"
        }
        
        # Create a mock user for the Depends(api_key_auth)
        with patch("src.server.middleware.auth.api_key_auth", return_value={"user": "test_user"}):
            # Test with valid parameters
            response = client.post(
                "/mcp/scrape",
                json={
                    "url": "https://example.com/docs/",
                    "mode": "auto",
                    "max_depth": 3,
                    "parallel": False,
                    "export_format": "both"
                }
            )
            
            assert response.status_code == 200
            assert response.json()["operation_id"] == "test_op_123"
            assert response.json()["status"] == "running"
            
            # Verify the controller was called with correct parameters
            mock_async_run.assert_called_once()
            call_args = mock_async_run.call_args[1]
            assert call_args["url"] == "https://example.com/docs/"
            assert call_args["mode"] == "auto"
            assert call_args["max_depth"] == 3
            assert call_args["parallel"] is False
            assert call_args["export_format"] == "both"
    
    def test_scrape_tool_validation(self, client):
        """Test that the scrape endpoint validates parameters correctly."""
        # Override auth for testing
        with patch("src.server.middleware.auth.api_key_auth", return_value={"user": "test_user"}):
            # Test with invalid mode
            response = client.post(
                "/mcp/scrape",
                json={
                    "url": "https://example.com/docs/",
                    "mode": "invalid_mode",
                    "max_depth": 3
                }
            )
            
            assert response.status_code == 422  # Validation error
            
            # Test with invalid max_depth
            response = client.post(
                "/mcp/scrape",
                json={
                    "url": "https://example.com/docs/",
                    "max_depth": 20  # Too large
                }
            )
            
            assert response.status_code == 422  # Validation error
            
            # Test with missing required url
            response = client.post(
                "/mcp/scrape",
                json={
                    "mode": "auto"
                }
            )
            
            assert response.status_code == 422  # Validation error
    
    @patch("src.controllers.main_controller.MainController.get_operation_status")
    def test_status_tool(self, mock_get_status, client):
        """Test the operation status endpoint returns correct information."""
        # Mock the controller's get_operation_status method
        mock_get_status.return_value = {
            "operation_id": "test_op_123",
            "status": "running",
            "progress": 45.0,
            "urls_discovered": 10,
            "urls_processed": 5
        }
        
        # Override auth for testing
        with patch("src.server.middleware.auth.api_key_auth", return_value={"user": "test_user"}):
            # Test with valid operation ID
            response = client.post(
                "/mcp/operation_status",
                json={
                    "operation_id": "test_op_123"
                }
            )
            
            assert response.status_code == 200
            assert response.json()["operation_id"] == "test_op_123"
            assert response.json()["status"] == "running"
            assert response.json()["progress"] == 45.0
            
            # Verify the controller was called with correct parameters
            mock_get_status.assert_called_once_with("test_op_123")
    
    @patch("src.controllers.main_controller.MainController.get_operation_status")
    def test_status_tool_not_found(self, mock_get_status, client):
        """Test the operation status endpoint handles not found operations correctly."""
        # Mock the controller raising a KeyError for non-existent operation
        mock_get_status.side_effect = KeyError("Operation not found")
        
        # Override auth for testing
        with patch("src.server.middleware.auth.api_key_auth", return_value={"user": "test_user"}):
            # Test with non-existent operation ID
            response = client.post(
                "/mcp/operation_status",
                json={
                    "operation_id": "non_existent"
                }
            )
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]
    
    @patch("src.server.mcp_server.scrape_tool")
    @patch("src.server.mcp_server.status_tool")
    def test_mcp_tools_handler(self, mock_status_tool, mock_scrape_tool, client):
        """Test that the MCP tools handler routes requests correctly."""
        # Mock the scrape and status tools
        mock_scrape_result = {
            "operation_id": "test_op_123",
            "status": "running"
        }
        mock_status_result = {
            "operation_id": "test_op_123",
            "status": "running",
            "progress": 50.0
        }
        
        mock_scrape_tool.return_value = mock_scrape_result
        mock_status_tool.return_value = mock_status_result
        
        # Test scrape_documentation tool
        response = client.post(
            "/mcp/tools",
            json={
                "name": "scrape_documentation",
                "parameters": {
                    "url": "https://example.com/docs/",
                    "mode": "auto"
                }
            }
        )
        
        assert response.status_code == 200
        assert response.json() == mock_scrape_result
        mock_scrape_tool.assert_called_once()
        
        # Test check_operation_status tool
        response = client.post(
            "/mcp/tools",
            json={
                "name": "check_operation_status",
                "parameters": {
                    "operation_id": "test_op_123"
                }
            }
        )
        
        assert response.status_code == 200
        assert response.json() == mock_status_result
        mock_status_tool.assert_called_once()
        
        # Test unknown tool
        response = client.post(
            "/mcp/tools",
            json={
                "name": "unknown_tool",
                "parameters": {}
            }
        )
        
        assert response.status_code == 200
        assert "error" in response.json()
        assert "Unknown tool" in response.json()["error"]
    
    def test_manifest_endpoint(self, client):
        """Test that the manifest endpoint returns a valid MCP manifest."""
        response = client.get("/mcp/manifest")
        
        assert response.status_code == 200
        manifest = response.json()
        
        # Check manifest structure
        assert "name" in manifest
        assert "description" in manifest
        assert "tools" in manifest
        
        # Check tools
        tools = manifest["tools"]
        assert len(tools) == 2
        
        # Check scrape tool
        scrape_tool = [t for t in tools if t["name"] == "scrape_documentation"][0]
        assert "parameters" in scrape_tool
        assert "url" in scrape_tool["parameters"]
        assert "returns" in scrape_tool
        
        # Check status tool
        status_tool = [t for t in tools if t["name"] == "check_operation_status"][0]
        assert "parameters" in status_tool
        assert "operation_id" in status_tool["parameters"]
        assert "returns" in status_tool
