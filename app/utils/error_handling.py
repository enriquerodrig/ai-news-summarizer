"""Error handling utilities including decorators and retry logic."""

import asyncio
import functools
import time
from typing import Any, Callable, Optional, Type, Tuple
from app.utils.logging import get_logger


logger = get_logger("error_handler")


class ExponentialBackoff:
    """Implements exponential backoff retry logic."""
    
    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        max_retries: int = 5
    ):
        """Initialize exponential backoff configuration.
        
        Args:
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            multiplier: Multiplier for each retry
            max_retries: Maximum number of retries
        """
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.max_retries = max_retries
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        delay = self.initial_delay * (self.multiplier ** attempt)
        return min(delay, self.max_delay)
    
    async def execute_async(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute async function with exponential backoff retry.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries - 1:
                    delay = self.get_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {delay}s",
                        details={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_retries": self.max_retries,
                            "delay": delay,
                            "error": str(e)
                        }
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_retries} attempts failed",
                        details={
                            "function": func.__name__,
                            "error": str(e)
                        }
                    )
        
        raise last_exception
    
    def execute_sync(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute sync function with exponential backoff retry.
        
        Args:
            func: Sync function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries - 1:
                    delay = self.get_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {delay}s",
                        details={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_retries": self.max_retries,
                            "delay": delay,
                            "error": str(e)
                        }
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_retries} attempts failed",
                        details={
                            "function": func.__name__,
                            "error": str(e)
                        }
                    )
        
        raise last_exception


def handle_errors(
    component_name: str,
    fallback_value: Any = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_level: str = "error"
):
    """Decorator to handle errors in component methods.
    
    Args:
        component_name: Name of the component for logging
        fallback_value: Value to return on error (None by default)
        exceptions: Tuple of exception types to catch
        log_level: Log level for errors (error, warning, critical)
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            component_logger = get_logger(component_name)
            try:
                return await func(*args, **kwargs)
            except exceptions as e:
                log_method = getattr(component_logger, log_level)
                log_method(
                    f"Error in {func.__name__}",
                    details={
                        "function": func.__name__,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                return fallback_value
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            component_logger = get_logger(component_name)
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                log_method = getattr(component_logger, log_level)
                log_method(
                    f"Error in {func.__name__}",
                    details={
                        "function": func.__name__,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                return fallback_value
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def retry_with_backoff(
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    multiplier: float = 2.0,
    max_retries: int = 5,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Decorator to retry function with exponential backoff.
    
    Args:
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        multiplier: Multiplier for each retry
        max_retries: Maximum number of retries
        exceptions: Tuple of exception types to retry on
        
    Returns:
        Decorated function
    """
    backoff = ExponentialBackoff(initial_delay, max_delay, multiplier, max_retries)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            async def wrapped_func():
                try:
                    return await func(*args, **kwargs)
                except exceptions:
                    raise
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    logger.error(
                        f"Unexpected error in {func.__name__}",
                        details={
                            "function": func.__name__,
                            "error_type": type(e).__name__,
                            "error_message": str(e)
                        }
                    )
                    raise
            
            return await backoff.execute_async(wrapped_func)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            def wrapped_func():
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    raise
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    logger.error(
                        f"Unexpected error in {func.__name__}",
                        details={
                            "function": func.__name__,
                            "error_type": type(e).__name__,
                            "error_message": str(e)
                        }
                    )
                    raise
            
            return backoff.execute_sync(wrapped_func)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def generate_user_friendly_message(error: Exception, context: str = "") -> str:
    """Generate user-friendly error message without technical details.
    
    Args:
        error: Exception that occurred
        context: Context of the error (e.g., "loading news", "generating summary")
        
    Returns:
        User-friendly error message
    """
    # Map error types to user-friendly messages
    error_messages = {
        "TimeoutError": "The request took too long to complete",
        "ConnectionError": "Unable to connect to the service",
        "HTTPError": "Unable to fetch data from the service",
        "ValueError": "Invalid data received",
        "KeyError": "Required information is missing",
    }
    
    error_type = type(error).__name__
    base_message = error_messages.get(error_type, "An unexpected error occurred")
    
    if context:
        return f"{base_message} while {context}. Please try again in a moment."
    else:
        return f"{base_message}. Please try again in a moment."


class RateLimitHandler:
    """Handles API rate limiting with exponential backoff."""
    
    def __init__(self, initial_delay: float = 1.0, max_delay: float = 300.0):
        """Initialize rate limit handler.
        
        Args:
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
        """
        self.backoff = ExponentialBackoff(
            initial_delay=initial_delay,
            max_delay=max_delay,
            multiplier=2.0,
            max_retries=5
        )
    
    async def handle_rate_limit(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Handle rate-limited API call with exponential backoff.
        
        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception if all retries fail
        """
        return await self.backoff.execute_async(func, *args, **kwargs)
