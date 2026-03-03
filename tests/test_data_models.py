"""
Unit tests for data models.

Tests basic validation and functionality of Pydantic models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.data_models import (
    Article,
    Summary,
    SummaryResponse,
    CacheEntry,
    ErrorLog,
    ErrorSeverity,
    UserError,
    AppConfig,
)


class TestArticleModel:
    """Tests for Article model."""
    
    def test_valid_article(self):
        """Test creating a valid article."""
        article = Article(
            id="test-123",
            title="Test Article",
            source="Test Source",
            publication_date=datetime.utcnow(),
            content="This is test content for the article.",
            url="https://example.com/article",
            category="Technology"
        )
        assert article.id == "test-123"
        assert article.title == "Test Article"
        assert article.category == "Technology"
    
    def test_article_empty_title(self):
        """Test that empty title raises validation error."""
        with pytest.raises(ValidationError, match="title cannot be empty"):
            Article(
                id="test-123",
                title="   ",
                source="Test Source",
                publication_date=datetime.utcnow(),
                content="Content",
                url="https://example.com/article"
            )
    
    def test_article_empty_content(self):
        """Test that empty content raises validation error."""
        with pytest.raises(ValidationError, match="content cannot be empty"):
            Article(
                id="test-123",
                title="Title",
                source="Test Source",
                publication_date=datetime.utcnow(),
                content="",
                url="https://example.com/article"
            )


class TestSummaryModel:
    """Tests for Summary model."""
    
    def test_valid_summary(self):
        """Test creating a valid summary."""
        summary_text = " ".join(["word"] * 75)  # 75 words
        summary = Summary(
            article_id="test-123",
            title="Test Article",
            summary_text=summary_text,
            source="Test Source",
            publication_date=datetime.utcnow(),
            category="Technology",
            generated_at=datetime.utcnow(),
            key_facts={"who": "test", "what": "test"}
        )
        assert summary.article_id == "test-123"
        assert len(summary.summary_text.split()) == 75
    
    def test_summary_too_short(self):
        """Test that summary with <50 words raises validation error."""
        summary_text = " ".join(["word"] * 30)  # 30 words
        with pytest.raises(ValidationError, match="Summary must be 50-150 words"):
            Summary(
                article_id="test-123",
                title="Test Article",
                summary_text=summary_text,
                source="Test Source",
                publication_date=datetime.utcnow(),
                generated_at=datetime.utcnow(),
                key_facts={}
            )
    
    def test_summary_too_long(self):
        """Test that summary with >150 words raises validation error."""
        summary_text = " ".join(["word"] * 200)  # 200 words
        with pytest.raises(ValidationError, match="Summary must be 50-150 words"):
            Summary(
                article_id="test-123",
                title="Test Article",
                summary_text=summary_text,
                source="Test Source",
                publication_date=datetime.utcnow(),
                generated_at=datetime.utcnow(),
                key_facts={}
            )


class TestCacheEntryModel:
    """Tests for CacheEntry model."""
    
    def test_cache_entry_not_expired(self):
        """Test that fresh cache entry is not expired."""
        entry = CacheEntry[str](
            value="test_value",
            created_at=datetime.utcnow(),
            ttl_seconds=60
        )
        assert not entry.is_expired()
    
    def test_cache_entry_expired(self):
        """Test that old cache entry is expired."""
        from datetime import timedelta
        old_time = datetime.utcnow() - timedelta(seconds=120)
        entry = CacheEntry[str](
            value="test_value",
            created_at=old_time,
            ttl_seconds=60
        )
        assert entry.is_expired()


class TestErrorModels:
    """Tests for error models."""
    
    def test_error_log_valid(self):
        """Test creating a valid error log."""
        error_log = ErrorLog(
            timestamp=datetime.utcnow(),
            component="TestComponent",
            severity=ErrorSeverity.ERROR,
            message="Test error message",
            details={"key": "value"}
        )
        assert error_log.component == "TestComponent"
        assert error_log.severity == ErrorSeverity.ERROR
    
    def test_error_log_empty_component(self):
        """Test that empty component raises validation error."""
        with pytest.raises(ValidationError, match="component cannot be empty"):
            ErrorLog(
                timestamp=datetime.utcnow(),
                component="",
                severity=ErrorSeverity.ERROR,
                message="Test message"
            )
    
    def test_user_error_valid(self):
        """Test creating a valid user error."""
        user_error = UserError(
            message="Something went wrong",
            retry_after=60
        )
        assert user_error.message == "Something went wrong"
        assert user_error.retry_after == 60


class TestAppConfig:
    """Tests for AppConfig model."""
    
    def test_valid_config(self, monkeypatch):
        """Test creating valid configuration."""
        monkeypatch.setenv("HUGGINGFACE_TOKEN", "test_token_123")
        monkeypatch.setenv("MCP_SERVER_URL", "https://mcp.example.com")
        
        config = AppConfig()
        assert config.huggingface_token == "test_token_123"
        assert config.mcp_server_url == "https://mcp.example.com"
        assert config.port == 8080  # default
        assert config.cache_ttl_minutes == 30  # default
    
    def test_missing_required_config(self, monkeypatch):
        """Test that missing required config raises validation error."""
        monkeypatch.delenv("HUGGINGFACE_TOKEN", raising=False)
        monkeypatch.delenv("MCP_SERVER_URL", raising=False)
        
        with pytest.raises(ValidationError, match="Field required"):
            AppConfig()
    
    def test_invalid_port(self, monkeypatch):
        """Test that invalid port raises validation error."""
        monkeypatch.setenv("HUGGINGFACE_TOKEN", "test_token")
        monkeypatch.setenv("MCP_SERVER_URL", "https://mcp.example.com")
        monkeypatch.setenv("PORT", "99999")
        
        with pytest.raises(ValidationError, match="Port must be between 1 and 65535"):
            AppConfig()
    
    def test_invalid_log_level(self, monkeypatch):
        """Test that invalid log level raises validation error."""
        monkeypatch.setenv("HUGGINGFACE_TOKEN", "test_token")
        monkeypatch.setenv("MCP_SERVER_URL", "https://mcp.example.com")
        monkeypatch.setenv("LOG_LEVEL", "INVALID")
        
        with pytest.raises(ValidationError, match="log_level must be one of"):
            AppConfig()
    
    def test_custom_values(self, monkeypatch):
        """Test that custom values override defaults."""
        monkeypatch.setenv("HUGGINGFACE_TOKEN", "test_token")
        monkeypatch.setenv("MCP_SERVER_URL", "https://mcp.example.com")
        monkeypatch.setenv("PORT", "3000")
        monkeypatch.setenv("CACHE_TTL_MINUTES", "60")
        monkeypatch.setenv("LOG_LEVEL", "debug")
        
        config = AppConfig()
        assert config.port == 3000
        assert config.cache_ttl_minutes == 60
        assert config.log_level == "DEBUG"  # Should be uppercased
