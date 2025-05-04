"""
MCP Protocol Schemas for Documentation Scraper Python

This module defines the Pydantic models for MCP protocol communication.
These models handle the standard MCP request/response format that wraps around
our specific tool implementations.
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, root_validator, validator


class MCPToolReference(BaseModel):
    """Reference to an MCP tool in a tools list response."""
    name: str = Field(..., description="Name of the tool")
    description: str = Field(..., description="Description of what the tool does")
    parameters_schema: Dict[str, Any] = Field(
        ..., 
        description="JSON Schema for the tool parameters"
    )


class MCPToolsResponse(BaseModel):
    """Response model for the MCP tools endpoint."""
    tools: List[MCPToolReference] = Field(
        ..., 
        description="List of available tools"
    )


class MCPInvokeRequest(BaseModel):
    """Request model for the MCP invoke endpoint."""
    name: str = Field(
        ..., 
        description="Name of the tool to invoke"
    )
    parameters: Dict[str, Any] = Field(
        default={},
        description="Parameters to pass to the tool"
    )
    
    @validator("name")
    def validate_tool_name(cls, v):
        """Validate that the tool name is one of the supported tools."""
        valid_tools = [
            "extract_document", 
            "process_content", 
            "export_content", 
            "check_status",
            "detect_framework"
        ]
        if v not in valid_tools:
            raise ValueError(f"Invalid tool name: {v}. Must be one of: {valid_tools}")
        return v


class MCPInvokeResponse(BaseModel):
    """Response model for the MCP invoke endpoint."""
    tool_name: str = Field(
        ..., 
        description="Name of the tool that was invoked"
    )
    result: Dict[str, Any] = Field(
        ..., 
        description="Result of the tool invocation"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if the invocation failed"
    )


class MCPError(BaseModel):
    """Error response model for MCP endpoints."""
    error: str = Field(
        ..., 
        description="Error message"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )


# Helper function to convert tool schemas to MCP tool references
def tool_schema_to_reference(tool_schema: Dict[str, Any]) -> MCPToolReference:
    """
    Convert a tool schema to an MCP tool reference.
    
    Args:
        tool_schema: Tool schema definition
        
    Returns:
        MCPToolReference for the tool
    """
    return MCPToolReference(
        name=tool_schema["name"],
        description=tool_schema["description"],
        parameters_schema={
            "type": "object",
            "properties": tool_schema["parameters"],
            "required": [
                param_name
                for param_name, param_def in tool_schema["parameters"].items()
                if param_def.get("required", False)
            ]
        }
    )
