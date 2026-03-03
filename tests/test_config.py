"""
Tests for configuration module.

Tests the config.py module's ability to load, validate, and fail fast
with descriptive error messages when configuration is missing or invalid.
"""

import os
import sys
import pytest
from unittest.mock import patch
from pydantic import ValidationError
from app.models.data_models import AppConfig


class TestConfigLoading:
    """Test configuration loading and validation."""
    
    def test_config_loads_with_valid_environment(self, monkeypatch):
        """Test that config loads successfully with all required variables."""
        # Set required environment variables
        monkeypatch.setenv("HUGGINGFACE_TOKEN", "test_token_123")
        monkeypatch.setenv("MCP_SERVER_URL", "http://localhost:9000")
        
        # Import config module (will trigger validation)
        from app.config import load_config
        config = load_config()
        
        assert config is not None
        assert config.huggingface_token == "test_token_123"
        assert config.mcp_server_url == "http://localhost:9000"
        assert config.port == 8080  # Default value
        assert config.cache_ttl_minutes == 30  # Default value
    
    def test_config_loads_with_custom_values(self, monkeypatch):
        """Test that config loads with custom optional values."""
        monkeypatch.setenv("HUGGINGFACE_TOKEN", "custom_token")
        monkeypatch.setenv("MCP_SERVER_URL", "http://mcp.example.com")
        monkeypatch.setenv("PORT", "9090")
        monkeypatch.setenv("CACHE_TTL_MINUTES", "60")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        
        from app.config import load_config
        config = load_config()
        
        assert config.port == 9090
        assert config.cache_ttl_minutes == 60
        assert config.log_level == "DEBUG"
    
    def test_config_fails_without_huggingface_token(self, monkeypatch):
        """Test that config fails fast when HUGGINGFACE_TOKEN is missing."""
        # Only set MCP_SERVER_URL, omit HUGGINGFACE_TOKEN
        monkeypatch.setenv("MCP_SERVER_URL", "http://localhost:9000")
        monkeypatch.delenv("HUGGINGFACE_TOKEN", raising=False)
        
        with pytest.raises(SystemExit) as exc_info:
            from app.config import load_config
            load_config()
        
        assert exc_info.value.code == 1
    
    def test_config_fails_without_mcp_server_url(self, monkeypatch):
        """Test that config fails fast when MCP_SERVER_URL is missing."""
        # Only set HUGGINGFACE_TOKEN, omit MCP_SERVER_URL
        monkeypatch.setenv("HUGGINGFACE_TOKEN", "test_token")
        monkeypatch.delenv("MCP_SERVER_URL", raising=False)
        
        with pytest.raises(SystemExit) as exc_info:
            from app.config import load_config
            load_config()
        
        assert exc_info.value.code == 1
    
    def test_config_fails_with_empty_required_values(self, monkeypatch):
        """Test that config fails when required values are empty strings."""
        monkeypatch.setenv("HUGGINGFACE_TOKEN", "")
        monkeypatch.setenv("MCP_SERVER_URL", "http://localhost:9000")
        
        with pytest.raises(SystemExit) as exc_info:
            from app.config import load_config
            load_config()
        
        assert exc_info.value.code == 1
    
    def test_config_fails_with_invalid_port(self, monkeypatch):
        """Test that config fails with invalid port number."""
        monkeypatch.setenv("HUGGINGFACE_TOKEN", "test_token")
        monkeypatch.setenv("MCP_SERVER_URL", "http://localhost:9000")
        monkeypatch.setenv("PORT", "99999")  # Invalid port
        
        with pytest.raises(SystemExit) as exc_info:
            from app.config import load_config
            load_config()
        
        assert exc_info.value.code == 1
    
    def test_config_fails_with_negative_cache_ttl(self, monkeypatch):
        """Test that config fails with negative cache TTL."""
        monkeypatch.setenv("HUGGINGFACE_TOKEN", "test_token")
        monkeypatch.setenv("MCP_SERVER_URL", "http://localhost:9000")
        monkeypatch.setenv("CACHE_TTL_MINUTES", "-10")
        
        with pytest.raises(SystemExit) as exc_info:
            from app.config import load_config
            load_config()
        
        assert exc_info.value.code == 1
    
    def test_config_fails_with_invalid_log_level(self, monkeypatch):
        """Test that config fails with invalid log level."""
        monkeypatch.setenv("HUGGINGFACE_TOKEN", "test_token")
        monkeypatch.setenv("MCP_SERVER_URL", "http://localhost:9000")
        monkeypatch.setenv("LOG_LEVEL", "INVALID")
        
        with pytest.raises(SystemExit) as exc_info:
            from app.config import load_config
            load_config()
        
        assert exc_info.value.code == 1
    
    def test_config_error_message_is_descriptive(self, monkeypatch, capsys):
        """Test that error messages are descriptive and helpful."""
        # Missing both required variables
        monkeypatch.delenv("HUGGINGFACE_TOKEN", raising=False)
        monkeypatch.delenv("MCP_SERVER_URL", raising=False)
        
        with pytest.raises(SystemExit):
            from app.config import load_config
            load_config()
        
        captured = capsys.readouterr()
        error_output = captured.err
        
        # Check that error message contains helpful information
        assert "CONFIGURATION ERROR" in error_output
        assert "HUGGINGFACE_TOKEN" in error_output or "MCP_SERVER_URL" in error_output
        assert "Configuration Guide" in error_output


class TestAppConfigModel:
    """Test the AppConfig model directly."""
    
    def test_appconfig_validates_required_fields(self):
        """Test that AppConfig requires huggingface_token and mcp_server_url."""
        with pytest.raises(ValidationError) as exc_info:
            AppConfig(huggingface_token="", mcp_server_url="http://test.com")
        
        errors = exc_info.value.errors()
        assert any('huggingface_token' in str(e['loc']) for e in errors)
    
    def test_appconfig_applies_defaults(self):
        """Test that AppConfig applies default values correctly."""
        config = AppConfig(
            huggingface_token="token",
            mcp_server_url="http://test.com"
        )
        
        assert config.port == 8080
        assert config.cache_ttl_minutes == 30
        assert config.news_refresh_minutes == 30
        assert config.max_concurrent_summaries == 50
        assert config.memory_limit_mb == 512
        assert config.log_level == "INFO"
    
    def test_appconfig_validates_port_range(self):
        """Test that AppConfig validates port is in valid range."""
        with pytest.raises(ValidationError) as exc_info:
            AppConfig(
                huggingface_token="token",
                mcp_server_url="http://test.com",
                port=70000
            )
        
        errors = exc_info.value.errors()
        assert any('port' in str(e['loc']) for e in errors)
    
    def test_appconfig_validates_positive_values(self):
        """Test that AppConfig validates numeric fields are positive."""
        with pytest.raises(ValidationError):
            AppConfig(
                huggingface_token="token",
                mcp_server_url="http://test.com",
                cache_ttl_minutes=-5
            )
    
    def test_appconfig_normalizes_log_level(self):
        """Test that AppConfig normalizes log level to uppercase."""
        config = AppConfig(
            huggingface_token="token",
            mcp_server_url="http://test.com",
            log_level="debug"
        )
        
        assert config.log_level == "DEBUG"
