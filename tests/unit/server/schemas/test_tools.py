"""
Unit tests for MCP tool schema models.

These tests verify that the tool schema models work correctly,
including tool definitions, validation, and the overall toolset.
"""

import pytest
from pydantic import ValidationError
from typing import Dict, List, Any

from src.server.schemas.tools import (
    MCPTool,
    MCPToolSet,
    mcp_tools,
    mcp_toolset,
    extract_document_tool,
    process_content_tool,
    export_content_tool,
    check_status_tool,
    detect_framework_tool
)


class TestMCPTool:
    """Tests for the MCPTool model."""
    
    def test_valid_tool(self):
        """Test that a valid tool can be created."""
        tool = MCPTool(
            name="test_tool",
            description="A test tool for testing",
            parameters={
                "param1": {
                    "type": "string",
                    "description": "A test parameter"
                }
            },
            returns={
                "result": {
                    "type": "string",
                    "description": "The test result"
                }
            }
        )
        
        assert tool.name == "test_tool"
        assert tool.description == "A test tool for testing"
        assert "param1" in tool.parameters
        assert "result" in tool.returns
        
    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        # Missing name
        with pytest.raises(ValidationError):
            MCPTool(
                description="A test tool",
                parameters={},
                returns={}
            )
            
        # Missing description
        with pytest.raises(ValidationError):
            MCPTool(
                name="test_tool",
                parameters={},
                returns={}
            )
            
        # Missing parameters
        with pytest.raises(ValidationError):
            MCPTool(
                name="test_tool",
                description="A test tool",
                returns={}
            )
            
        # Missing returns
        with pytest.raises(ValidationError):
            MCPTool(
                name="test_tool",
                description="A test tool",
                parameters={}
            )


class TestMCPToolSet:
    """Tests for the MCPToolSet model."""
    
    def test_valid_toolset(self):
        """Test that a valid toolset can be created."""
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            parameters={},
            returns={}
        )
        
        toolset = MCPToolSet(
            version="1.0",
            tools=[tool]
        )
        
        assert toolset.version == "1.0"
        assert len(toolset.tools) == 1
        assert toolset.tools[0].name == "test_tool"
        
    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            parameters={},
            returns={}
        )
        
        # Missing version
        with pytest.raises(ValidationError):
            MCPToolSet(tools=[tool])
            
        # Missing tools
        with pytest.raises(ValidationError):
            MCPToolSet(version="1.0")
        
        # Empty tools list
        with pytest.raises(ValidationError):
            MCPToolSet(version="1.0", tools=[])


class TestPredefinedTools:
    """Tests for the predefined tool schemas."""
    
    def test_extract_document_tool(self):
        """Test the extract_document tool schema."""
        tool = extract_document_tool
        
        assert tool.name == "extract_document"
        assert "url" in tool.parameters
        assert tool.parameters["url"]["required"] is True
        assert "mode" in tool.parameters
        assert "parallel" in tool.parameters
        assert "max_depth" in tool.parameters
        assert "concurrency" in tool.parameters
        assert "use_ai" in tool.parameters
        assert "filters" in tool.parameters
        
        # Verify return schema
        assert "operation_id" in tool.returns
        assert "status" in tool.returns
        assert "message" in tool.returns
        
    def test_process_content_tool(self):
        """Test the process_content tool schema."""
        tool = process_content_tool
        
        assert tool.name == "process_content"
        assert "content" in tool.parameters
        assert "context" in tool.parameters
        assert "content_type" in tool.parameters
        assert "processing_mode" in tool.parameters
        
    def test_export_content_tool(self):
        """Test the export_content tool schema."""
        tool = export_content_tool
        
        assert tool.name == "export_content"
        assert "operation_id" in tool.parameters
        assert "content_map" in tool.parameters
        assert "format" in tool.parameters
        assert "project_name" in tool.parameters
        assert "include_metadata" in tool.parameters
        
        # Verify return schema
        assert "operation_id" in tool.returns
        assert "status" in tool.returns
        assert "exports" in tool.returns
        
    def test_check_status_tool(self):
        """Test the check_status tool schema."""
        tool = check_status_tool
        
        assert tool.name == "check_status"
        assert "operation_id" in tool.parameters
        assert tool.parameters["operation_id"]["required"] is True
        assert "include_details" in tool.parameters
        
        # Verify return schema
        assert "operation_id" in tool.returns
        assert "operation_type" in tool.returns
        assert "status" in tool.returns
        assert "progress" in tool.returns
        assert "message" in tool.returns
        assert "details" in tool.returns
        
    def test_detect_framework_tool(self):
        """Test the detect_framework tool schema."""
        tool = detect_framework_tool
        
        assert tool.name == "detect_framework"
        assert "url" in tool.parameters
        assert tool.parameters["url"]["required"] is True
        
        # Verify return schema
        assert "framework" in tool.returns
        assert "confidence" in tool.returns
        assert "indicators" in tool.returns
        
    def test_mcp_tools_list(self):
        """Test the list of all MCP tools."""
        # Verify that all expected tools are in the list
        tool_names = [tool.name for tool in mcp_tools]
        
        assert "extract_document" in tool_names
        assert "process_content" in tool_names
        assert "export_content" in tool_names
        assert "check_status" in tool_names
        assert "detect_framework" in tool_names
        assert len(tool_names) == 5  # Make sure there are exactly 5 tools
        
    def test_mcp_toolset(self):
        """Test the MCP toolset definition."""
        assert mcp_toolset.version == "1.0"
        assert len(mcp_toolset.tools) == 5
        
        # Verify that all tools in the toolset match those in the list
        toolset_names = [tool.name for tool in mcp_toolset.tools]
        list_names = [tool.name for tool in mcp_tools]
        
        assert set(toolset_names) == set(list_names)
