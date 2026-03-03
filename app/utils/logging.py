"""Structured logging system with JSON formatting for container environments."""

import json
import logging
import sys
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class LogLevel(str, Enum):
    """Log severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs in JSON format."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "component": record.name,
            "severity": record.levelname,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "details") and record.details:
            log_data["details"] = record.details
        
        return json.dumps(log_data)


class StructuredLogger:
    """Structured logger with JSON formatting and component tracking."""
    
    def __init__(self, component_name: str):
        """Initialize structured logger for a component.
        
        Args:
            component_name: Name of the component using this logger
        """
        self.component_name = component_name
        self.logger = logging.getLogger(component_name)
        
        # Configure logger if not already configured
        if not self.logger.handlers:
            self._configure_logger()
    
    def _configure_logger(self):
        """Configure logger with JSON formatter and stdout handler."""
        # Set level to INFO by default
        self.logger.setLevel(logging.INFO)
        
        # Create stdout handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        
        # Set JSON formatter
        formatter = JSONFormatter()
        handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def info(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Log INFO level message.
        
        Args:
            message: Log message
            details: Optional additional details dictionary
        """
        self.logger.info(message, extra={"details": details})
    
    def warning(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Log WARNING level message.
        
        Args:
            message: Log message
            details: Optional additional details dictionary
        """
        self.logger.warning(message, extra={"details": details})
    
    def error(self, message: str, details: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        """Log ERROR level message.
        
        Args:
            message: Log message
            details: Optional additional details dictionary
            exc_info: Whether to include exception information
        """
        self.logger.error(message, extra={"details": details}, exc_info=exc_info)
    
    def critical(self, message: str, details: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        """Log CRITICAL level message.
        
        Args:
            message: Log message
            details: Optional additional details dictionary
            exc_info: Whether to include exception information
        """
        self.logger.critical(message, extra={"details": details}, exc_info=exc_info)


def get_logger(component_name: str) -> StructuredLogger:
    """Get or create a structured logger for a component.
    
    Args:
        component_name: Name of the component
        
    Returns:
        StructuredLogger instance for the component
    """
    return StructuredLogger(component_name)


def configure_root_logger(log_level: str = "INFO"):
    """Configure the root logger for the application.
    
    Args:
        log_level: Log level (INFO, WARNING, ERROR, CRITICAL)
    """
    # Convert string to logging level
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add stdout handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)
