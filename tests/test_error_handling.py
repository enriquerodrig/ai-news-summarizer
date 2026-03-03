"""Tests for error handling utilities."""

import asyncio
import pytest
from app.utils.error_handling import (
    ExponentialBackoff,
    handle_errors,
    retry_with_backoff,
    generate_user_friendly_message,
    RateLimitHandler
)


def test_exponential_backoff_delay_calculation():
    """Test exponential backoff delay calculation."""
    backoff = ExponentialBackoff(
        initial_delay=1.0,
        max_delay=60.0,
        multiplier=2.0
    )
    
    # Test delay progression
    assert backoff.get_delay(0) == 1.0
    assert backoff.get_delay(1) == 2.0
    assert backoff.get_delay(2) == 4.0
    assert backoff.get_delay(3) == 8.0
    assert backoff.get_delay(4) == 16.0
    assert backoff.get_delay(5) == 32.0
    
    # Test max delay cap
    assert backoff.get_delay(10) == 60.0


@pytest.mark.asyncio
async def test_exponential_backoff_async_success():
    """Test exponential backoff with successful async function."""
    backoff = ExponentialBackoff(initial_delay=0.01, max_retries=3)
    
    call_count = 0
    
    async def test_func():
        nonlocal call_count
        call_count += 1
        return "success"
    
    result = await backoff.execute_async(test_func)
    
    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_exponential_backoff_async_retry():
    """Test exponential backoff retries on failure."""
    backoff = ExponentialBackoff(initial_delay=0.01, max_retries=3)
    
    call_count = 0
    
    async def test_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Temporary error")
        return "success"
    
    result = await backoff.execute_async(test_func)
    
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_exponential_backoff_async_max_retries():
    """Test exponential backoff fails after max retries."""
    backoff = ExponentialBackoff(initial_delay=0.01, max_retries=3)
    
    call_count = 0
    
    async def test_func():
        nonlocal call_count
        call_count += 1
        raise ValueError("Persistent error")
    
    with pytest.raises(ValueError, match="Persistent error"):
        await backoff.execute_async(test_func)
    
    assert call_count == 3


def test_exponential_backoff_sync_success():
    """Test exponential backoff with successful sync function."""
    backoff = ExponentialBackoff(initial_delay=0.01, max_retries=3)
    
    call_count = 0
    
    def test_func():
        nonlocal call_count
        call_count += 1
        return "success"
    
    result = backoff.execute_sync(test_func)
    
    assert result == "success"
    assert call_count == 1


def test_exponential_backoff_sync_retry():
    """Test exponential backoff retries on sync function failure."""
    backoff = ExponentialBackoff(initial_delay=0.01, max_retries=3)
    
    call_count = 0
    
    def test_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Temporary error")
        return "success"
    
    result = backoff.execute_sync(test_func)
    
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_handle_errors_decorator_async():
    """Test handle_errors decorator with async function."""
    
    @handle_errors(component_name="test_component", fallback_value="fallback")
    async def test_func(should_fail: bool):
        if should_fail:
            raise ValueError("Test error")
        return "success"
    
    # Test success case
    result = await test_func(False)
    assert result == "success"
    
    # Test error case
    result = await test_func(True)
    assert result == "fallback"


def test_handle_errors_decorator_sync():
    """Test handle_errors decorator with sync function."""
    
    @handle_errors(component_name="test_component", fallback_value="fallback")
    def test_func(should_fail: bool):
        if should_fail:
            raise ValueError("Test error")
        return "success"
    
    # Test success case
    result = test_func(False)
    assert result == "success"
    
    # Test error case
    result = test_func(True)
    assert result == "fallback"


@pytest.mark.asyncio
async def test_retry_with_backoff_decorator_async():
    """Test retry_with_backoff decorator with async function."""
    call_count = 0
    
    @retry_with_backoff(
        initial_delay=0.01,
        max_retries=3,
        exceptions=(ValueError,)
    )
    async def test_func():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ValueError("Temporary error")
        return "success"
    
    result = await test_func()
    
    assert result == "success"
    assert call_count == 2


def test_retry_with_backoff_decorator_sync():
    """Test retry_with_backoff decorator with sync function."""
    call_count = 0
    
    @retry_with_backoff(
        initial_delay=0.01,
        max_retries=3,
        exceptions=(ValueError,)
    )
    def test_func():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ValueError("Temporary error")
        return "success"
    
    result = test_func()
    
    assert result == "success"
    assert call_count == 2


def test_generate_user_friendly_message_timeout():
    """Test user-friendly message for timeout error."""
    error = TimeoutError("Connection timed out")
    message = generate_user_friendly_message(error, "loading news")
    
    assert "took too long" in message.lower()
    assert "loading news" in message
    assert "try again" in message.lower()
    # Should not contain technical details
    assert "TimeoutError" not in message
    assert "Connection timed out" not in message


def test_generate_user_friendly_message_connection():
    """Test user-friendly message for connection error."""
    error = ConnectionError("Failed to connect")
    message = generate_user_friendly_message(error, "fetching data")
    
    assert "connect" in message.lower()
    assert "fetching data" in message
    assert "try again" in message.lower()
    # Should not contain technical details
    assert "ConnectionError" not in message
    assert "Failed to connect" not in message


def test_generate_user_friendly_message_generic():
    """Test user-friendly message for generic error."""
    error = RuntimeError("Internal error")
    message = generate_user_friendly_message(error)
    
    assert "unexpected error" in message.lower()
    assert "try again" in message.lower()
    # Should not contain technical details
    assert "RuntimeError" not in message
    assert "Internal error" not in message


def test_generate_user_friendly_message_no_technical_details():
    """Test that user-friendly messages never contain technical details."""
    errors = [
        ValueError("Invalid value at line 42"),
        KeyError("missing_key"),
        AttributeError("'NoneType' object has no attribute 'value'"),
        TypeError("unsupported operand type(s)"),
    ]
    
    for error in errors:
        message = generate_user_friendly_message(error, "processing request")
        
        # Should not contain exception type names
        assert type(error).__name__ not in message
        # Should not contain original error message
        assert str(error) not in message
        # Should not contain technical terms
        assert "NoneType" not in message
        assert "attribute" not in message
        assert "operand" not in message
        # Should be user-friendly
        assert "try again" in message.lower()


@pytest.mark.asyncio
async def test_rate_limit_handler():
    """Test rate limit handler with exponential backoff."""
    handler = RateLimitHandler(initial_delay=0.01, max_delay=1.0)
    
    call_count = 0
    
    async def rate_limited_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Rate limited")
        return "success"
    
    result = await handler.handle_rate_limit(rate_limited_func)
    
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_handle_errors_with_specific_exceptions():
    """Test handle_errors decorator catches only specified exceptions."""
    
    @handle_errors(
        component_name="test_component",
        fallback_value="fallback",
        exceptions=(ValueError,)
    )
    async def test_func(error_type: str):
        if error_type == "value":
            raise ValueError("Value error")
        elif error_type == "type":
            raise TypeError("Type error")
        return "success"
    
    # Should catch ValueError
    result = await test_func("value")
    assert result == "fallback"
    
    # Should not catch TypeError
    with pytest.raises(TypeError):
        await test_func("type")


def test_exponential_backoff_custom_multiplier():
    """Test exponential backoff with custom multiplier."""
    backoff = ExponentialBackoff(
        initial_delay=1.0,
        multiplier=3.0,
        max_delay=100.0
    )
    
    assert backoff.get_delay(0) == 1.0
    assert backoff.get_delay(1) == 3.0
    assert backoff.get_delay(2) == 9.0
    assert backoff.get_delay(3) == 27.0
    assert backoff.get_delay(4) == 81.0
