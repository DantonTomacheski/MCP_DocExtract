"""
Unit tests for the MCP server implementation.

These tests verify that the MCP server routes and handlers work correctly.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.server.mcp_server import MCPServer
from src.server.schemas.mcp import MCPInvokeRequest


class TestMCPServer:
    """Tests for the MCPServer class."""
    
    @pytest.fixture
    def server(self):
        """Create a test instance of the MCPServer."""
        return MCPServer(host="127.0.0.1", port=8000)
    
    @pytest.fixture
    def client(self, server):
        """Create a TestClient for the MCPServer."""
        return TestClient(server.app)
    
    def test_server_initialization(self, server):
        """Test that the server is initialized correctly."""
        assert server.host == "127.0.0.1"
        assert server.port == 8000
        assert server.app is not None
        assert server.controller is not None
        assert server.active_operations == {}
    
    def test_mcp_endpoint_invalid_request(self, client):
        """Test that the MCP endpoint rejects invalid requests."""
        # Empty request
        response = client.post("/api/mcp", json={})
        assert response.status_code == 400
        
        # Missing parameters
        response = client.post("/api/mcp", json={"name": "extract_document"})
        assert response.status_code == 400
        
        # Invalid tool name
        response = client.post(
            "/api/mcp", 
            json={"name": "invalid_tool", "parameters": {}}
        )
        assert response.status_code == 400
        assert "Unknown tool" in response.json()["error"]
    
    @patch("src.server.mcp_server.MCPServer._handle_extract_document")
    def test_mcp_endpoint_extract_document(self, mock_handler, client):
        """Test that extract_document requests are routed correctly."""
        # Mock the handler to return a simple response
        mock_handler.return_value = {"status": "ok"}
        
        response = client.post(
            "/api/mcp", 
            json={
                "name": "extract_document", 
                "parameters": {"url": "https://example.com"}
            }
        )
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_handler.assert_called_once_with({"url": "https://example.com"})
    
    @patch("src.server.mcp_server.MCPServer._handle_process_content")
    def test_mcp_endpoint_process_content(self, mock_handler, client):
        """Test that process_content requests are routed correctly."""
        # Mock the handler to return a simple response
        mock_handler.return_value = {"status": "ok"}
        
        response = client.post(
            "/api/mcp", 
            json={
                "name": "process_content", 
                "parameters": {"content": "Test content"}
            }
        )
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_handler.assert_called_once_with({"content": "Test content"})
    
    @patch("src.server.mcp_server.MCPServer._handle_export_content")
    def test_mcp_endpoint_export_content(self, mock_handler, client):
        """Test that export_content requests are routed correctly."""
        # Mock the handler to return a simple response
        mock_handler.return_value = {"status": "ok"}
        
        response = client.post(
            "/api/mcp", 
            json={
                "name": "export_content", 
                "parameters": {"operation_id": "abc123"}
            }
        )
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_handler.assert_called_once_with({"operation_id": "abc123"})
    
    @patch("src.server.mcp_server.MCPServer._handle_check_status")
    def test_mcp_endpoint_check_status(self, mock_handler, client):
        """Test that check_status requests are routed correctly."""
        # Mock the handler to return a simple response
        mock_handler.return_value = {"status": "ok"}
        
        response = client.post(
            "/api/mcp", 
            json={
                "name": "check_status", 
                "parameters": {"operation_id": "abc123"}
            }
        )
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_handler.assert_called_once_with({"operation_id": "abc123"})
    
    def test_mcp_endpoint_exception_handling(self, client):
        """Test that exceptions in the MCP endpoint are handled correctly."""
        # Use a patch to force an exception in the request handling
        with patch("src.server.mcp_server.MCPServer._handle_extract_document", 
                 side_effect=Exception("Test exception")):
            
            response = client.post(
                "/api/mcp", 
                json={
                    "name": "extract_document", 
                    "parameters": {"url": "https://example.com"}
                }
            )
            
            assert response.status_code == 500
            assert "error" in response.json()
            assert "Test exception" in response.json()["error"]
    
    def test_security_headers_middleware(self, client):
        """Test that security headers are added to responses."""
        response = client.get("/")  # Any route will do
        
        # Check security headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "Content-Security-Policy" in response.headers


class TestMCPServerHandlers:
    """Tests for the MCPServer handler methods."""
    
    @pytest.fixture
    def server(self):
        """Create a test instance of the MCPServer."""
        server = MCPServer()
        # Mock the controller for testing
        server.controller = MagicMock()
        return server
    
    @pytest.mark.asyncio
    async def test_handle_extract_document(self, server):
        """Test the extract_document handler."""
        # For now, we're just checking the placeholder implementation
        response = await server._handle_extract_document({"url": "https://example.com"})
        assert response.status_code == 200
        assert "status" in response.body.decode()
        assert "Not implemented yet" in response.body.decode()
    
    @pytest.mark.asyncio
    async def test_handle_process_content(self, server):
        """Test the process_content handler."""
        # For now, we're just checking the placeholder implementation
        response = await server._handle_process_content({"content": "Test content"})
        assert response.status_code == 200
        assert "status" in response.body.decode()
        assert "Not implemented yet" in response.body.decode()
    
    @pytest.mark.asyncio
    async def test_handle_export_content(self, server):
        """Test the export_content handler."""
        # For now, we're just checking the placeholder implementation
        response = await server._handle_export_content({"operation_id": "abc123"})
        assert response.status_code == 200
        assert "status" in response.body.decode()
        assert "Not implemented yet" in response.body.decode()
    
    @pytest.mark.asyncio
    async def test_handle_check_status(self, server):
        """Test the check_status handler."""
        # For now, we're just checking the placeholder implementation
        response = await server._handle_check_status({"operation_id": "abc123"})
        assert response.status_code == 200
        assert "status" in response.body.decode()
        assert "Not implemented yet" in response.body.decode()
    
    def test_start_method(self, server):
        """Test the start method (without actually starting the server)."""
        with patch("uvicorn.run") as mock_run:
            server.start()
            mock_run.assert_called_once_with(
                server.app,
                host=server.host,
                port=server.port
            )
