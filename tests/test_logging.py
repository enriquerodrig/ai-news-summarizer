"""Tests for structured logging system."""

import json
import logging
from io import StringIO
from app.utils.logging import (
    StructuredLogger,
    get_logger,
    configure_root_logger,
    JSONFormatter
)


def test_json_formatter():
    """Test that JSONFormatter produces valid JSON output."""
    formatter = JSONFormatter()
    
    # Create a log record
    record = logging.LogRecord(
        name="test_component",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    # Format the record
    output = formatter.format(record)
    
    # Parse as JSON
    log_data = json.loads(output)
    
    # Verify structure
    assert "timestamp" in log_data
    assert "component" in log_data
    assert "severity" in log_data
    assert "message" in log_data
    assert log_data["component"] == "test_component"
    assert log_data["severity"] == "INFO"
    assert log_data["message"] == "Test message"


def test_structured_logger_info():
    """Test INFO level logging."""
    logger = get_logger("test_component")
    
    # Capture stdout
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.logger.handlers = [handler]
    
    # Log a message
    logger.info("Test info message", details={"key": "value"})
    
    # Parse output
    output = stream.getvalue()
    log_data = json.loads(output)
    
    assert log_data["severity"] == "INFO"
    assert log_data["message"] == "Test info message"
    assert log_data["details"]["key"] == "value"


def test_structured_logger_warning():
    """Test WARNING level logging."""
    logger = get_logger("test_component")
    
    # Capture stdout
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.logger.handlers = [handler]
    
    # Log a message
    logger.warning("Test warning message")
    
    # Parse output
    output = stream.getvalue()
    log_data = json.loads(output)
    
    assert log_data["severity"] == "WARNING"
    assert log_data["message"] == "Test warning message"


def test_structured_logger_error():
    """Test ERROR level logging."""
    logger = get_logger("test_component")
    
    # Capture stdout
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.logger.handlers = [handler]
    
    # Log a message
    logger.error("Test error message", details={"error_code": 500})
    
    # Parse output
    output = stream.getvalue()
    log_data = json.loads(output)
    
    assert log_data["severity"] == "ERROR"
    assert log_data["message"] == "Test error message"
    assert log_data["details"]["error_code"] == 500


def test_structured_logger_critical():
    """Test CRITICAL level logging."""
    logger = get_logger("test_component")
    
    # Capture stdout
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.logger.handlers = [handler]
    
    # Log a message
    logger.critical("Test critical message")
    
    # Parse output
    output = stream.getvalue()
    log_data = json.loads(output)
    
    assert log_data["severity"] == "CRITICAL"
    assert log_data["message"] == "Test critical message"


def test_logger_with_exception():
    """Test logging with exception information."""
    logger = get_logger("test_component")
    
    # Capture stdout
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.logger.handlers = [handler]
    
    # Log with exception
    try:
        raise ValueError("Test exception")
    except ValueError:
        logger.error("Error occurred", exc_info=True)
    
    # Parse output
    output = stream.getvalue()
    log_data = json.loads(output)
    
    assert log_data["severity"] == "ERROR"
    assert log_data["message"] == "Error occurred"
    assert "exception" in log_data
    assert "ValueError: Test exception" in log_data["exception"]


def test_component_name_in_logs():
    """Test that component name is included in all logs."""
    component_name = "news_aggregator"
    logger = get_logger(component_name)
    
    # Capture stdout
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.logger.handlers = [handler]
    
    # Log messages at different levels
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    # Parse all outputs
    outputs = stream.getvalue().strip().split('\n')
    
    for output in outputs:
        log_data = json.loads(output)
        assert log_data["component"] == component_name


def test_timestamp_format():
    """Test that timestamp is in ISO format with Z suffix."""
    logger = get_logger("test_component")
    
    # Capture stdout
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.logger.handlers = [handler]
    
    # Log a message
    logger.info("Test message")
    
    # Parse output
    output = stream.getvalue()
    log_data = json.loads(output)
    
    # Verify timestamp format
    timestamp = log_data["timestamp"]
    assert timestamp.endswith("Z")
    assert "T" in timestamp
    # Should be parseable as ISO format
    from datetime import datetime
    datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
