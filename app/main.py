"""
FastAPI application for AI News Summarizer.

This module implements the main FastAPI application with REST endpoints
for serving news summaries, health checks, and the web interface.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import config
from app.components.cache import CacheManager
from app.components.news_aggregator import NewsAggregator
from app.components.ai_summarizer import AISummarizer
from app.models.data_models import SummaryResponse, UserError
from app.utils.logging import configure_root_logger, get_logger
from app.utils.error_handling import generate_user_friendly_message


# Configure logging
configure_root_logger(config.log_level)
logger = get_logger("main")


# ============================================================================
# Application State
# ============================================================================

class AppState:
    """Application state container for shared components."""
    
    def __init__(self):
        self.cache_manager: CacheManager = None
        self.news_aggregator: NewsAggregator = None
        self.ai_summarizer: AISummarizer = None
        self.last_update: datetime = None


app_state = AppState()


# ============================================================================
# Lifespan Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup and shutdown).
    
    This context manager initializes all components on startup and
    cleans up resources on shutdown.
    """
    # Startup
    logger.info("Starting AI News Summarizer application")
    logger.info(f"Configuration: port={config.port}, cache_ttl={config.cache_ttl_minutes}min")
    
    try:
        # Initialize components
        logger.info("Initializing components...")
        
        # Initialize cache manager
        app_state.cache_manager = CacheManager(ttl_minutes=config.cache_ttl_minutes)
        logger.info("Cache manager initialized")
        
        # Initialize news aggregator
        app_state.news_aggregator = NewsAggregator(
            mcp_server_url=config.mcp_server_url,
            retry_delay=60
        )
        logger.info("News aggregator initialized")
        
        # Connect to RSS feeds
        connected = await app_state.news_aggregator.connect_to_mcp()
        if not connected:
            logger.warning("Failed to connect to RSS feeds on startup")
        
        # Initialize AI summarizer
        agno_config = {
            "model": "facebook/bart-large-cnn",
            "timeout": 5
        }
        app_state.ai_summarizer = AISummarizer(
            agno_config=agno_config,
            hf_token=config.huggingface_token
        )
        logger.info("AI summarizer initialized")
        
        # Schedule periodic news updates
        app_state.news_aggregator.schedule_updates(
            interval_minutes=config.news_refresh_minutes
        )
        logger.info(f"Scheduled news updates every {config.news_refresh_minutes} minutes")
        
        logger.info("Application startup complete")
        
        yield
        
    finally:
        # Shutdown
        logger.info("Shutting down application...")
        
        # Stop background scheduler
        if app_state.news_aggregator:
            app_state.news_aggregator.stop_scheduler()
            logger.info("News aggregator scheduler stopped")
        
        # Close AI summarizer
        if app_state.ai_summarizer:
            await app_state.ai_summarizer.close()
            logger.info("AI summarizer closed")
        
        logger.info("Application shutdown complete")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="AI News Summarizer",
    description="AI-powered news aggregation and summarization service",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve main HTML page.
    
    Returns:
        HTML content for the web interface
    """
    try:
        # Read HTML file from static directory
        with open("app/static/index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        logger.error("index.html not found in app/static/")
        return HTMLResponse(
            content="<h1>AI News Summarizer</h1><p>Web interface not available</p>",
            status_code=200
        )


@app.get("/api/summaries", response_model=List[SummaryResponse])
async def get_summaries():
    """Get list of news summaries with caching.
    
    This endpoint checks the cache first. If cached summaries are available
    and not expired, they are returned immediately. Otherwise, it fetches
    new articles, generates summaries, and caches the results.
    
    Returns:
        List of SummaryResponse objects with news summaries
        
    Raises:
        HTTPException: If unable to fetch or process news
    """
    try:
        logger.info("GET /api/summaries - Request received")
        
        # Check cache first
        cache_key = "news_summaries"
        cached_summaries = await app_state.cache_manager.get(cache_key)
        
        if cached_summaries is not None:
            logger.info("Cache hit - returning cached summaries")
            return cached_summaries
        
        logger.info("Cache miss - fetching and processing new articles")
        
        # Fetch latest news articles
        try:
            articles = await app_state.news_aggregator.fetch_latest_news(hours=24)
            logger.info(f"Fetched {len(articles)} articles")
        except Exception as e:
            logger.error(f"Failed to fetch articles: {e}", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail=generate_user_friendly_message(e, "loading news")
            )
        
        if not articles:
            logger.warning("No articles fetched")
            return []
        
        # Generate summaries using AI
        try:
            summaries = await app_state.ai_summarizer.batch_summarize(articles)
            logger.info(f"Generated {len(summaries)} summaries")
        except Exception as e:
            logger.error(f"Failed to generate summaries: {e}", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail=generate_user_friendly_message(e, "generating summaries")
            )
        
        # Sort articles by publication date (newest first)
        summaries.sort(key=lambda s: s.publication_date, reverse=True)
        
        # Convert to response format
        current_time = datetime.utcnow()
        app_state.last_update = current_time
        
        summary_responses = []
        for summary in summaries:
            # Format publication date as human-readable
            time_diff = current_time - summary.publication_date
            if time_diff.days > 0:
                published_str = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
            elif time_diff.seconds >= 3600:
                hours = time_diff.seconds // 3600
                published_str = f"{hours} hour{'s' if hours > 1 else ''} ago"
            else:
                minutes = time_diff.seconds // 60
                published_str = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            
            response = SummaryResponse(
                id=summary.article_id,
                title=summary.title,
                summary=summary.summary_text,
                source=summary.source,
                published=published_str,
                category=summary.category or "General",
                timestamp=summary.publication_date,
                last_updated=current_time
            )
            summary_responses.append(response)
        
        # Cache the results with 30-minute TTL
        await app_state.cache_manager.set(
            cache_key,
            summary_responses,
            ttl=config.cache_ttl_minutes * 60
        )
        logger.info(f"Cached {len(summary_responses)} summaries with {config.cache_ttl_minutes}min TTL")
        
        return summary_responses
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Unexpected error in /api/summaries: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Unable to load news summaries. Please try again in a moment."
        )


@app.get("/api/health")
async def health_check():
    """Health check endpoint for deployment platforms.
    
    This endpoint verifies that the application is running and all
    components are initialized. Used by Railway and Render for
    health monitoring.
    
    Returns:
        JSON response with health status
    """
    try:
        # Check if components are initialized
        components_status = {
            "cache_manager": app_state.cache_manager is not None,
            "news_aggregator": app_state.news_aggregator is not None,
            "ai_summarizer": app_state.ai_summarizer is not None,
        }
        
        # Check if news aggregator is connected
        if app_state.news_aggregator:
            components_status["rss_connected"] = app_state.news_aggregator.connected
        
        # Overall health status
        all_healthy = all(components_status.values())
        
        response = {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "components": components_status,
            "last_update": app_state.last_update.isoformat() if app_state.last_update else None
        }
        
        status_code = 200 if all_healthy else 503
        
        return JSONResponse(content=response, status_code=status_code)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return JSONResponse(
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Health check failed"
            },
            status_code=503
        )


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with user-friendly messages.
    
    Args:
        request: Request object
        exc: HTTPException
        
    Returns:
        JSON response with error details
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "code": exc.status_code
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions.
    
    Args:
        request: Request object
        exc: Exception
        
    Returns:
        JSON response with generic error message
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "An unexpected error occurred. Please try again in a moment.",
                "code": 500
            }
        }
    )


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.environ.get("PORT", config.port))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level=config.log_level.lower()
    )
