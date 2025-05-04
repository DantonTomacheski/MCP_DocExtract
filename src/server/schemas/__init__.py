"""
MCP Server Schemas Package

This package contains all the Pydantic models and schemas used by the MCP server
for the Documentation Scraper Python project.
"""

# Export request models
from src.server.schemas.requests import (
    ExtractDocumentRequest,
    ProcessContentRequest,
    ExportContentRequest,
    StatusCheckRequest,
    ScrapingMode
)

# Export response models
from src.server.schemas.responses import (
    ExtractDocumentResponse,
    ProcessContentResponse,
    ExportContentResponse,
    StatusCheckResponse,
    OperationStatus,
    ExportDetails
)

# Export MCP protocol models
from src.server.schemas.mcp import (
    MCPToolReference,
    MCPToolsResponse,
    MCPInvokeRequest,
    MCPInvokeResponse,
    MCPError,
    tool_schema_to_reference
)

# Export tool schemas
from src.server.schemas.tools import (
    mcp_tools,
    mcp_toolset,
    extract_document_tool,
    process_content_tool,
    export_content_tool,
    check_status_tool,
    detect_framework_tool
)

# Export interface helpers
from src.server.schemas.interface import (
    MCPToolRegistry,
    mcp_registry
)