"""
Unit tests for MCP response schema models.

These tests verify that the response models work correctly,
including validation, defaults, and serialization.
"""

import pytest
from pydantic import ValidationError
from datetime import datetime, timedelta

from src.server.schemas.responses import (
    OperationStatus,
    ExtractDocumentResponse,
    ProcessContentResponse,
    ExportDetails,
    ExportContentResponse,
    StatusCheckResponse
)


class TestOperationStatus:
    """Tests for the OperationStatus enum."""
    
    def test_valid_statuses(self):
        """Test that valid operation statuses can be used."""
        assert OperationStatus.PENDING == "pending"
        assert OperationStatus.RUNNING == "running"
        assert OperationStatus.COMPLETED == "completed"
        assert OperationStatus.FAILED == "failed"
        assert OperationStatus.CANCELED == "canceled"
        
    def test_from_string(self):
        """Test that an OperationStatus can be created from a string."""
        assert OperationStatus("pending") == OperationStatus.PENDING
        assert OperationStatus("running") == OperationStatus.RUNNING
        assert OperationStatus("completed") == OperationStatus.COMPLETED
        assert OperationStatus("failed") == OperationStatus.FAILED
        assert OperationStatus("canceled") == OperationStatus.CANCELED
        
    def test_invalid_status(self):
        """Test that an invalid status raises a ValueError."""
        with pytest.raises(ValueError):
            OperationStatus("invalid_status")


class TestExtractDocumentResponse:
    """Tests for the ExtractDocumentResponse model."""
    
    def test_minimal_valid_response(self):
        """Test that a response with just the required fields is valid."""
        now = datetime.now()
        response = ExtractDocumentResponse(
            operation_id="abc123",
            status=OperationStatus.PENDING,
            started_at=now
        )
        
        assert response.operation_id == "abc123"
        assert response.status == OperationStatus.PENDING
        assert response.started_at == now
        assert response.estimated_completion is None
        assert response.progress is None
        assert response.urls_discovered is None
        assert response.urls_processed is None
        assert response.message is None
        assert response.result is None
        
    def test_full_response(self):
        """Test that a response with all fields is valid."""
        now = datetime.now()
        estimated = now + timedelta(minutes=5)
        
        response = ExtractDocumentResponse(
            operation_id="abc123",
            status=OperationStatus.RUNNING,
            started_at=now,
            estimated_completion=estimated,
            progress=45.5,
            urls_discovered=100,
            urls_processed=45,
            message="Processing in progress",
            result={"sample": "data"}
        )
        
        assert response.operation_id == "abc123"
        assert response.status == OperationStatus.RUNNING
        assert response.started_at == now
        assert response.estimated_completion == estimated
        assert response.progress == 45.5
        assert response.urls_discovered == 100
        assert response.urls_processed == 45
        assert response.message == "Processing in progress"
        assert response.result["sample"] == "data"
        
    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        now = datetime.now()
        
        # Missing operation_id
        with pytest.raises(ValidationError):
            ExtractDocumentResponse(
                status=OperationStatus.PENDING,
                started_at=now
            )
            
        # Missing status
        with pytest.raises(ValidationError):
            ExtractDocumentResponse(
                operation_id="abc123",
                started_at=now
            )
            
        # Missing started_at
        with pytest.raises(ValidationError):
            ExtractDocumentResponse(
                operation_id="abc123",
                status=OperationStatus.PENDING
            )


class TestProcessContentResponse:
    """Tests for the ProcessContentResponse model."""
    
    def test_minimal_valid_response(self):
        """Test that a response with just the required fields is valid."""
        response = ProcessContentResponse(
            processed_content="<p>Cleaned content</p>",
            original_length=100,
            processed_length=80,
            processing_time=1.2
        )
        
        assert response.processed_content == "<p>Cleaned content</p>"
        assert response.original_length == 100
        assert response.processed_length == 80
        assert response.processing_time == 1.2
        assert response.changes_made is None
        assert response.message is None
        
    def test_full_response(self):
        """Test that a response with all fields is valid."""
        response = ProcessContentResponse(
            processed_content="<p>Cleaned content</p>",
            original_length=100,
            processed_length=80,
            processing_time=1.2,
            changes_made=["Removed redundant elements", "Fixed formatting"],
            message="Successfully processed"
        )
        
        assert response.processed_content == "<p>Cleaned content</p>"
        assert response.original_length == 100
        assert response.processed_length == 80
        assert response.processing_time == 1.2
        assert response.changes_made == ["Removed redundant elements", "Fixed formatting"]
        assert response.message == "Successfully processed"
        
    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        # Missing processed_content
        with pytest.raises(ValidationError):
            ProcessContentResponse(
                original_length=100,
                processed_length=80,
                processing_time=1.2
            )
            
        # Missing original_length
        with pytest.raises(ValidationError):
            ProcessContentResponse(
                processed_content="<p>Cleaned content</p>",
                processed_length=80,
                processing_time=1.2
            )
            
        # Missing processed_length
        with pytest.raises(ValidationError):
            ProcessContentResponse(
                processed_content="<p>Cleaned content</p>",
                original_length=100,
                processing_time=1.2
            )
            
        # Missing processing_time
        with pytest.raises(ValidationError):
            ProcessContentResponse(
                processed_content="<p>Cleaned content</p>",
                original_length=100,
                processed_length=80
            )


class TestExportDetails:
    """Tests for the ExportDetails model."""
    
    def test_valid_export_details(self):
        """Test that valid export details can be created."""
        details = ExportDetails(
            file_path="/path/to/export.json",
            file_size=12345,
            page_count=10,
            format="json"
        )
        
        assert details.file_path == "/path/to/export.json"
        assert details.file_size == 12345
        assert details.page_count == 10
        assert details.format == "json"
        
    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        # Missing file_path
        with pytest.raises(ValidationError):
            ExportDetails(
                file_size=12345,
                page_count=10,
                format="json"
            )
            
        # Missing file_size
        with pytest.raises(ValidationError):
            ExportDetails(
                file_path="/path/to/export.json",
                page_count=10,
                format="json"
            )
            
        # Missing page_count
        with pytest.raises(ValidationError):
            ExportDetails(
                file_path="/path/to/export.json",
                file_size=12345,
                format="json"
            )
            
        # Missing format
        with pytest.raises(ValidationError):
            ExportDetails(
                file_path="/path/to/export.json",
                file_size=12345,
                page_count=10
            )


class TestExportContentResponse:
    """Tests for the ExportContentResponse model."""
    
    def test_minimal_valid_response(self):
        """Test that a response with just the required fields is valid."""
        response = ExportContentResponse(
            operation_id="abc123",
            status=OperationStatus.COMPLETED
        )
        
        assert response.operation_id == "abc123"
        assert response.status == OperationStatus.COMPLETED
        assert response.exports is None
        assert response.message is None
        
    def test_full_response(self):
        """Test that a response with all fields is valid."""
        exports = [
            ExportDetails(
                file_path="/path/to/export.json",
                file_size=12345,
                page_count=10,
                format="json"
            ),
            ExportDetails(
                file_path="/path/to/export.md",
                file_size=5678,
                page_count=10,
                format="markdown"
            )
        ]
        
        response = ExportContentResponse(
            operation_id="abc123",
            status=OperationStatus.COMPLETED,
            exports=exports,
            message="Export completed successfully"
        )
        
        assert response.operation_id == "abc123"
        assert response.status == OperationStatus.COMPLETED
        assert len(response.exports) == 2
        assert response.exports[0].file_path == "/path/to/export.json"
        assert response.exports[1].format == "markdown"
        assert response.message == "Export completed successfully"
        
    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        # Missing operation_id
        with pytest.raises(ValidationError):
            ExportContentResponse(
                status=OperationStatus.COMPLETED
            )
            
        # Missing status
        with pytest.raises(ValidationError):
            ExportContentResponse(
                operation_id="abc123"
            )


class TestStatusCheckResponse:
    """Tests for the StatusCheckResponse model."""
    
    def test_minimal_valid_response(self):
        """Test that a response with just the required fields is valid."""
        now = datetime.now()
        
        response = StatusCheckResponse(
            operation_id="abc123",
            operation_type="extraction",
            status=OperationStatus.RUNNING,
            started_at=now,
            updated_at=now
        )
        
        assert response.operation_id == "abc123"
        assert response.operation_type == "extraction"
        assert response.status == OperationStatus.RUNNING
        assert response.started_at == now
        assert response.updated_at == now
        assert response.progress is None
        assert response.message is None
        assert response.details is None
        
    def test_full_response(self):
        """Test that a response with all fields is valid."""
        now = datetime.now()
        
        response = StatusCheckResponse(
            operation_id="abc123",
            operation_type="extraction",
            status=OperationStatus.RUNNING,
            started_at=now,
            updated_at=now,
            progress=75.0,
            message="Still processing",
            details={
                "urls_discovered": 100,
                "urls_processed": 75,
                "current_url": "https://example.com/page75"
            }
        )
        
        assert response.operation_id == "abc123"
        assert response.operation_type == "extraction"
        assert response.status == OperationStatus.RUNNING
        assert response.started_at == now
        assert response.updated_at == now
        assert response.progress == 75.0
        assert response.message == "Still processing"
        assert response.details["urls_discovered"] == 100
        assert response.details["current_url"] == "https://example.com/page75"
        
    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        now = datetime.now()
        
        # Missing operation_id
        with pytest.raises(ValidationError):
            StatusCheckResponse(
                operation_type="extraction",
                status=OperationStatus.RUNNING,
                started_at=now,
                updated_at=now
            )
            
        # Missing operation_type
        with pytest.raises(ValidationError):
            StatusCheckResponse(
                operation_id="abc123",
                status=OperationStatus.RUNNING,
                started_at=now,
                updated_at=now
            )
            
        # Missing status
        with pytest.raises(ValidationError):
            StatusCheckResponse(
                operation_id="abc123",
                operation_type="extraction",
                started_at=now,
                updated_at=now
            )
            
        # Missing started_at
        with pytest.raises(ValidationError):
            StatusCheckResponse(
                operation_id="abc123",
                operation_type="extraction",
                status=OperationStatus.RUNNING,
                updated_at=now
            )
            
        # Missing updated_at
        with pytest.raises(ValidationError):
            StatusCheckResponse(
                operation_id="abc123",
                operation_type="extraction",
                status=OperationStatus.RUNNING,
                started_at=now
            )
