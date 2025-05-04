"""
Pydantic schemas for MCP server response models.

This module defines the response models used by the MCP server for the Documentation Scraper.
These models ensure consistent and well-structured responses.
"""

from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl


class OperationStatus(str, Enum):
    """Enum of possible operation statuses."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class ExtractDocumentResponse(BaseModel):
    """
    Response model for document extraction.
    
    This model structures responses for the extract_document MCP tool.
    """
    operation_id: str = Field(
        ...,
        description="Unique identifier for the extraction operation"
    )
    status: OperationStatus = Field(
        ...,
        description="Current status of the extraction operation"
    )
    started_at: datetime = Field(
        ...,
        description="Timestamp when the operation started"
    )
    estimated_completion: Optional[datetime] = Field(
        default=None,
        description="Estimated completion time (if available)"
    )
    progress: Optional[float] = Field(
        default=None,
        description="Progress as a percentage (0-100)"
    )
    urls_discovered: Optional[int] = Field(
        default=None,
        description="Number of URLs discovered so far"
    )
    urls_processed: Optional[int] = Field(
        default=None,
        description="Number of URLs processed so far"
    )
    message: Optional[str] = Field(
        default=None,
        description="Optional status message or error"
    )
    result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Results if operation completed immediately"
    )


class ProcessContentResponse(BaseModel):
    """
    Response model for content processing with AI.
    
    This model structures responses for the process_content MCP tool.
    """
    processed_content: str = Field(
        ...,
        description="The processed content after AI cleaning/processing"
    )
    original_length: int = Field(
        ...,
        description="Character length of the original content"
    )
    processed_length: int = Field(
        ...,
        description="Character length of the processed content"
    )
    processing_time: float = Field(
        ...,
        description="Time taken to process the content in seconds"
    )
    changes_made: Optional[List[str]] = Field(
        default=None,
        description="List of significant changes made during processing"
    )
    message: Optional[str] = Field(
        default=None,
        description="Optional message about the processing"
    )


class ExportDetails(BaseModel):
    """Details about an exported file."""
    file_path: str = Field(
        ...,
        description="Path to the exported file"
    )
    file_size: int = Field(
        ...,
        description="Size of the file in bytes"
    )
    page_count: int = Field(
        ...,
        description="Number of pages included in the export"
    )
    format: str = Field(
        ...,
        description="Format of the export (json, markdown)"
    )


class ExportContentResponse(BaseModel):
    """
    Response model for content exporting.
    
    This model structures responses for the export_content MCP tool.
    """
    operation_id: str = Field(
        ...,
        description="Unique identifier for the export operation"
    )
    status: OperationStatus = Field(
        ...,
        description="Status of the export operation"
    )
    exports: Optional[List[ExportDetails]] = Field(
        default=None,
        description="Details about exported files"
    )
    message: Optional[str] = Field(
        default=None,
        description="Optional message about the export"
    )


class StatusCheckResponse(BaseModel):
    """
    Response model for operation status checking.
    
    This model structures responses for the check_status MCP tool.
    """
    operation_id: str = Field(
        ...,
        description="ID of the operation being checked"
    )
    operation_type: str = Field(
        ...,
        description="Type of operation (extraction, export, etc.)"
    )
    status: OperationStatus = Field(
        ...,
        description="Current status of the operation"
    )
    started_at: datetime = Field(
        ...,
        description="When the operation started"
    )
    updated_at: datetime = Field(
        ...,
        description="When the operation status was last updated"
    )
    progress: Optional[float] = Field(
        default=None,
        description="Progress as a percentage (0-100)"
    )
    message: Optional[str] = Field(
        default=None,
        description="Optional status message or error"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detailed status information (if requested)"
    )
