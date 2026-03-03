# Implementation Plan: AI News Summarizer

## Overview

This implementation plan breaks down the AI News Summarizer into discrete coding tasks. The application uses Python with FastAPI for the backend, Agno framework for AI orchestration, HuggingFace for summarization, and a responsive HTML/CSS/JavaScript frontend. Each task builds incrementally toward a fully functional containerized application deployable to Railway or Render.

## Tasks

- [x] 1. Set up project structure and core dependencies
  - Create directory structure: `app/`, `app/models/`, `app/components/`, `app/static/`, `tests/`
  - Create `requirements.txt` with FastAPI, Pydantic, Agno, HuggingFace Transformers, Hypothesis, pytest
  - Create `pyproject.toml` for project metadata
  - Create `.env.example` template with required environment variables
  - _Requirements: 4.2, 5.5, 7.1, 7.2, 7.3, 7.4_

- [x] 2. Implement data models with validation
  - [x] 2.1 Create Pydantic models for Article, Summary, SummaryResponse, CacheEntry, ErrorLog, UserError, and AppConfig
    - Write models in `app/models/data_models.py` with field validation
    - Implement datetime JSON encoders
    - Add validators for required fields and constraints
    - _Requirements: 1.3, 2.3, 7.5, 7.6, 8.1_

  - [ ]* 2.2 Write property test for Article metadata completeness
    - **Property 2: Article Metadata Completeness**
    - **Validates: Requirements 1.3**

  - [ ]* 2.3 Write property test for Summary word count constraint
    - **Property 3: Summary Word Count Constraint**
    - **Validates: Requirements 2.3**

  - [ ]* 2.4 Write property test for configuration validation
    - **Property 8: Configuration Environment Variable Support**
    - **Validates: Requirements 4.4, 7.1, 7.5, 7.6**

- [x] 3. Implement configuration management
  - [x] 3.1 Create AppConfig class with environment variable loading
    - Write `app/config.py` using Pydantic BaseSettings
    - Implement validation for required variables (HUGGINGFACE_TOKEN, MCP_SERVER_URL)
    - Add default values for optional settings (PORT=8080, CACHE_TTL_MINUTES=30, etc.)
    - Implement fail-fast validation with descriptive error messages
    - _Requirements: 4.3, 4.4, 4.5, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [ ]* 3.2 Write unit tests for configuration validation edge cases
    - Test missing required variables
    - Test invalid formats (non-numeric port, invalid URLs)
    - Test default value application
    - _Requirements: 7.5, 7.6_

- [x] 4. Implement cache layer component
  - [x] 4.1 Create CacheManager class with TTL support
    - Write `app/components/cache.py` with in-memory storage
    - Implement get(), set(), invalidate(), and is_expired() methods
    - Add thread-safe operations using asyncio locks
    - Implement automatic expiration checking
    - _Requirements: 9.2, 9.3_

  - [ ]* 4.2 Write unit tests for cache expiration and cleanup
    - Test TTL expiration logic
    - Test cache invalidation
    - Test concurrent access scenarios
    - _Requirements: 9.2, 9.3_

- [x] 5. Implement News Aggregator component
  - [x] 5.1 Create NewsAggregator class with MCP Server integration
    - Write `app/components/news_aggregator.py`
    - Implement __init__() with MCP server URL configuration
    - Implement connect_to_mcp() with retry logic (60-second delay)
    - Implement fetch_latest_news() to retrieve articles from last 24 hours
    - Add article metadata normalization (title, source, date, content)
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 5.2 Implement background scheduler for periodic news fetching
    - Add schedule_updates() method using asyncio tasks
    - Configure 30-minute refresh interval
    - _Requirements: 1.5, 9.1_

  - [ ]* 5.3 Write property test for 24-hour article filtering
    - **Property 1: 24-Hour Article Filtering**
    - **Validates: Requirements 1.2**

  - [ ]* 5.4 Write unit tests for MCP connection retry logic
    - Test connection failure and retry behavior
    - Test retry delay timing
    - Mock MCP server responses
    - _Requirements: 1.4_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement AI Summarizer component
  - [x] 7.1 Create AISummarizer class with Agno and HuggingFace integration
    - Write `app/components/ai_summarizer.py`
    - Implement __init__() with Agno configuration and HuggingFace token
    - Implement summarize_article() using facebook/bart-large-cnn model
    - Enforce 50-150 word summary length constraint
    - Add 5-second timeout per article
    - Implement fallback message on summarization failure
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 2.6_

  - [x] 7.2 Implement batch processing with concurrency control
    - Implement batch_summarize() for processing up to 50 articles concurrently
    - Add asyncio semaphore for concurrency limiting
    - _Requirements: 2.6, 10.2_

  - [x] 7.3 Implement key facts extraction and validation
    - Implement _extract_key_facts() to identify who, what, when, where, why
    - Add validation to ensure key facts are preserved in summaries
    - _Requirements: 2.4_

  - [ ]* 7.4 Write property test for summary processing time
    - **Property 5: Summary Processing Time**
    - **Validates: Requirements 2.6**

  - [ ]* 7.5 Write property test for key facts preservation
    - **Property 4: Key Facts Preservation**
    - **Validates: Requirements 2.4**

  - [ ]* 7.6 Write unit tests for summarization error handling
    - Test timeout scenarios
    - Test API rate limiting with exponential backoff
    - Test fallback message generation
    - _Requirements: 2.5, 8.4_

- [x] 8. Implement error handling and logging infrastructure
  - [x] 8.1 Create structured logging system
    - Write `app/utils/logging.py` with JSON log formatting
    - Implement log levels (INFO, WARNING, ERROR, CRITICAL)
    - Configure logging to stdout for container compatibility
    - Add component name and timestamp to all log entries
    - _Requirements: 8.1, 8.2, 8.3, 8.6_

  - [x] 8.2 Implement error handling utilities
    - Create error handler decorators for components
    - Implement exponential backoff for rate limiting
    - Add user-friendly error message generation
    - _Requirements: 8.4, 8.5_

  - [ ]* 8.3 Write property test for error log structure
    - **Property 9: Error Log Structure**
    - **Validates: Requirements 8.1, 8.3**

  - [ ]* 8.4 Write property test for user error message safety
    - **Property 10: User Error Message Safety**
    - **Validates: Requirements 8.5**

- [x] 9. Implement FastAPI backend with REST endpoints
  - [x] 9.1 Create FastAPI application with core endpoints
    - Write `app/main.py` with FastAPI app initialization
    - Implement GET / endpoint to serve HTML page
    - Implement GET /api/summaries endpoint returning list of SummaryResponse
    - Implement GET /api/health endpoint for platform health checks
    - Wire together NewsAggregator, AISummarizer, and CacheManager
    - _Requirements: 3.1, 6.6, 6.7_

  - [x] 9.2 Implement caching logic in API endpoints
    - Add cache check in /api/summaries endpoint
    - Return cached summaries if available and not expired
    - Fetch and process new articles on cache miss
    - Store generated summaries in cache with 30-minute TTL
    - _Requirements: 9.2, 9.3_

  - [x] 9.3 Implement article sorting and display logic
    - Sort articles by publication date (newest first)
    - Add last update timestamp to responses
    - _Requirements: 9.4, 9.5_

  - [ ]* 9.4 Write property test for article display ordering
    - **Property 11: Article Display Ordering**
    - **Validates: Requirements 9.5**

  - [ ]* 9.5 Write integration tests for full news pipeline
    - Test end-to-end flow from fetching to API response
    - Mock MCP Server and HuggingFace API
    - Verify cache behavior
    - _Requirements: 1.1, 2.1, 9.2_

- [x] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Implement responsive web interface
  - [x] 11.1 Create HTML structure with card-based layout
    - Write `app/static/index.html` with semantic HTML5
    - Create card structure for news summaries
    - Add metadata display (source, timestamp, category)
    - Include last update timestamp display
    - _Requirements: 3.1, 3.6, 9.4_

  - [x] 11.2 Create CSS styling with Tailwind CSS
    - Write `app/static/styles.css` or use Tailwind CDN
    - Implement responsive design for 320px-2560px viewports
    - Add card hover effects
    - Implement color coding by news category
    - Create typography hierarchy for readability
    - Add category icons
    - _Requirements: 3.2, 3.3, 3.4_

  - [x] 11.3 Create JavaScript for dynamic content loading
    - Write `app/static/app.js` to fetch from /api/summaries
    - Implement DOM manipulation to render summary cards
    - Add error handling with user-friendly messages
    - Optimize for 3-second load time
    - _Requirements: 3.5, 8.5_

  - [ ]* 11.4 Write property test for responsive layout integrity
    - **Property 6: Responsive Layout Integrity**
    - **Validates: Requirements 3.3**

  - [ ]* 11.5 Write property test for summary display metadata completeness
    - **Property 7: Summary Display Metadata Completeness**
    - **Validates: Requirements 3.6**

- [x] 12. Implement Docker containerization
  - [x] 12.1 Create Dockerfile with multi-stage build
    - Write `Dockerfile` in repository root
    - Use Python 3.11 slim base image
    - Install dependencies from requirements.txt
    - Copy application code
    - Expose configurable port (default 8080)
    - Set CMD to run FastAPI with uvicorn
    - Optimize for image size <1GB
    - _Requirements: 4.1, 4.2, 4.3, 4.6_

  - [x] 12.2 Create docker-compose.yml for local development
    - Write `docker-compose.yml` with service definition
    - Mount environment variables from .env file
    - Configure port mapping
    - _Requirements: 5.4_

  - [ ]* 12.3 Write unit test to verify Docker image size
    - Test that built image is under 1GB
    - _Requirements: 4.6_

- [x] 13. Create deployment configuration files
  - [x] 13.1 Create Railway deployment configuration
    - Write `railway.json` with service configuration
    - Configure health check endpoint (/api/health)
    - Set environment variable requirements
    - Configure automatic deployments from main branch
    - _Requirements: 6.1, 6.3, 6.5, 6.6_

  - [x] 13.2 Create Render deployment configuration
    - Write `render.yaml` with service configuration
    - Configure health check endpoint (/api/health)
    - Set environment variable requirements
    - Configure automatic deployments from main branch
    - _Requirements: 6.2, 6.3, 6.5, 6.7_

  - [x] 13.3 Verify container startup time
    - Test that application starts within 60 seconds
    - Add startup logging for debugging
    - _Requirements: 6.4_

- [x] 14. Create repository documentation and configuration
  - [x] 14.1 Create comprehensive README.md
    - Write `README.md` with project overview
    - Add setup instructions (local and Docker)
    - Document environment variables
    - Add deployment instructions for Railway and Render
    - Include usage examples
    - _Requirements: 5.2_

  - [x] 14.2 Create .gitignore file
    - Write `.gitignore` excluding .env, __pycache__, venv, .pytest_cache
    - Exclude Docker volumes and logs
    - _Requirements: 5.3_

  - [x] 14.3 Create .env.example template
    - Document all required environment variables
    - Provide example values (non-sensitive)
    - _Requirements: 5.5_

- [x] 15. Implement performance optimizations
  - [x] 15.1 Add request queuing for load management
    - Implement request queue with 200-item limit
    - Add 30-second timeout for queued requests
    - Return 503 with Retry-After header when queue is full
    - _Requirements: 10.5_

  - [x] 15.2 Add memory monitoring and cache cleanup
    - Implement memory usage tracking
    - Trigger cache cleanup at 450MB (LRU eviction)
    - Reject requests with 503 when exceeding 512MB
    - Add WARNING logs at 400MB, ERROR logs at 480MB
    - _Requirements: 10.4_

  - [ ]* 15.3 Write performance tests for concurrent load
    - Test 100 concurrent users
    - Verify response times <3 seconds
    - Verify memory stays <512MB
    - _Requirements: 10.1, 10.3, 10.4_

- [x] 16. Final checkpoint - Ensure all tests pass and application is ready for deployment
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Integration tests verify end-to-end workflows
- The implementation uses Python with FastAPI, Agno, HuggingFace, and Hypothesis for property-based testing
- All components are designed for Docker containerization and deployment to Railway or Render
