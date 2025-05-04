"""
Pydantic schemas for MCP server request models.

This module defines the request models used by the MCP server for the Documentation Scraper.
These models validate incoming requests and provide proper type hints.
"""

import re
from typing import Dict, List, Optional, Union, Any, Literal
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, validator, root_validator, constr


class ScrapingMode(str, Enum):
    """Enum of supported scraping modes."""
    GENERIC = "generic"
    DEEPWIKI = "deepwiki"
    AUTO = "auto"


class FilterType(str, Enum):
    """Enum of supported filter types."""
    INCLUDE = "include"
    EXCLUDE = "exclude"
    PRIORITY = "priority"


class ExtractDocumentRequest(BaseModel):
    """
    Request model for document extraction.
    
    This model validates requests for the extract_document MCP tool.
    """
    url: HttpUrl = Field(
        ..., 
        description="URL of the documentation site to extract"
    )
    mode: ScrapingMode = Field(
        default=ScrapingMode.AUTO,
        description="Scraping mode to use (generic, deepwiki, or auto for automatic detection)"
    )
    parallel: bool = Field(
        default=True,
        description="Whether to use parallel scraping for better performance"
    )
    max_depth: Optional[int] = Field(
        default=5,
        description="Maximum depth of links to follow from the starting URL"
    )
    concurrency: Optional[int] = Field(
        default=3,
        description="Number of concurrent workers for parallel scraping"
    )
    use_ai: bool = Field(
        default=True,
        description="Whether to use AI for content processing and link filtering"
    )
    filters: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="Optional filters to apply during scraping with URL patterns"
    )
    
    @root_validator(skip_on_failure=True)
    def validate_extraction_params(cls, values):
        """Validate the extraction parameters as a whole."""
        # Check if parallel mode is enabled but concurrency is set to 1
        if values.get("parallel") and values.get("concurrency") == 1:
            values["concurrency"] = 3  # Set a more reasonable default
        
        # If not using parallel mode, ensure concurrency is set to 1
        if not values.get("parallel") and values.get("concurrency", 0) > 1:
            values["concurrency"] = 1
            
        # Validate filters if provided
        if values.get("filters"):
            valid_keys = [f.value for f in FilterType]
            for key in values["filters"].keys():
                if key not in valid_keys:
                    raise ValueError(f"Invalid filter type: {key}. Must be one of: {', '.join(valid_keys)}")
                    
        return values
    
    @validator("max_depth")
    def validate_max_depth(cls, v):
        """Validate max_depth is a reasonable value."""
        if v is not None and (v < 1 or v > 10):
            raise ValueError("max_depth must be between 1 and 10")
        
        # Provide a warning for deep crawls that might take a long time
        if v is not None and v > 5:
            import logging
            logging.warning(f"Deep crawl requested with max_depth={v}. This may take a long time.")
            
        return v
    
    @validator("concurrency")
    def validate_concurrency(cls, v):
        """Validate concurrency is a reasonable value."""
        if v is not None and (v < 1 or v > 10):
            raise ValueError("concurrency must be between 1 and 10")
        return v


class ContentType(str, Enum):
    """Enum of supported content types."""
    DOCUMENTATION = "documentation"
    TUTORIAL = "tutorial"
    REFERENCE = "reference"
    API = "api"
    GUIDE = "guide"
    FAQ = "faq"


class ProcessingMode(str, Enum):
    """Enum of supported processing modes."""
    CLEAN = "clean"
    SUMMARIZE = "summarize"
    RESTRUCTURE = "restructure"
    EXTRACT_CODE = "extract_code"
    FORMAT = "format"


class ProcessContentRequest(BaseModel):
    """
    Request model for content processing with AI.
    
    This model validates requests for the process_content MCP tool.
    """
    content: str = Field(
        ...,
        description="Raw content to process"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional context to help AI understand the content better"
    )
    content_type: ContentType = Field(
        default=ContentType.DOCUMENTATION,
        description="Type of content being processed"
    )
    processing_mode: ProcessingMode = Field(
        default=ProcessingMode.CLEAN,
        description="Processing mode for AI processing"
    )
    
    @validator("content")
    def validate_content_length(cls, v):
        """Validate content is not too long or empty."""
        if len(v) < 1:
            raise ValueError("content cannot be empty")
        if len(v) > 100000:  # 100KB limit
            raise ValueError("content is too large (max 100KB)")
            
        # Check if content looks like HTML, text, or other format
        if v.lstrip().startswith("<") and "</" in v:
            # HTML content detected
            if "<html" not in v.lower() and "<body" not in v.lower():
                import logging
                logging.warning("Content appears to be HTML fragment rather than complete HTML document")
        elif len(v.splitlines()) < 2 and len(v) > 500:
            import logging
            logging.warning("Content appears to be a single long line, which may affect processing quality")
            
        return v


class ExportFormat(str, Enum):
    """Enum of supported export formats."""
    JSON = "json"
    MARKDOWN = "markdown"
    BOTH = "both"


class ExportContentRequest(BaseModel):
    """
    Request model for content exporting.
    
    This model validates requests for the export_content MCP tool.
    """
    operation_id: Optional[constr(min_length=3, max_length=64, regex=r'^[a-zA-Z0-9_-]+$')] = Field(
        default=None,
        description="ID of an existing extraction operation to export results from"
    )
    content_map: Optional[Dict[str, str]] = Field(
        default=None,
        description="Map of URLs to content to export directly"
    )
    format: ExportFormat = Field(
        default=ExportFormat.JSON,
        description="Output format for the exported content"
    )
    project_name: Optional[constr(min_length=1, max_length=100, strip_whitespace=True)] = Field(
        default=None,
        description="Name to use for the project in the exported files"
    )
    include_metadata: bool = Field(
        default=True,
        description="Whether to include metadata in the exported files"
    )
    
    # This validator is no longer needed since we're using an Enum
    
    @root_validator(skip_on_failure=True)
    def validate_content_source(cls, values):
        """Validate that either content_map or operation_id is provided."""
        if (
            "content_map" in values and values["content_map"] is None and 
            "operation_id" in values and values["operation_id"] is None
        ):
            raise ValueError("Either content_map or operation_id must be provided")
        
        # If content_map is provided, validate URL keys
        if values.get("content_map"):
            for url in values["content_map"].keys():
                if not url.startswith("http"):
                    raise ValueError(f"Invalid URL in content_map: {url}")
                    
        return values


class StatusCheckRequest(BaseModel):
    """
    Request model for operation status checking.
    
    This model validates requests for the check_status MCP tool.
    """
    operation_id: constr(min_length=3, max_length=64, regex=r'^[a-zA-Z0-9_-]+$') = Field(
        ...,
        description="ID of the operation to check status for"
    )
    include_details: bool = Field(
        default=False,
        description="Whether to include detailed status information"
    )
    
    @validator("operation_id")
    def validate_operation_id_format(cls, v):
        """Validate that the operation ID has a valid prefix."""
        valid_prefixes = ["ex_", "proc_", "exp_"]
        
        # Check if operation ID has a valid prefix
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(f"Operation ID must start with one of: {', '.join(valid_prefixes)}")
            
        return v
