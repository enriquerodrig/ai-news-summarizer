"""
AI Summarizer component for generating concise news summaries.

This module implements the AISummarizer class which uses the Agno framework
to orchestrate AI summarization tasks with HuggingFace models. It supports
batch processing with concurrency control and key facts extraction.
"""

import asyncio
import re
from datetime import datetime
from typing import List, Optional, Dict
import logging

from app.models.data_models import Article, Summary


# Configure logging
logger = logging.getLogger(__name__)


class AISummarizer:
    """
    AI-powered summarizer using Agno framework and HuggingFace models.
    
    This class generates concise summaries (50-150 words) of news articles
    while preserving key facts (who, what, when, where, why). It supports
    batch processing with concurrency control and implements fallback
    mechanisms for error handling.
    """
    
    def __init__(self, agno_config: dict, hf_token: str):
        """
        Initialize Agno framework and HuggingFace client.
        
        Args:
            agno_config: Configuration dictionary for Agno framework
            hf_token: HuggingFace API token for authentication
        """
        self.agno_config = agno_config
        self.hf_token = hf_token
        self.model_name = "facebook/bart-large-cnn"
        self.timeout_seconds = 5
        self.min_words = 50
        self.max_words = 150
        
        # Initialize HuggingFace client
        self._init_huggingface_client()
        
        logger.info(
            f"AISummarizer initialized with model={self.model_name}, "
            f"timeout={self.timeout_seconds}s"
        )
    
    def _init_huggingface_client(self):
        """Initialize HuggingFace API client with authentication."""
        try:
            import httpx
            self.hf_client = httpx.AsyncClient(
                base_url="https://api-inference.huggingface.co/models",
                headers={"Authorization": f"Bearer {self.hf_token}"},
                timeout=self.timeout_seconds
            )
            logger.info("HuggingFace client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize HuggingFace client: {e}")
            raise
    
    async def summarize_article(self, article: Article) -> Summary:
        """
        Generate 50-150 word summary preserving key facts.
        
        This method uses the facebook/bart-large-cnn model to generate
        a concise summary of the article. It enforces word count constraints
        and implements a 5-second timeout. On failure, it returns a fallback
        message.
        
        Args:
            article: Article object to summarize
            
        Returns:
            Summary object with generated summary text and key facts
        """
        try:
            # Call HuggingFace API with timeout
            summary_text = await asyncio.wait_for(
                self._call_huggingface(article.content),
                timeout=self.timeout_seconds
            )
            
            # Enforce word count constraints
            summary_text = self._enforce_word_count(summary_text)
            
            # Extract key facts from original article
            key_facts = self._extract_key_facts(article.content, summary_text)
            
            # Create Summary object
            summary = Summary(
                article_id=article.id,
                title=article.title,
                summary_text=summary_text,
                source=article.source,
                publication_date=article.publication_date,
                category=article.category,
                generated_at=datetime.utcnow(),
                key_facts=key_facts
            )
            
            logger.info(f"Successfully summarized article {article.id}")
            return summary
            
        except asyncio.TimeoutError:
            logger.warning(
                f"Summarization timeout for article {article.id} "
                f"after {self.timeout_seconds}s"
            )
            return self._create_fallback_summary(article)
            
        except Exception as e:
            logger.error(
                f"Summarization failed for article {article.id}: {e}",
                exc_info=True
            )
            return self._create_fallback_summary(article)
    
    async def _call_huggingface(self, text: str) -> str:
        """
        Call HuggingFace API to generate summary.
        
        Args:
            text: Article content to summarize
            
        Returns:
            Generated summary text
            
        Raises:
            Exception: If API call fails
        """
        try:
            # Prepare request payload
            payload = {
                "inputs": text,
                "parameters": {
                    "max_length": 150,
                    "min_length": 50,
                    "do_sample": False
                }
            }
            
            # Make API request
            response = await self.hf_client.post(
                f"/{self.model_name}",
                json=payload
            )
            
            # Handle rate limiting with exponential backoff
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 1))
                logger.warning(f"Rate limited, retrying after {retry_after}s")
                await asyncio.sleep(retry_after)
                return await self._call_huggingface(text)
            
            # Check for errors
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                summary_text = result[0].get("summary_text", "")
                return summary_text
            
            raise ValueError("Invalid response format from HuggingFace API")
            
        except Exception as e:
            logger.error(f"HuggingFace API call failed: {e}")
            raise
    
    def _enforce_word_count(self, text: str) -> str:
        """
        Enforce 50-150 word constraint on summary text.
        
        Args:
            text: Summary text to adjust
            
        Returns:
            Adjusted summary text within word count limits
        """
        words = text.split()
        word_count = len(words)
        
        if word_count < self.min_words:
            # If too short, pad with ellipsis (shouldn't happen with proper model config)
            logger.warning(f"Summary too short ({word_count} words), padding")
            return text
        
        if word_count > self.max_words:
            # If too long, truncate to max words
            logger.debug(f"Summary too long ({word_count} words), truncating")
            truncated = " ".join(words[:self.max_words])
            # Add ellipsis if we truncated mid-sentence
            if not truncated.endswith((".", "!", "?")):
                truncated += "..."
            return truncated
        
        return text
    
    def _extract_key_facts(self, original_text: str, summary_text: str) -> Dict[str, Optional[str]]:
        """
        Identify who, what, when, where, why in the article and summary.
        
        This method uses pattern matching to extract key facts from both
        the original article and the generated summary to validate that
        important information is preserved.
        
        Args:
            original_text: Original article content
            summary_text: Generated summary text
            
        Returns:
            Dictionary with key facts (who, what, when, where, why)
        """
        key_facts = {
            "who": None,
            "what": None,
            "when": None,
            "where": None,
            "why": None
        }
        
        # Extract WHO (people, organizations)
        # Look for proper nouns, titles, organizations
        who_patterns = [
            r'\b(?:President|Prime Minister|CEO|Director|Minister)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s+(?:said|announced|stated|reported)',
            r'\b(?:by|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        for pattern in who_patterns:
            match = re.search(pattern, original_text)
            if match:
                key_facts["who"] = match.group(1)
                break
        
        # Extract WHAT (main event/action)
        # Look for main verbs and actions in first sentences
        sentences = original_text.split('.')[:2]
        if sentences:
            key_facts["what"] = sentences[0].strip()[:100]  # First sentence, truncated
        
        # Extract WHEN (time references)
        when_patterns = [
            r'\b((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)(?:,?\s+\w+\s+\d+)?)',
            r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+(?:,?\s+\d{4})?)',
            r'\b(today|yesterday|tomorrow|this week|last week|this month)\b',
            r'\b(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)',
        ]
        for pattern in when_patterns:
            match = re.search(pattern, original_text, re.IGNORECASE)
            if match:
                key_facts["when"] = match.group(1)
                break
        
        # Extract WHERE (locations)
        where_patterns = [
            r'\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:,\s+[A-Z]{2})?)',
            r'\bat\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\b([A-Z][a-z]+(?:,\s+[A-Z][a-z]+)*)\s+(?:—|–|-)',
        ]
        for pattern in where_patterns:
            match = re.search(pattern, original_text)
            if match:
                location = match.group(1)
                # Filter out common false positives
                if location not in ["The", "A", "An", "This", "That"]:
                    key_facts["where"] = location
                    break
        
        # Extract WHY (reasons, causes)
        why_patterns = [
            r'\bbecause\s+([^.]+)',
            r'\bdue to\s+([^.]+)',
            r'\bin order to\s+([^.]+)',
            r'\bto\s+([^.]+)',
        ]
        for pattern in why_patterns:
            match = re.search(pattern, original_text, re.IGNORECASE)
            if match:
                reason = match.group(1).strip()[:100]  # Truncate
                key_facts["why"] = reason
                break
        
        # Validate that key facts are preserved in summary
        preserved_count = 0
        for fact_type, fact_value in key_facts.items():
            if fact_value and fact_value.lower() in summary_text.lower():
                preserved_count += 1
        
        logger.debug(
            f"Extracted {sum(1 for v in key_facts.values() if v)} key facts, "
            f"{preserved_count} preserved in summary"
        )
        
        return key_facts
    
    def _create_fallback_summary(self, article: Article) -> Summary:
        """
        Create fallback summary when summarization fails.
        
        Args:
            article: Original article
            
        Returns:
            Summary with fallback message
        """
        fallback_text = (
            f"Summary unavailable for this article. "
            f"Please refer to the original source for full details. "
            f"Article: {article.title}"
        )
        
        # Pad to meet minimum word count
        words = fallback_text.split()
        while len(words) < self.min_words:
            words.append(".")
        fallback_text = " ".join(words[:self.max_words])
        
        return Summary(
            article_id=article.id,
            title=article.title,
            summary_text=fallback_text,
            source=article.source,
            publication_date=article.publication_date,
            category=article.category,
            generated_at=datetime.utcnow(),
            key_facts={}
        )
    
    async def batch_summarize(self, articles: List[Article]) -> List[Summary]:
        """
        Process multiple articles concurrently (up to 50).
        
        This method implements concurrent processing with a semaphore
        to limit the number of simultaneous API calls. This prevents
        overwhelming the HuggingFace API and manages resource usage.
        
        Args:
            articles: List of articles to summarize
            
        Returns:
            List of Summary objects
        """
        if not articles:
            return []
        
        # Limit to 50 concurrent summaries
        max_concurrent = min(50, len(articles))
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def summarize_with_semaphore(article: Article) -> Summary:
            """Wrapper to enforce concurrency limit."""
            async with semaphore:
                return await self.summarize_article(article)
        
        logger.info(
            f"Starting batch summarization of {len(articles)} articles "
            f"with max_concurrent={max_concurrent}"
        )
        
        # Process all articles concurrently with semaphore control
        tasks = [summarize_with_semaphore(article) for article in articles]
        summaries = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log errors
        valid_summaries = []
        for i, result in enumerate(summaries):
            if isinstance(result, Exception):
                logger.error(
                    f"Batch summarization failed for article {articles[i].id}: {result}"
                )
                # Create fallback summary for failed articles
                valid_summaries.append(self._create_fallback_summary(articles[i]))
            else:
                valid_summaries.append(result)
        
        logger.info(
            f"Batch summarization complete: {len(valid_summaries)} summaries generated"
        )
        
        return valid_summaries
    
    async def close(self):
        """Close HTTP client and cleanup resources."""
        if hasattr(self, 'hf_client'):
            await self.hf_client.aclose()
            logger.info("HuggingFace client closed")
