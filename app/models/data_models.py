"""
Data models for AI News Summarizer application.

This module defines Pydantic models for articles, summaries, cache entries,
error handling, and application configuration with comprehensive validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings


# ============================================================================
# Article Models
# ============================================================================

class Article(BaseModel):
    """Raw news article from MCP Server."""
    
    id: str
    title: str
    source: str
    publication_date: datetime
    content: str
    url: HttpUrl
    category: Optional[str] = None
    
    @field_validator('title', 'source', 'content')
    @classmethod
    def validate_non_empty(cls, v, info):
        """Ensure required string fields are not empty."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")
        return v.strip()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# Summary Models
# ============================================================================

class Summary(BaseModel):
    """AI-generated summary with metadata."""
    
    article_id: str
    title: str
    summary_text: str = Field(..., min_length=50, max_length=1000)
    source: str
    publication_date: datetime
    category: Optional[str] = None
    generated_at: datetime
    key_facts: dict
    
    @field_validator('summary_text')
    @classmethod
    def validate_word_count(cls, v):
        """Ensure summary is between 50-150 words."""
        word_count = len(v.split())
        if word_count < 50 or word_count > 150:
            raise ValueError(f"Summary must be 50-150 words, got {word_count}")
        return v
    
    @field_validator('title', 'source')
    @classmethod
    def validate_non_empty(cls, v, info):
        """Ensure required string fields are not empty."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")
        return v.strip()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SummaryResponse(BaseModel):
    """API response format for frontend."""
    
    id: str
    title: str
    summary: str
    source: str
    published: str  # Human-readable format
    category: str
    timestamp: datetime
    last_updated: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# Cache Models
# ============================================================================

T = TypeVar('T')

class CacheEntry(BaseModel, Generic[T]):
    """Cache entry with TTL tracking."""
    
    value: T
    created_at: datetime
    ttl_seconds: int
    
    def is_expired(self) -> bool:
        """Check if entry has exceeded TTL."""
        age = (datetime.utcnow() - self.created_at).total_seconds()
        return age > self.ttl_seconds
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# Error Models
# ============================================================================

class ErrorSeverity(str, Enum):
    """Log severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorLog(BaseModel):
    """Structured error logging."""
    
    timestamp: datetime
    component: str
    severity: ErrorSeverity
    message: str
    details: Optional[dict] = None
    
    @field_validator('component', 'message')
    @classmethod
    def validate_non_empty(cls, v, info):
        """Ensure required string fields are not empty."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")
        return v.strip()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserError(BaseModel):
    """User-facing error response."""
    
    message: str
    retry_after: Optional[int] = None  # seconds
    
    @field_validator('message')
    @classmethod
    def validate_non_empty(cls, v):
        """Ensure message is not empty."""
        if not v or not v.strip():
            raise ValueError("message cannot be empty")
        return v.strip()


# ============================================================================
# Configuration Models
# ============================================================================

class AppConfig(BaseSettings):
    """Application configuration from environment variables."""
    
    # Required configuration
    huggingface_token: str
    
    # Optional with defaults
    mcp_server_url: str = "http://localhost:3000"  # Not used, RSS feeds are direct
    port: int = 8080
    cache_ttl_minutes: int = 30
    news_refresh_minutes: int = 30
    max_concurrent_summaries: int = 50
    memory_limit_mb: int = 512
    log_level: str = "INFO"
    
    @field_validator('huggingface_token')
    @classmethod
    def validate_required(cls, v, info):
        """Validate required configuration fields are present and non-empty."""
        if not v or not v.strip():
            raise ValueError(f"Required configuration missing: {info.field_name}")
        return v.strip()
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        """Validate port is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v
    
    @field_validator('cache_ttl_minutes', 'news_refresh_minutes', 'max_concurrent_summaries', 'memory_limit_mb')
    @classmethod
    def validate_positive(cls, v, info):
        """Validate numeric fields are positive."""
        if v <= 0:
            raise ValueError(f"{info.field_name} must be positive, got {v}")
        return v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level is valid."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}, got {v}")
        return v_upper
    
    class Config:
        env_file = ".env"
        case_sensitive = False
