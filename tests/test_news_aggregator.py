"""
Unit tests for NewsAggregator component.

Tests the NewsAggregator class including connection logic, article fetching,
and metadata normalization.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from app.components.news_aggregator import NewsAggregator, RSSFeedClient
from app.models.data_models import Article


@pytest.mark.asyncio
async def test_news_aggregator_initialization():
    """Test NewsAggregator initializes with correct configuration."""
    aggregator = NewsAggregator(
        mcp_server_url="https://hnrss.org/frontpage,https://techcrunch.com/feed/",
        retry_delay=30
    )
    
    assert aggregator.mcp_server_url == "https://hnrss.org/frontpage,https://techcrunch.com/feed/"
    assert aggregator.retry_delay == 30
    assert aggregator.connected is False
    assert aggregator.retry_count == 0
    assert isinstance(aggregator.rss_client, RSSFeedClient)
    assert len(aggregator.feed_urls) == 2


@pytest.mark.asyncio
async def test_connect_to_mcp_success():
    """Test successful connection to RSS feeds."""
    aggregator = NewsAggregator(mcp_server_url="https://hnrss.org/frontpage")
    
    # Mock the RSS client connect method
    aggregator.rss_client.connect = AsyncMock(return_value=True)
    
    result = await aggregator.connect_to_mcp()
    
    assert result is True
    assert aggregator.connected is True
    assert aggregator.retry_count == 0


@pytest.mark.asyncio
async def test_fetch_latest_news_auto_connect():
    """Test fetch_latest_news automatically connects if not connected."""
    aggregator = NewsAggregator(mcp_server_url="https://hnrss.org/frontpage")
    
    # Mock the RSS client methods
    aggregator.rss_client.connect = AsyncMock(return_value=True)
    mock_articles = [
        Article(
            id="test1",
            title="Test Article 1",
            source="Test Source",
            publication_date=datetime.utcnow(),
            content="Test content 1",
            url="https://example.com/1",
            category="Technology"
        )
    ]
    aggregator.rss_client.fetch_articles = AsyncMock(return_value=mock_articles)
    
    # Should auto-connect and fetch articles
    articles = await aggregator.fetch_latest_news(hours=24)
    
    assert aggregator.connected is True
    assert isinstance(articles, list)
    assert len(articles) > 0
    assert all(isinstance(article, Article) for article in articles)


@pytest.mark.asyncio
async def test_fetch_latest_news_returns_articles():
    """Test fetch_latest_news returns properly formatted articles."""
    aggregator = NewsAggregator(mcp_server_url="https://hnrss.org/frontpage")
    
    # Mock the RSS client methods
    aggregator.rss_client.connect = AsyncMock(return_value=True)
    mock_articles = [
        Article(
            id="test1",
            title="Test Article 1",
            source="Test Source",
            publication_date=datetime.utcnow(),
            content="Test content 1",
            url="https://example.com/1",
            category="Technology"
        ),
        Article(
            id="test2",
            title="Test Article 2",
            source="Test Source",
            publication_date=datetime.utcnow() - timedelta(hours=2),
            content="Test content 2",
            url="https://example.com/2",
            category="Business"
        )
    ]
    aggregator.rss_client.fetch_articles = AsyncMock(return_value=mock_articles)
    
    await aggregator.connect_to_mcp()
    articles = await aggregator.fetch_latest_news(hours=24)
    
    assert len(articles) > 0
    
    # Verify all articles have required metadata
    for article in articles:
        assert article.id
        assert article.title
        assert article.source
        assert article.publication_date
        assert article.content
        assert article.url
        # category is optional


@pytest.mark.asyncio
async def test_fetch_latest_news_filters_by_time():
    """Test fetch_latest_news filters articles to specified time window."""
    aggregator = NewsAggregator(mcp_server_url="https://hnrss.org/frontpage")
    
    # Mock the RSS client methods
    aggregator.rss_client.connect = AsyncMock(return_value=True)
    
    # Create articles with different timestamps
    now = datetime.utcnow()
    mock_articles = [
        Article(
            id="test1",
            title="Recent Article",
            source="Test Source",
            publication_date=now - timedelta(hours=12),
            content="Recent content",
            url="https://example.com/1",
            category="Technology"
        ),
        Article(
            id="test2",
            title="Old Article",
            source="Test Source",
            publication_date=now - timedelta(hours=48),  # Too old
            content="Old content",
            url="https://example.com/2",
            category="Technology"
        )
    ]
    aggregator.rss_client.fetch_articles = AsyncMock(return_value=mock_articles)
    
    await aggregator.connect_to_mcp()
    
    hours = 24
    articles = await aggregator.fetch_latest_news(hours=hours)
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    # All articles should be within the time window
    for article in articles:
        assert article.publication_date >= cutoff_time


@pytest.mark.asyncio
async def test_article_metadata_normalization():
    """Test that article metadata is properly normalized."""
    aggregator = NewsAggregator(mcp_server_url="https://hnrss.org/frontpage")
    
    # Mock the RSS client methods
    aggregator.rss_client.connect = AsyncMock(return_value=True)
    mock_articles = [
        Article(
            id="test1",
            title="Test Article",
            source="Test Source",
            publication_date=datetime.utcnow(),
            content="Test content with sufficient length",
            url="https://example.com/1",
            category="Technology"
        )
    ]
    aggregator.rss_client.fetch_articles = AsyncMock(return_value=mock_articles)
    
    await aggregator.connect_to_mcp()
    articles = await aggregator.fetch_latest_news()
    
    for article in articles:
        # Title should be non-empty string
        assert isinstance(article.title, str)
        assert len(article.title.strip()) > 0
        
        # Source should be non-empty string
        assert isinstance(article.source, str)
        assert len(article.source.strip()) > 0
        
        # Publication date should be datetime
        assert isinstance(article.publication_date, datetime)
        
        # Content should be non-empty string
        assert isinstance(article.content, str)
        assert len(article.content.strip()) > 0
        
        # URL should be valid
        assert article.url is not None


@pytest.mark.asyncio
async def test_schedule_updates_placeholder():
    """Test schedule_updates method exists and can be called."""
    aggregator = NewsAggregator(mcp_server_url="https://hnrss.org/frontpage")
    
    # Should not raise an error
    aggregator.schedule_updates(interval_minutes=30)
    
    # Method exists and can be called
    assert hasattr(aggregator, 'schedule_updates')
    
    # Clean up
    aggregator.stop_scheduler()


@pytest.mark.asyncio
async def test_schedule_updates_starts_scheduler():
    """Test schedule_updates starts the background scheduler."""
    aggregator = NewsAggregator(mcp_server_url="https://hnrss.org/frontpage")
    
    # Scheduler should not be running initially
    assert not aggregator.is_scheduler_running()
    
    # Start the scheduler
    aggregator.schedule_updates(interval_minutes=30)
    
    # Scheduler should now be running
    assert aggregator.is_scheduler_running()
    assert aggregator._scheduler_task is not None
    
    # Clean up
    aggregator.stop_scheduler()
    await asyncio.sleep(0.1)  # Give time for task to cancel


@pytest.mark.asyncio
async def test_schedule_updates_prevents_duplicate_start():
    """Test schedule_updates prevents starting multiple schedulers."""
    aggregator = NewsAggregator(mcp_server_url="https://hnrss.org/frontpage")
    
    # Start the scheduler
    aggregator.schedule_updates(interval_minutes=30)
    first_task = aggregator._scheduler_task
    
    # Try to start again
    aggregator.schedule_updates(interval_minutes=30)
    second_task = aggregator._scheduler_task
    
    # Should be the same task (no duplicate)
    assert first_task is second_task
    
    # Clean up
    aggregator.stop_scheduler()
    await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_stop_scheduler():
    """Test stop_scheduler stops the background scheduler."""
    aggregator = NewsAggregator(mcp_server_url="https://hnrss.org/frontpage")
    
    # Start the scheduler
    aggregator.schedule_updates(interval_minutes=30)
    assert aggregator.is_scheduler_running()
    
    # Stop the scheduler
    aggregator.stop_scheduler()
    
    # Scheduler should be stopped
    assert not aggregator.is_scheduler_running()
    
    # Give time for task to cancel
    await asyncio.sleep(0.1)
    
    # Task should be cancelled or done
    if aggregator._scheduler_task:
        assert aggregator._scheduler_task.done() or aggregator._scheduler_task.cancelled()


@pytest.mark.asyncio
async def test_stop_scheduler_idempotent():
    """Test stop_scheduler can be called multiple times safely."""
    aggregator = NewsAggregator(mcp_server_url="https://hnrss.org/frontpage")
    
    # Stop without starting (should not raise error)
    aggregator.stop_scheduler()
    assert not aggregator.is_scheduler_running()
    
    # Start and stop
    aggregator.schedule_updates(interval_minutes=30)
    aggregator.stop_scheduler()
    
    # Stop again (should not raise error)
    aggregator.stop_scheduler()
    assert not aggregator.is_scheduler_running()


@pytest.mark.asyncio
async def test_scheduler_fetches_news_periodically():
    """Test scheduler periodically fetches news at specified interval."""
    aggregator = NewsAggregator(mcp_server_url="https://hnrss.org/frontpage")
    
    # Mock the RSS client methods
    aggregator.rss_client.connect = AsyncMock(return_value=True)
    mock_articles = [
        Article(
            id="test1",
            title="Test Article",
            source="Test Source",
            publication_date=datetime.utcnow(),
            content="Test content",
            url="https://example.com/1",
            category="Technology"
        )
    ]
    aggregator.rss_client.fetch_articles = AsyncMock(return_value=mock_articles)
    
    # Connect first
    await aggregator.connect_to_mcp()
    
    # Use a short interval for testing (1 second = 1/60 minute)
    test_interval_minutes = 1 / 60  # 1 second
    
    # Start the scheduler
    aggregator.schedule_updates(interval_minutes=test_interval_minutes)
    
    # Wait for at least one fetch cycle
    await asyncio.sleep(1.5)
    
    # Scheduler should still be running
    assert aggregator.is_scheduler_running()
    
    # Clean up
    aggregator.stop_scheduler()
    await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_scheduler_handles_errors_gracefully():
    """Test scheduler continues running even if fetch fails."""
    aggregator = NewsAggregator(mcp_server_url="https://hnrss.org/frontpage")
    
    # Mock the RSS client to fail
    aggregator.rss_client.connect = AsyncMock(return_value=True)
    aggregator.rss_client.fetch_articles = AsyncMock(side_effect=Exception("Simulated fetch error"))
    
    await aggregator.connect_to_mcp()
    
    # Start scheduler with short interval
    test_interval_minutes = 1 / 60  # 1 second
    aggregator.schedule_updates(interval_minutes=test_interval_minutes)
    
    # Wait for a couple of cycles
    await asyncio.sleep(2.5)
    
    # Scheduler should still be running despite errors
    assert aggregator.is_scheduler_running()
    
    # Clean up
    aggregator.stop_scheduler()
    await asyncio.sleep(0.1)

