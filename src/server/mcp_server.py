"""
MCP Server Implementation for Documentation Scraper Python

This module implements a Model Context Protocol (MCP) server for the Documentation Scraper,
allowing AI agents to interact with the scraping capabilities through a standardized interface.
"""

import os
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from pydantic import BaseModel, Field, root_validator
from enum import Enum

from src.utils.logging import get_logger
from src.controllers.main_controller import MainController
from src.server.middleware.auth import api_key_auth
from src.server.middleware.logging import log_request_middleware
from src.server.schemas.requests import (
    ScrapeRequest,
    OperationStatusRequest
)

# Get logger
logger = get_logger(__name__)

# Define the MCP server app
app = FastAPI(
    title="DocExtract AI MCP Server",
    description="MCP Server for DocExtract AI documentation extraction",
    version="0.1.0"
)

# Add middleware
app.middleware("http")(log_request_middleware)

# Initialize controller
controller = MainController()

class ToolSchema(BaseModel):
    """Base schema for MCP tools"""
    pass


class ScrapeToolSchema(ToolSchema):
    """Schema for the scrape tool"""
    url: str = Field(..., description="URL of the documentation site to scrape")
    mode: str = Field("auto", description="Scraping mode: auto, generic, deepwiki")
    max_depth: int = Field(5, description="Maximum depth of links to follow")
    parallel: bool = Field(False, description="Whether to use parallel processing")
    concurrency: int = Field(3, description="Number of concurrent workers if parallel")
    use_ai: bool = Field(False, description="Whether to use AI for content processing")
    export_format: str = Field("both", description="Export format: json, markdown, both")
    output_dir: Optional[str] = Field(None, description="Directory to save output files")

    @root_validator
    def validate_fields(cls, values):
        # Validate mode
        mode = values.get("mode")
        if mode not in ["auto", "generic", "deepwiki"]:
            raise ValueError(f"Invalid mode: {mode}. Must be auto, generic, or deepwiki")
            
        # Validate export_format
        export_format = values.get("export_format")
        if export_format not in ["json", "markdown", "both"]:
            raise ValueError(f"Invalid export_format: {export_format}. Must be json, markdown, or both")
            
        # Validate concurrency
        concurrency = values.get("concurrency")
        if concurrency < 1 or concurrency > 10:
            raise ValueError(f"Invalid concurrency: {concurrency}. Must be between 1 and 10")
            
        # Validate max_depth
        max_depth = values.get("max_depth")
        if max_depth < 1 or max_depth > 10:
            raise ValueError(f"Invalid max_depth: {max_depth}. Must be between 1 and 10")
            
        return values


class StatusToolSchema(ToolSchema):
    """Schema for the operation status tool"""
    operation_id: str = Field(..., description="ID of the operation to check status for")


@app.get("/")
async def default_handler():
    """Default handler for the MCP server"""
    return {"message": "DocExtract AI MCP Server"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/mcp/scrape")
async def scrape_tool(request: ScrapeToolSchema, user=Depends(api_key_auth)):
    """MCP endpoint for scraping documentation sites"""
    try:
        logger.info(f"Received scrape request for URL: {request.url}")
        
        # Call the controller to start the scraping process
        result = await controller.async_run(
            url=request.url,
            mode=request.mode,
            output_dir=request.output_dir,
            parallel=request.parallel,
            concurrency=request.concurrency,
            max_depth=request.max_depth,
            use_ai=request.use_ai,
            export_format=request.export_format
        )
        
        logger.info(f"Scrape operation started with ID: {result['operation_id']}")
        
        return {
            "operation_id": result["operation_id"],
            "status": result["status"],
            "message": result["message"]
        }
        
    except Exception as e:
        logger.error(f"Error in scrape_tool: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/operation_status")
async def status_tool(request: StatusToolSchema, user=Depends(api_key_auth)):
    """MCP endpoint for checking operation status"""
    try:
        logger.info(f"Received status request for operation: {request.operation_id}")
        
        # Get operation status from controller
        try:
            status = controller.get_operation_status(request.operation_id)
            return status
        except KeyError as e:
            raise HTTPException(status_code=404, detail=f"Operation not found: {request.operation_id}")
        
    except Exception as e:
        logger.error(f"Error in status_tool: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/tools")
async def mcp_tools_handler(request: Request):
    """MCP tools handler"""
    try:
        # Parse request body
        body = await request.json()
        
        # Extract tool name and parameters
        tool_name = body.get("name")
        parameters = body.get("parameters", {})
        
        logger.info(f"Received MCP tool request: {tool_name}")
        
        # Route to appropriate tool handler
        if tool_name == "scrape_documentation":
            # Convert parameters to ScrapeToolSchema
            scrape_params = ScrapeToolSchema(**parameters)
            return await scrape_tool(scrape_params)
            
        elif tool_name == "check_operation_status":
            # Convert parameters to StatusToolSchema
            status_params = StatusToolSchema(**parameters)
            return await status_tool(status_params)
            
        else:
            return {"error": f"Unknown tool: {tool_name}"}
            
    except Exception as e:
        logger.error(f"Error in MCP tools handler: {str(e)}", exc_info=True)
        return {"error": str(e)}


@app.get("/mcp/manifest")
async def mcp_manifest():
    """Return the MCP server manifest"""
    return {
        "name": "DocExtract AI",
        "description": "Documentation extraction and processing tool",
        "tools": [
            {
                "name": "scrape_documentation",
                "description": "Scrape and extract documentation from a website",
                "parameters": {
                    "url": {
                        "type": "string",
                        "description": "URL of the documentation site to scrape"
                    },
                    "mode": {
                        "type": "string",
                        "description": "Scraping mode: auto, generic, deepwiki",
                        "default": "auto"
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth of links to follow",
                        "default": 5
                    },
                    "parallel": {
                        "type": "boolean",
                        "description": "Whether to use parallel processing",
                        "default": False
                    },
                    "concurrency": {
                        "type": "integer",
                        "description": "Number of concurrent workers if parallel",
                        "default": 3
                    },
                    "use_ai": {
                        "type": "boolean",
                        "description": "Whether to use AI for content processing",
                        "default": False
                    },
                    "export_format": {
                        "type": "string",
                        "description": "Export format: json, markdown, both",
                        "default": "both"
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Directory to save output files",
                        "required": False
                    }
                },
                "returns": {
                    "operation_id": {
                        "type": "string",
                        "description": "ID of the operation for status tracking"
                    },
                    "status": {
                        "type": "string",
                        "description": "Status of the operation (running, completed, failed)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Human-readable status message"
                    }
                }
            },
            {
                "name": "check_operation_status",
                "description": "Check the status of a running operation",
                "parameters": {
                    "operation_id": {
                        "type": "string",
                        "description": "ID of the operation to check status for"
                    }
                },
                "returns": {
                    "status": {
                        "type": "string",
                        "description": "Status of the operation (running, completed, failed)"
                    },
                    "progress": {
                        "type": "number",
                        "description": "Progress percentage (0-100)"
                    },
                    "urls_discovered": {
                        "type": "integer",
                        "description": "Number of URLs discovered"
                    },
                    "urls_processed": {
                        "type": "integer",
                        "description": "Number of URLs processed"
                    },
                    "message": {
                        "type": "string",
                        "description": "Human-readable status message"
                    }
                }
            }
        ]
    }


def main():
    """Entry point for the MCP server."""
    # Read configuration from environment variables
    host = os.environ.get("MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("MCP_PORT", "8000"))
    
    # Start the server
    import uvicorn
    uvicorn.run(
        app,
        host=host,
        port=port
    )


if __name__ == "__main__":
    main()
