"""
Unit tests for AI Summarizer component.

This module tests the AISummarizer class including summarization,
batch processing, key facts extraction, and error handling.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from app.components.ai_summarizer import AISummarizer
from app.models.data_models import Article, Summary


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_article():
    """Create a sample article for testing."""
    return Article(
        id="test-123",
        title="President Announces New Climate Policy",
        source="Test News",
        publication_date=datetime.utcnow(),
        content=(
            "President Jane Smith announced a new climate policy on Monday in Washington, D.C. "
            "The policy aims to reduce carbon emissions by 50% by 2030. "
            "The announcement was made because of increasing concerns about climate change. "
            "Scientists have warned that immediate action is necessary to prevent catastrophic "
            "environmental damage. The new policy includes investments in renewable energy, "
            "stricter regulations on industrial emissions, and incentives for electric vehicles."
        ),
        url="https://example.com/article",
        category="Politics"
    )


@pytest.fixture
def mock_hf_response():
    """Mock HuggingFace API response."""
    return [
        {
            "summary_text": (
                "President Jane Smith announced a new climate policy on Monday in Washington, D.C. "
                "The policy aims to reduce carbon emissions by 50% by 2030 through investments in "
                "renewable energy, stricter industrial regulations, and electric vehicle incentives. "
                "The announcement addresses increasing concerns about climate change and warnings "
                "from scientists about the need for immediate action to prevent environmental damage."
            )
        }
    ]


@pytest.fixture
def ai_summarizer():
    """Create AISummarizer instance with test configuration."""
    config = {
        "model": "facebook/bart-large-cnn",
        "timeout": 5
    }
    return AISummarizer(agno_config=config, hf_token="test-token")


# ============================================================================
# Initialization Tests
# ============================================================================

def test_ai_summarizer_initialization():
    """Test AISummarizer initializes with correct configuration."""
    config = {"model": "facebook/bart-large-cnn"}
    summarizer = AISummarizer(agno_config=config, hf_token="test-token")
    
    assert summarizer.agno_config == config
    assert summarizer.hf_token == "test-token"
    assert summarizer.model_name == "facebook/bart-large-cnn"
    assert summarizer.timeout_seconds == 5
    assert summarizer.min_words == 50
    assert summarizer.max_words == 150


# ============================================================================
# Summarization Tests
# ============================================================================

@pytest.mark.asyncio
async def test_summarize_article_success(ai_summarizer, sample_article, mock_hf_response):
    """Test successful article summarization."""
    # Mock the HuggingFace API call
    with patch.object(ai_summarizer, '_call_huggingface', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_hf_response[0]["summary_text"]
        
        summary = await ai_summarizer.summarize_article(sample_article)
        
        # Verify summary structure
        assert isinstance(summary, Summary)
        assert summary.article_id == sample_article.id
        assert summary.title == sample_article.title
        assert summary.source == sample_article.source
        assert summary.category == sample_article.category
        
        # Verify word count constraint
        word_count = len(summary.summary_text.split())
        assert 50 <= word_count <= 150
        
        # Verify key facts extracted
        assert isinstance(summary.key_facts, dict)
        assert "who" in summary.key_facts
        assert "what" in summary.key_facts
        assert "when" in summary.key_facts
        assert "where" in summary.key_facts
        assert "why" in summary.key_facts


@pytest.mark.asyncio
async def test_summarize_article_timeout(ai_summarizer, sample_article):
    """Test summarization timeout handling."""
    # Mock timeout
    with patch.object(ai_summarizer, '_call_huggingface', new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = asyncio.TimeoutError()
        
        summary = await ai_summarizer.summarize_article(sample_article)
        
        # Verify fallback summary created
        assert isinstance(summary, Summary)
        assert "Summary unavailable" in summary.summary_text
        assert summary.article_id == sample_article.id


@pytest.mark.asyncio
async def test_summarize_article_api_error(ai_summarizer, sample_article):
    """Test summarization API error handling."""
    # Mock API error
    with patch.object(ai_summarizer, '_call_huggingface', new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = Exception("API Error")
        
        summary = await ai_summarizer.summarize_article(sample_article)
        
        # Verify fallback summary created
        assert isinstance(summary, Summary)
        assert "Summary unavailable" in summary.summary_text


# ============================================================================
# Word Count Enforcement Tests
# ============================================================================

def test_enforce_word_count_within_limits(ai_summarizer):
    """Test word count enforcement when text is within limits."""
    text = " ".join(["word"] * 100)  # 100 words
    result = ai_summarizer._enforce_word_count(text)
    assert len(result.split()) == 100


def test_enforce_word_count_too_long(ai_summarizer):
    """Test word count enforcement when text exceeds maximum."""
    text = " ".join(["word"] * 200)  # 200 words
    result = ai_summarizer._enforce_word_count(text)
    word_count = len(result.split())
    assert word_count <= 150


def test_enforce_word_count_too_short(ai_summarizer):
    """Test word count enforcement when text is below minimum."""
    text = " ".join(["word"] * 30)  # 30 words
    result = ai_summarizer._enforce_word_count(text)
    # Should return as-is (padding handled elsewhere)
    assert len(result.split()) == 30


# ============================================================================
# Key Facts Extraction Tests
# ============================================================================

def test_extract_key_facts_who(ai_summarizer):
    """Test extraction of 'who' key fact."""
    text = "President Jane Smith announced a new policy today."
    summary = "Jane Smith announced a policy."
    
    facts = ai_summarizer._extract_key_facts(text, summary)
    
    assert facts["who"] is not None
    assert "Jane Smith" in facts["who"] or "Smith" in facts["who"]


def test_extract_key_facts_when(ai_summarizer):
    """Test extraction of 'when' key fact."""
    text = "The event occurred on Monday, January 15, 2024."
    summary = "Event on Monday."
    
    facts = ai_summarizer._extract_key_facts(text, summary)
    
    assert facts["when"] is not None


def test_extract_key_facts_where(ai_summarizer):
    """Test extraction of 'where' key fact."""
    text = "The announcement was made in Washington, D.C. at the White House."
    summary = "Announcement in Washington."
    
    facts = ai_summarizer._extract_key_facts(text, summary)
    
    assert facts["where"] is not None


def test_extract_key_facts_why(ai_summarizer):
    """Test extraction of 'why' key fact."""
    text = "The policy was implemented because of increasing environmental concerns."
    summary = "Policy due to environmental concerns."
    
    facts = ai_summarizer._extract_key_facts(text, summary)
    
    assert facts["why"] is not None


# ============================================================================
# Batch Processing Tests
# ============================================================================

@pytest.mark.asyncio
async def test_batch_summarize_success(ai_summarizer, sample_article, mock_hf_response):
    """Test successful batch summarization."""
    articles = [sample_article for _ in range(5)]
    
    with patch.object(ai_summarizer, '_call_huggingface', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_hf_response[0]["summary_text"]
        
        summaries = await ai_summarizer.batch_summarize(articles)
        
        assert len(summaries) == 5
        assert all(isinstance(s, Summary) for s in summaries)
        assert mock_call.call_count == 5


@pytest.mark.asyncio
async def test_batch_summarize_empty_list(ai_summarizer):
    """Test batch summarization with empty article list."""
    summaries = await ai_summarizer.batch_summarize([])
    assert summaries == []


@pytest.mark.asyncio
async def test_batch_summarize_concurrency_limit(ai_summarizer, sample_article, mock_hf_response):
    """Test batch summarization respects concurrency limit."""
    # Create 60 articles (more than the 50 limit)
    articles = [sample_article for _ in range(60)]
    
    with patch.object(ai_summarizer, '_call_huggingface', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_hf_response[0]["summary_text"]
        
        summaries = await ai_summarizer.batch_summarize(articles)
        
        # Should still process all articles
        assert len(summaries) == 60
        assert all(isinstance(s, Summary) for s in summaries)


@pytest.mark.asyncio
async def test_batch_summarize_partial_failures(ai_summarizer, sample_article, mock_hf_response):
    """Test batch summarization handles partial failures."""
    articles = [sample_article for _ in range(5)]
    
    # Mock some successes and some failures
    call_count = 0
    async def mock_call_with_failures(text):
        nonlocal call_count
        call_count += 1
        if call_count % 2 == 0:
            raise Exception("API Error")
        return mock_hf_response[0]["summary_text"]
    
    with patch.object(ai_summarizer, '_call_huggingface', new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = mock_call_with_failures
        
        summaries = await ai_summarizer.batch_summarize(articles)
        
        # Should return summaries for all articles (with fallbacks for failures)
        assert len(summaries) == 5
        assert all(isinstance(s, Summary) for s in summaries)


# ============================================================================
# Fallback Summary Tests
# ============================================================================

def test_create_fallback_summary(ai_summarizer, sample_article):
    """Test fallback summary creation."""
    summary = ai_summarizer._create_fallback_summary(sample_article)
    
    assert isinstance(summary, Summary)
    assert summary.article_id == sample_article.id
    assert summary.title == sample_article.title
    assert "Summary unavailable" in summary.summary_text
    
    # Verify word count meets minimum
    word_count = len(summary.summary_text.split())
    assert word_count >= 50


# ============================================================================
# HuggingFace API Tests
# ============================================================================

@pytest.mark.asyncio
async def test_call_huggingface_success(ai_summarizer, mock_hf_response):
    """Test successful HuggingFace API call."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_hf_response
    
    with patch.object(ai_summarizer.hf_client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await ai_summarizer._call_huggingface("Test content")
        
        assert result == mock_hf_response[0]["summary_text"]
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_call_huggingface_rate_limit(ai_summarizer, mock_hf_response):
    """Test HuggingFace API rate limit handling."""
    # First response: rate limited
    rate_limit_response = Mock()
    rate_limit_response.status_code = 429
    rate_limit_response.headers = {"Retry-After": "1"}
    
    # Second response: success
    success_response = Mock()
    success_response.status_code = 200
    success_response.json.return_value = mock_hf_response
    
    with patch.object(ai_summarizer.hf_client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [rate_limit_response, success_response]
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await ai_summarizer._call_huggingface("Test content")
            
            assert result == mock_hf_response[0]["summary_text"]
            assert mock_post.call_count == 2
            mock_sleep.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_call_huggingface_error(ai_summarizer):
    """Test HuggingFace API error handling."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = Exception("Server Error")
    
    with patch.object(ai_summarizer.hf_client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        with pytest.raises(Exception):
            await ai_summarizer._call_huggingface("Test content")


# ============================================================================
# Cleanup Tests
# ============================================================================

@pytest.mark.asyncio
async def test_close(ai_summarizer):
    """Test cleanup of resources."""
    with patch.object(ai_summarizer.hf_client, 'aclose', new_callable=AsyncMock) as mock_close:
        await ai_summarizer.close()
        mock_close.assert_called_once()
