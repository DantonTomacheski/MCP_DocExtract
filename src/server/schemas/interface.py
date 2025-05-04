"""
MCP Interface Schemas for Documentation Scraper Python

This module provides interface definitions and helpers to integrate
all the MCP schemas into a cohesive API for the server implementation.
"""

from typing import Dict, List, Any, Optional, Union
import json

from pydantic import BaseModel, ValidationError

from src.server.schemas.tools import (
    mcp_tools,
    mcp_toolset,
    extract_document_tool,
    process_content_tool,
    export_content_tool,
    check_status_tool,
    detect_framework_tool
)
from src.server.schemas.mcp import (
    MCPToolReference,
    MCPToolsResponse,
    MCPInvokeRequest,
    MCPInvokeResponse,
    MCPError,
    tool_schema_to_reference
)
from src.server.schemas.requests import (
    ExtractDocumentRequest,
    ProcessContentRequest,
    ExportContentRequest,
    StatusCheckRequest,
    ScrapingMode
)
from src.server.schemas.responses import (
    ExtractDocumentResponse,
    ProcessContentResponse,
    ExportContentResponse,
    StatusCheckResponse,
    OperationStatus
)


class MCPToolRegistry:
    """
    Registry for MCP tools.
    
    This class provides a central registry for all MCP tools and
    methods to validate and process MCP requests.
    """
    
    def __init__(self):
        """Initialize the MCP tool registry with all available tools."""
        self.tools = {tool.name: tool for tool in mcp_tools}
        
    def get_tools_response(self) -> MCPToolsResponse:
        """
        Get the MCP tools response.
        
        Returns:
            MCPToolsResponse containing all available tools
        """
        tool_references = [
            tool_schema_to_reference(tool.dict())
            for tool in mcp_tools
        ]
        return MCPToolsResponse(tools=tool_references)
    
    def validate_request(self, request: MCPInvokeRequest) -> Optional[str]:
        """
        Validate an MCP invoke request.
        
        Args:
            request: The MCP invoke request to validate
            
        Returns:
            Error message if validation fails, None otherwise
        """
        if request.name not in self.tools:
            return f"Unknown tool: {request.name}"
        
        # Get the tool schema
        tool = self.tools[request.name]
        
        # Validate parameters against the tool's parameter schema
        try:
            # Different validation depending on the tool
            if request.name == "extract_document":
                ExtractDocumentRequest(**request.parameters)
            elif request.name == "process_content":
                ProcessContentRequest(**request.parameters)
            elif request.name == "export_content":
                ExportContentRequest(**request.parameters)
            elif request.name == "check_status":
                StatusCheckRequest(**request.parameters)
            elif request.name == "detect_framework":
                # Simple validation for now
                if "url" not in request.parameters:
                    return "Missing required parameter: url"
            else:
                return f"No validation handler for tool: {request.name}"
                
            return None
        except ValidationError as e:
            return f"Parameter validation error: {str(e)}"
    
    def format_response(self, tool_name: str, result: Dict[str, Any]) -> MCPInvokeResponse:
        """
        Format a tool result as an MCP invoke response.
        
        Args:
            tool_name: Name of the tool that was invoked
            result: Result of the tool invocation
            
        Returns:
            MCPInvokeResponse containing the result
        """
        return MCPInvokeResponse(
            tool_name=tool_name,
            result=result
        )
    
    def format_error(self, error: str, details: Optional[Dict[str, Any]] = None) -> MCPError:
        """
        Format an error as an MCP error response.
        
        Args:
            error: Error message
            details: Additional error details
            
        Returns:
            MCPError containing the error information
        """
        return MCPError(
            error=error,
            details=details
        )


# Singleton instance for global use
mcp_registry = MCPToolRegistry()
