"""
News Aggregator component for fetching articles from RSS feeds.

This module implements the NewsAggregator class that connects to real RSS feeds,
retrieves news articles, and normalizes article metadata. It uses feedparser to
parse RSS/Atom feeds from multiple sources.
"""

import asyncio
import logging
import hashlib
from datetime import datetime, timedelta
from typing import List
import feedparser
import httpx
from app.models.data_models import Article


logger = logging.getLogger(__name__)


# ============================================================================
# RSS Feed Client
# ============================================================================

class RSSFeedClient:
    """RSS Feed client for fetching articles from RSS/Atom feeds.
    
    This implementation uses feedparser to parse real RSS feeds from
    multiple sources like Hacker News, TechCrunch, The Verge, NYTimes, etc.
    """
    
    def __init__(self, feed_urls: List[str]):
        """Initialize RSS Feed client.
        
        Args:
            feed_urls: List of RSS feed URLs to fetch from
        """
        self.feed_urls = feed_urls
        self.connected = False
        logger.info(f"RSSFeedClient initialized with {len(feed_urls)} feeds")
    
    async def connect(self) -> bool:
        """Verify RSS feeds are accessible, with detailed logging for each URL."""
        if not self.feed_urls:
            logger.error("No RSS feed URLs configured")
            return False

        at_least_one_success = False
        async with httpx.AsyncClient(timeout=10.0) as client:
            for url in self.feed_urls:
                try:
                    logger.info(f"[RSSFeedClient] Attempting to connect to: {url}")
                    response = await client.get(url)
                    if response.status_code == 200:
                        logger.info(f"[RSSFeedClient] Successfully connected to: {url}")
                        at_least_one_success = True
                    else:
                        logger.error(f"[RSSFeedClient] Failed to connect to {url}: Status {response.status_code}")
                except Exception as e:
                    logger.error(f"[RSSFeedClient] Exception connecting to {url}: {str(e)}")
        self.connected = at_least_one_success
        return at_least_one_success
    
    async def fetch_articles(self, hours: int = 24) -> List[Article]:
        """Fetch articles from all configured RSS feeds.
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            List[Article]: List of articles from all feeds
        """
        if not self.connected:
            raise ConnectionError("RSS client not connected")
        
        all_articles = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Fetch from each feed
        for feed_url in self.feed_urls:
            try:
                logger.info(f"Fetching feed: {feed_url}")
                
                # Fetch feed content
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(feed_url)
                    response.raise_for_status()
                    
                # Parse feed
                feed = feedparser.parse(response.text)
                
                # Extract feed source name
                feed_source = feed.feed.get('title', 'Unknown Source')
                
                # Process entries
                for entry in feed.entries:
                    try:
                        # Parse publication date
                        pub_date = None
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            pub_date = datetime(*entry.published_parsed[:6])
                        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                            pub_date = datetime(*entry.updated_parsed[:6])
                        else:
                            # If no date, use current time
                            pub_date = datetime.utcnow()
                        
                        # Skip if too old
                        if pub_date < cutoff_time:
                            continue
                        
                        # Extract content
                        content = ""
                        if hasattr(entry, 'summary'):
                            content = entry.summary
                        elif hasattr(entry, 'description'):
                            content = entry.description
                        elif hasattr(entry, 'content'):
                            content = entry.content[0].value if entry.content else ""
                        
                        # Clean HTML tags from content
                        import re
                        content = re.sub(r'<[^>]+>', '', content)
                        content = content.strip()
                        
                        # Skip if no content
                        if not content or len(content) < 50:
                            continue
                        
                        # Generate unique ID from URL
                        article_id = hashlib.md5(entry.link.encode()).hexdigest()[:16]
                        
                        # Determine category from feed or tags
                        category = None
                        if hasattr(entry, 'tags') and entry.tags:
                            category = entry.tags[0].term
                        elif 'tech' in feed_url.lower():
                            category = "Technology"
                        elif 'business' in feed_url.lower():
                            category = "Business"
                        elif 'science' in feed_url.lower():
                            category = "Science"
                        else:
                            category = "General"
                        
                        # Create Article object
                        article = Article(
                            id=article_id,
                            title=entry.title.strip(),
                            source=feed_source,
                            publication_date=pub_date,
                            content=content,
                            url=entry.link,
                            category=category
                        )
                        
                        all_articles.append(article)
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse entry from {feed_url}: {str(e)}")
                        continue
                
                logger.info(f"Fetched {len(feed.entries)} entries from {feed_source}")
                
            except Exception as e:
                logger.error(f"Failed to fetch feed {feed_url}: {str(e)}")
                continue
        
        logger.info(f"Total articles fetched: {len(all_articles)}")
        return all_articles


# ============================================================================
# News Aggregator Component
# ============================================================================

class NewsAggregator:
    """News Aggregator component for fetching and normalizing articles.
    
    This class manages connections to RSS feeds, retrieves news articles,
    and ensures all article metadata is properly normalized. It implements
    retry logic for connection failures and filters articles by time window.
    """
    
    def __init__(
        self,
        mcp_server_url: str,
        retry_delay: int = 60
    ):
        """Initialize NewsAggregator with RSS feed configuration.
        
        Args:
            mcp_server_url: Comma-separated list of RSS feed URLs
            retry_delay: Delay in seconds between connection retry attempts (default: 60)
        """
        self.mcp_server_url = mcp_server_url
        self.retry_delay = retry_delay
        
        # Parse feed URLs (comma-separated)
        self.feed_urls = [url.strip() for url in mcp_server_url.split(',') if url.strip()]
        
        # Initialize RSS client
        self.rss_client = RSSFeedClient(self.feed_urls)
        self.connected = False
        self.retry_count = 0
        
        # Background task reference for scheduled updates
        self._scheduler_task = None
        self._running = False
        
        logger.info(
            f"NewsAggregator initialized with {len(self.feed_urls)} RSS feeds, "
            f"retry_delay: {retry_delay}s"
        )
    
    async def connect_to_mcp(self) -> bool:
        """Establish connection to RSS feeds with retry logic.
        
        Implements retry logic with configurable delay on connection failures.
        Logs connection attempts and failures for debugging.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info(f"Attempting to connect to RSS feeds")
            self.connected = await self.rss_client.connect()
            
            if self.connected:
                logger.info("Successfully connected to RSS feeds")
                self.retry_count = 0
                return True
            else:
                logger.error("Failed to connect to RSS feeds")
                return False
                
        except Exception as e:
            self.retry_count += 1
            logger.error(
                f"RSS connection error (attempt {self.retry_count}): {str(e)}",
                exc_info=True
            )
            
            # Log retry information
            logger.info(f"Will retry connection after {self.retry_delay} seconds")
            await asyncio.sleep(self.retry_delay)
            
            return False
    
    async def fetch_latest_news(self, hours: int = 24) -> List[Article]:
        """Fetch articles from the last N hours.
        
        Retrieves articles from RSS feeds and ensures they are within
        the specified time window. All article metadata is normalized and
        validated through the Article model.
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            List[Article]: List of articles from the specified time period
            
        Raises:
            ConnectionError: If not connected to RSS feeds
        """
        if not self.connected:
            logger.warning("Not connected to RSS feeds, attempting to connect...")
            connected = await self.connect_to_mcp()
            if not connected:
                raise ConnectionError(
                    "Cannot fetch news: not connected to RSS feeds. "
                    f"Retry after {self.retry_delay} seconds."
                )
        
        try:
            logger.info(f"Fetching articles from last {hours} hours")
            articles = await self.rss_client.fetch_articles(hours=hours)
            
            # Filter articles to ensure they're within the time window
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            filtered_articles = [
                article for article in articles
                if article.publication_date >= cutoff_time
            ]
            
            # Sort by publication date (newest first)
            filtered_articles.sort(key=lambda x: x.publication_date, reverse=True)
            
            logger.info(
                f"Fetched {len(articles)} articles, "
                f"{len(filtered_articles)} within {hours}-hour window"
            )
            
            return filtered_articles
            
        except Exception as e:
            logger.error(f"Error fetching articles: {str(e)}", exc_info=True)
            raise
    
    def schedule_updates(self, interval_minutes: int = 30):
        """Schedule periodic news fetching.
        
        Creates a background asyncio task that calls fetch_latest_news()
        at the specified interval. The task reference is stored so it can
        be cancelled if needed. Prevents duplicate schedulers from running.
        
        Args:
            interval_minutes: Interval between updates in minutes (default: 30)
        """
        logger.info(f"Scheduling news updates every {interval_minutes} minutes")
        
        # Prevent duplicate schedulers - if already running, don't start another
        if self.is_scheduler_running():
            logger.info("Scheduler already running, not starting duplicate")
            return
        
        # Create and store the background task
        self._running = True
        self._scheduler_task = asyncio.create_task(
            self._periodic_update_loop(interval_minutes)
        )
        
        logger.info("Background scheduler started successfully")
    
    def is_scheduler_running(self) -> bool:
        """Check if the background scheduler is currently running.
        
        Returns:
            bool: True if scheduler is running, False otherwise
        """
        return (
            self._running and 
            self._scheduler_task is not None and 
            not self._scheduler_task.done()
        )
    
    async def _periodic_update_loop(self, interval_minutes: int):
        """Internal method for periodic update loop.
        
        This method runs in the background and periodically fetches news.
        It handles errors gracefully and continues running even if individual
        fetch attempts fail.
        
        Args:
            interval_minutes: Interval between updates in minutes
        """
        interval_seconds = interval_minutes * 60
        
        logger.info(f"Starting periodic update loop (interval: {interval_seconds}s)")
        
        while self._running:
            try:
                # Fetch latest news
                logger.info("Periodic update: fetching latest news")
                articles = await self.fetch_latest_news()
                logger.info(f"Periodic update: fetched {len(articles)} articles")
                
            except Exception as e:
                logger.error(f"Error during periodic update: {str(e)}", exc_info=True)
                # Continue running even if fetch fails
            
            # Wait for the next interval
            try:
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                logger.info("Periodic update loop cancelled")
                break
        
        logger.info("Periodic update loop stopped")
    
    def stop_scheduler(self):
        """Stop the background scheduler.
        
        Cancels the background task and stops periodic updates.
        This method is idempotent and can be called multiple times safely.
        """
        logger.info("Stopping background scheduler")
        self._running = False
        
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            logger.info("Background task cancelled")
        else:
            logger.info("No active background task to cancel")
