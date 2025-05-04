"""
MCP Tool Schemas for Documentation Scraper Python

This module defines the tool schemas that will be exposed to AI agents
via the MCP protocol. These schemas define the structure and documentation
for each tool that the MCP server will provide.
"""

import re
from typing import Dict, List, Optional, Any, Union, Callable
from urllib.parse import urlparse
from pydantic import BaseModel, Field, root_validator, validator, ValidationError


class MCPTool(BaseModel):
    """Base model for an MCP tool schema definition."""
    name: str = Field(..., description="Name of the tool")
    description: str = Field(..., description="Detailed description of what the tool does")
    parameters: Dict[str, Any] = Field(..., description="Parameters the tool accepts")
    returns: Dict[str, Any] = Field(..., description="Schema for what the tool returns")
    
    @validator('name')
    def validate_name(cls, v: str) -> str:
        """Validate that the tool name follows proper format."""
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError(f"Tool name '{v}' must be snake_case and start with a letter")
        return v
    
    @validator('description')
    def validate_description(cls, v: str) -> str:
        """Validate that the description is substantial."""
        if len(v.strip()) < 10:
            raise ValueError("Tool description must be at least 10 characters long")
        return v.strip()
    
    @validator('parameters', 'returns')
    def validate_schema_objects(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that schema objects contain required format."""
        if not v:
            raise ValueError("Schema object cannot be empty")
        return v


class MCPToolSet(BaseModel):
    """A set of MCP tools with metadata."""
    version: str = Field(..., description="MCP tool schema version")
    tools: List[MCPTool] = Field(..., min_items=1, description="List of available tools")
    
    @validator('version')
    def validate_version(cls, v: str) -> str:
        """Validate that the version follows semantic versioning format."""
        if not re.match(r'^\d+\.\d+(\.\d+)?$', v):
            raise ValueError(f"Version '{v}' must follow semantic versioning format (e.g., '1.0' or '1.0.1')")
        return v
    
    @root_validator
    def validate_tool_uniqueness(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that all tools have unique names."""
        if 'tools' in values and values['tools']:
            tool_names = [tool.name for tool in values['tools']]
            duplicate_names = set([name for name in tool_names if tool_names.count(name) > 1])
            if duplicate_names:
                raise ValueError(f"Duplicate tool names found: {duplicate_names}")
        return values


# Extract Document Tool
extract_document_tool = MCPTool(
    name="extract_document",
    description="""
    Extract documentation content from a website.
    
    This tool navigates through a documentation website, starting from the provided URL,
    and extracts structured content from all relevant pages. It uses a breadth-first search
    algorithm to discover and process pages, and can optionally use AI to improve the
    quality of the extracted content.
    
    The operation is asynchronous and returns an operation ID that can be used to check
    status and retrieve results when complete.
    """,
    parameters={
        "url": {
            "type": "string",
            "description": "URL of the documentation site to extract",
            "format": "uri",
            "pattern": "^https?://[^\s/$.?#].[^\s]*$",
            "required": True
        },
        "mode": {
            "type": "string",
            "description": "Scraping mode to use",
            "enum": ["generic", "deepwiki", "auto"],
            "default": "auto"
        },
        "parallel": {
            "type": "boolean",
            "description": "Whether to use parallel scraping for better performance",
            "default": True
        },
        "max_depth": {
            "type": "integer",
            "description": "Maximum depth of links to follow from the starting URL",
            "default": 5,
            "minimum": 1,
            "maximum": 10
        },
        "concurrency": {
            "type": "integer",
            "description": "Number of concurrent workers for parallel scraping",
            "default": 3,
            "minimum": 1,
            "maximum": 10
        },
        "use_ai": {
            "type": "boolean",
            "description": "Whether to use AI for content processing and link filtering",
            "default": True
        },
        "filters": {
            "type": "object",
            "description": "Optional filters to apply during scraping (URL patterns, etc.)",
            "required": False
        }
    },
    returns={
        "operation_id": {
            "type": "string",
            "description": "Unique identifier for the extraction operation"
        },
        "status": {
            "type": "string",
            "description": "Current status of the extraction operation",
            "enum": ["pending", "running", "completed", "failed", "canceled"]
        },
        "message": {
            "type": "string",
            "description": "Optional status message or error"
        }
    }
)


# Process Content Tool
process_content_tool = MCPTool(
    name="process_content",
    description="""
    Process raw documentation content with AI assistance.
    
    This tool uses advanced AI models to clean, structure, and improve documentation content.
    It can remove irrelevant elements, improve formatting, and ensure content is well-structured
    while preserving the technical accuracy of the original content.
    
    This operation is synchronous and returns the processed content immediately.
    """,
    parameters={
        "content": {
            "type": "string",
            "description": "Raw content to process",
            "required": True
        },
        "context": {
            "type": "string",
            "description": "Optional context to help AI understand the content better",
            "required": False
        },
        "content_type": {
            "type": "string",
            "description": "Type of content being processed",
            "default": "documentation"
        },
        "processing_mode": {
            "type": "string",
            "description": "Processing mode (clean, summarize, restructure)",
            "default": "clean",
            "enum": ["clean", "summarize", "restructure"]
        }
    },
    returns={
        "processed_content": {
            "type": "string",
            "description": "The processed content after AI cleaning/processing"
        },
        "original_length": {
            "type": "integer",
            "description": "Character length of the original content"
        },
        "processed_length": {
            "type": "integer",
            "description": "Character length of the processed content"
        },
        "processing_time": {
            "type": "number",
            "description": "Time taken to process the content in seconds"
        },
        "changes_made": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of significant changes made during processing"
        }
    }
)


# Export Content Tool
export_content_tool = MCPTool(
    name="export_content",
    description="""
    Export extracted documentation content to specified formats.
    
    This tool exports previously extracted documentation content to JSON, Markdown,
    or both formats. It can either export content from a completed extraction operation
    or directly from provided content.
    
    The operation is asynchronous for large exports and returns an operation ID
    that can be used to check status and retrieve results.
    """,
    parameters={
        "operation_id": {
            "type": "string",
            "description": "ID of an existing extraction operation to export results from",
            "required": False
        },
        "content_map": {
            "type": "object",
            "description": "Map of URLs to content to export directly",
            "required": False
        },
        "format": {
            "type": "string",
            "description": "Output format (json, markdown, or both)",
            "default": "json",
            "enum": ["json", "markdown", "both"]
        },
        "project_name": {
            "type": "string",
            "description": "Name to use for the project in the exported files",
            "required": False
        },
        "include_metadata": {
            "type": "boolean",
            "description": "Whether to include metadata in the exported files",
            "default": True
        }
    },
    returns={
        "operation_id": {
            "type": "string",
            "description": "Unique identifier for the export operation"
        },
        "status": {
            "type": "string",
            "description": "Status of the export operation",
            "enum": ["pending", "running", "completed", "failed", "canceled"]
        },
        "exports": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "file_size": {"type": "integer"},
                    "page_count": {"type": "integer"},
                    "format": {"type": "string"}
                }
            },
            "description": "Details about exported files (if immediately available)"
        }
    }
)


# Check Status Tool
check_status_tool = MCPTool(
    name="check_status",
    description="""
    Check the status of a previously initiated operation.
    
    This tool allows checking the current status of an asynchronous operation
    such as document extraction or content export. It provides progress information
    and results if the operation has completed.
    
    This operation is synchronous and returns the current status immediately.
    """,
    parameters={
        "operation_id": {
            "type": "string",
            "description": "ID of the operation to check status for",
            "required": True
        },
        "include_details": {
            "type": "boolean",
            "description": "Whether to include detailed status information",
            "default": False
        }
    },
    returns={
        "operation_id": {
            "type": "string",
            "description": "ID of the operation being checked"
        },
        "operation_type": {
            "type": "string",
            "description": "Type of operation (extraction, export, etc.)"
        },
        "status": {
            "type": "string",
            "description": "Current status of the operation",
            "enum": ["pending", "running", "completed", "failed", "canceled"]
        },
        "progress": {
            "type": "number",
            "description": "Progress as a percentage (0-100)"
        },
        "message": {
            "type": "string",
            "description": "Optional status message or error"
        },
        "details": {
            "type": "object",
            "description": "Detailed status information (if requested)"
        }
    }
)


# Get framework detection tool
detect_framework_tool = MCPTool(
    name="detect_framework",
    description="""
    Detect the documentation framework used by a website.
    
    This tool analyzes a documentation website and attempts to determine
    the framework or platform used (e.g., Docusaurus, MkDocs, Sphinx, etc.).
    This information can be used to select the most appropriate extraction strategy.
    
    This operation is synchronous and returns the detected framework immediately.
    """,
    parameters={
        "url": {
            "type": "string",
            "description": "URL of the website to analyze",
            "format": "uri",
            "pattern": "^https?://[^\s/$.?#].[^\s]*$",
            "required": True
        }
    },
    returns={
        "framework": {
            "type": "string",
            "description": "Detected documentation framework"
        },
        "confidence": {
            "type": "number",
            "description": "Confidence score (0-1) of the detection"
        },
        "indicators": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Indicators that led to the framework detection"
        }
    }
)


# List of all available tools
mcp_tools = [
    extract_document_tool,
    process_content_tool,
    export_content_tool,
    check_status_tool,
    detect_framework_tool
]

# MCP tool set definition
mcp_toolset = MCPToolSet(
    version="1.0",
    tools=mcp_tools
)
