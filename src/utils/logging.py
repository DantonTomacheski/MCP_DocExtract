"""
Structured logging utilities for DocExtract AI.

This module provides a structured logging system with configurable outputs
and log levels to facilitate debugging and monitoring of the application.
"""

import json
import logging
import os
import sys
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Union

from rich.console import Console
from rich.logging import RichHandler


class LogLevel(str, Enum):
    """Log level enumeration for type checking."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StructuredLogger:
    """
    A structured logger implementation for DocExtract AI.
    
    This logger provides structured JSON logging for machine consumption
    combined with rich formatted output for human readability in the console.
    """
    
    def __init__(self, name: str, level: Union[LogLevel, str] = LogLevel.INFO):
        """
        Initialize the structured logger.
        
        Args:
            name: Logger name (usually module name)
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.name = name
        self.logger = logging.getLogger(name)
        
        # Set level
        level_str = level.value if isinstance(level, LogLevel) else level
        self.logger.setLevel(getattr(logging, level_str))
        
        # Avoid duplicate handlers
        if self.logger.handlers:
            return
            
        # Create console handler with rich formatting
        console = Console(highlight=True)
        console_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            markup=True,
            rich_tracebacks=True
        )
        console_handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(console_handler)
        
        # Create file handler for JSON logs if enabled
        log_path = os.environ.get("DOC_EXTRACT_LOG_PATH")
        if log_path:
            os.makedirs(log_path, exist_ok=True)
            file_path = os.path.join(
                log_path, 
                f"docextract_{datetime.now().strftime('%Y%m%d')}.jsonl"
            )
            file_handler = logging.FileHandler(file_path)
            file_handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(file_handler)
            
        # Ensure propagation is on
        self.logger.propagate = True
    
    def _format_structured_log(
        self, 
        message: str,
        level: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format a structured log message as JSON.
        
        Args:
            message: The log message
            level: The log level
            context: Additional context data
            
        Returns:
            JSON formatted log string
        """
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "logger": self.name,
            "message": message
        }
        
        if context:
            log_data["context"] = context
            
        return json.dumps(log_data)
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a debug message.
        
        Args:
            message: The message to log
            context: Additional context data
        """
        if context:
            self.logger.debug(
                self._format_structured_log(message, "DEBUG", context)
            )
        else:
            self.logger.debug(message)
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an info message.
        
        Args:
            message: The message to log
            context: Additional context data
        """
        if context:
            self.logger.info(
                self._format_structured_log(message, "INFO", context)
            )
        else:
            self.logger.info(message)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a warning message.
        
        Args:
            message: The message to log
            context: Additional context data
        """
        if context:
            self.logger.warning(
                self._format_structured_log(message, "WARNING", context)
            )
        else:
            self.logger.warning(message)
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an error message.
        
        Args:
            message: The message to log
            context: Additional context data
        """
        if context:
            self.logger.error(
                self._format_structured_log(message, "ERROR", context)
            )
        else:
            self.logger.error(message)
    
    def critical(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a critical message.
        
        Args:
            message: The message to log
            context: Additional context data
        """
        if context:
            self.logger.critical(
                self._format_structured_log(message, "CRITICAL", context)
            )
        else:
            self.logger.critical(message)
            

# Create a default logger instance
def get_logger(name: str, level: Union[LogLevel, str] = LogLevel.INFO) -> StructuredLogger:
    """
    Get a structured logger for the given name.
    
    Args:
        name: Logger name (usually module name)
        level: Log level
        
    Returns:
        A configured StructuredLogger instance
    """
    return StructuredLogger(name, level)
