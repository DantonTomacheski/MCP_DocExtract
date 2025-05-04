"""
Unit tests for the structured logging module.

These tests verify that the structured logger works correctly,
including log formatting, levels, and JSON output.
"""

import json
import logging
import os
from unittest.mock import MagicMock, patch
import pytest

from src.utils.logging import StructuredLogger, LogLevel, get_logger


class TestStructuredLogger:
    """Tests for the StructuredLogger class."""
    
    def test_logger_initialization(self):
        """Test that the logger initializes correctly."""
        logger = StructuredLogger("test_logger", LogLevel.DEBUG)
        
        assert logger.name == "test_logger"
        assert logger.logger.level == logging.DEBUG
        assert logger.logger.handlers, "Logger should have at least one handler"
        
    def test_string_log_level(self):
        """Test that string log levels are handled correctly."""
        logger = StructuredLogger("test_logger", "WARNING")
        
        assert logger.logger.level == logging.WARNING
    
    @patch("logging.Logger.debug")
    def test_debug_method(self, mock_debug):
        """Test the debug method."""
        logger = StructuredLogger("test_logger")
        logger.debug("Test debug message")
        
        mock_debug.assert_called_once_with("Test debug message")
    
    @patch("logging.Logger.info")
    def test_info_method(self, mock_info):
        """Test the info method."""
        logger = StructuredLogger("test_logger")
        logger.info("Test info message")
        
        mock_info.assert_called_once_with("Test info message")
    
    @patch("logging.Logger.warning")
    def test_warning_method(self, mock_warning):
        """Test the warning method."""
        logger = StructuredLogger("test_logger")
        logger.warning("Test warning message")
        
        mock_warning.assert_called_once_with("Test warning message")
    
    @patch("logging.Logger.error")
    def test_error_method(self, mock_error):
        """Test the error method."""
        logger = StructuredLogger("test_logger")
        logger.error("Test error message")
        
        mock_error.assert_called_once_with("Test error message")
    
    @patch("logging.Logger.critical")
    def test_critical_method(self, mock_critical):
        """Test the critical method."""
        logger = StructuredLogger("test_logger")
        logger.critical("Test critical message")
        
        mock_critical.assert_called_once_with("Test critical message")
    
    @patch("logging.Logger.info")
    def test_structured_json_format(self, mock_info):
        """Test the structured JSON formatting with context."""
        logger = StructuredLogger("test_logger")
        context = {"user": "test", "request_id": "123"}
        logger.info("Test message", context)
        
        # Get the argument passed to info
        args, _ = mock_info.call_args
        log_message = args[0]
        
        # Verify the structure
        log_data = json.loads(log_message)
        assert log_data["message"] == "Test message"
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test_logger"
        assert "timestamp" in log_data
        assert log_data["context"] == context
    
    @patch.dict(os.environ, {"DOC_EXTRACT_LOG_PATH": "/tmp/logs"})
    @patch("os.makedirs")
    @patch("logging.FileHandler")
    def test_file_handler_creation(self, mock_file_handler, mock_makedirs):
        """Test that a file handler is created when log path is set."""
        mock_file_handler_instance = MagicMock()
        mock_file_handler.return_value = mock_file_handler_instance
        
        logger = StructuredLogger("test_logger")
        
        mock_makedirs.assert_called_once_with("/tmp/logs", exist_ok=True)
        mock_file_handler.assert_called_once()
        assert mock_file_handler_instance.setFormatter.called


class TestLoggerFactory:
    """Tests for the logger factory function."""
    
    def test_get_logger(self):
        """Test the get_logger factory function."""
        logger = get_logger("test_factory", LogLevel.WARNING)
        
        assert isinstance(logger, StructuredLogger)
        assert logger.name == "test_factory"
        assert logger.logger.level == logging.WARNING
