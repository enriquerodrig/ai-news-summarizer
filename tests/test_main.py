"""
Tests for FastAPI main application.

This module tests the core API endpoints including health checks,
summary retrieval, and caching behavior.
"""

import os
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

# Set required environment variables before importing app
os.environ.setdefault("HUGGINGFACE_TOKEN", "test_token")
os.environ.setdefault("MCP_SERVER_URL", "https://test.example.com/rss")

from app.main import app, app_state
from app.models.data_models import Article, Summary


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_article():
    """Create a mock article for testing."""
    return Article(
        id="test123",
        title="Test Article",
        source="Test Source",
        publication_date=datetime.utcnow(),
        content="This is a test article with enough content to be summarized properly.",
        url="https://example.com/article",
        category="Technology"
    )


@pytest.fixture
def mock_summary():
    """Create a mock summary for testing."""
    # Create a summary with exactly 50 words to meet the minimum requirement
    summary_text = " ".join(["word"] * 50)
    return Summary(
        article_id="test123",
        title="Test Article",
        summary_text=summary_text,
        source="Test Source",
        publication_date=datetime.utcnow(),
        category="Technology",
        generated_at=datetime.utcnow(),
        key_facts={"who": "Test", "what": "Testing", "when": "Now", "where": "Here", "why": "Because"}
    )


def test_health_check_endpoint(client):
    """Test that health check endpoint returns 200 status."""
    response = client.get("/api/health")
    assert response.status_code in [200, 503]  # 503 if components not initialized
    
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert data["status"] in ["healthy", "degraded", "unhealthy"]


def test_index_endpoint_returns_html(client):
    """Test that index endpoint returns HTML content."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "AI News Summarizer" in response.text


@pytest.mark.asyncio
async def test_summaries_endpoint_with_cache_miss(client, mock_article, mock_summary):
    """Test summaries endpoint when cache is empty (cache miss)."""
    # Mock the components
    with patch.object(app_state, 'cache_manager') as mock_cache, \
         patch.object(app_state, 'news_aggregator') as mock_aggregator, \
         patch.object(app_state, 'ai_summarizer') as mock_summarizer:
        
        # Setup mocks
        mock_cache.get = AsyncMock(return_value=None)  # Cache miss
        mock_cache.set = AsyncMock()
        mock_aggregator.fetch_latest_news = AsyncMock(return_value=[mock_article])
        mock_summarizer.batch_summarize = AsyncMock(return_value=[mock_summary])
        
        # Make request
        response = client.get("/api/summaries")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_summaries_endpoint_with_cache_hit(client):
    """Test summaries endpoint when cache has data (cache hit)."""
    cached_data = [
        {
            "id": "test123",
            "title": "Cached Article",
            "summary": "This is a cached summary with enough words to meet requirements.",
            "source": "Test Source",
            "published": "1 hour ago",
            "category": "Technology",
            "timestamp": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }
    ]
    
    with patch.object(app_state, 'cache_manager') as mock_cache:
        mock_cache.get = AsyncMock(return_value=cached_data)
        
        response = client.get("/api/summaries")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Cached Article"


@pytest.mark.asyncio
async def test_summaries_endpoint_sorts_by_date(client, mock_article, mock_summary):
    """Test that summaries are sorted by publication date (newest first)."""
    from datetime import timedelta
    
    # Create articles with different dates
    old_article = Article(
        id="old123",
        title="Old Article",
        source="Test Source",
        publication_date=datetime.utcnow() - timedelta(hours=5),
        content="Old article content with sufficient length for processing.",
        url="https://example.com/old",
        category="Technology"
    )
    
    new_article = Article(
        id="new123",
        title="New Article",
        source="Test Source",
        publication_date=datetime.utcnow() - timedelta(hours=1),
        content="New article content with sufficient length for processing.",
        url="https://example.com/new",
        category="Technology"
    )
    
    old_summary = Summary(
        article_id="old123",
        title="Old Article",
        summary_text=" ".join(["word"] * 50),  # Exactly 50 words
        source="Test Source",
        publication_date=old_article.publication_date,
        category="Technology",
        generated_at=datetime.utcnow(),
        key_facts={}
    )
    
    new_summary = Summary(
        article_id="new123",
        title="New Article",
        summary_text=" ".join(["word"] * 50),  # Exactly 50 words
        source="Test Source",
        publication_date=new_article.publication_date,
        category="Technology",
        generated_at=datetime.utcnow(),
        key_facts={}
    )
    
    with patch.object(app_state, 'cache_manager') as mock_cache, \
         patch.object(app_state, 'news_aggregator') as mock_aggregator, \
         patch.object(app_state, 'ai_summarizer') as mock_summarizer:
        
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_aggregator.fetch_latest_news = AsyncMock(return_value=[old_article, new_article])
        mock_summarizer.batch_summarize = AsyncMock(return_value=[old_summary, new_summary])
        
        response = client.get("/api/summaries")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify newest article is first
        assert len(data) >= 2
        # The newer article should come first
        assert data[0]["title"] == "New Article"
        assert data[1]["title"] == "Old Article"


def test_error_handling_for_missing_components(client):
    """Test that appropriate errors are returned when components are not initialized."""
    # This test verifies graceful degradation
    response = client.get("/api/health")
    
    # Should still return a response even if components aren't fully initialized
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_summaries_caches_results(client, mock_article, mock_summary):
    """Test that summaries endpoint caches results after fetching."""
    with patch.object(app_state, 'cache_manager') as mock_cache, \
         patch.object(app_state, 'news_aggregator') as mock_aggregator, \
         patch.object(app_state, 'ai_summarizer') as mock_summarizer:
        
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_aggregator.fetch_latest_news = AsyncMock(return_value=[mock_article])
        mock_summarizer.batch_summarize = AsyncMock(return_value=[mock_summary])
        
        response = client.get("/api/summaries")
        
        assert response.status_code == 200
        
        # Verify cache.set was called
        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        assert call_args[0][0] == "news_summaries"  # cache key
        assert isinstance(call_args[0][1], list)  # cached value is a list


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
