"""
API Utilities Module - Error handling and resilience.

Per PRD Part 18: Error Handling & Resilience
Implements retry logic, graceful degradation, and user-friendly error messages.
"""

import os
import time
import functools
from typing import Optional, Callable, Any
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


class APIError(Exception):
    """Base class for API errors."""
    def __init__(self, message: str, retry_after: int = 0, is_retryable: bool = False):
        self.message = message
        self.retry_after = retry_after
        self.is_retryable = is_retryable
        super().__init__(message)


class RateLimitError(APIError):
    """Rate limit exceeded."""
    def __init__(self, retry_after: int = 5):
        super().__init__(
            "High demand - waiting for availability",
            retry_after=retry_after,
            is_retryable=True
        )


class TimeoutError(APIError):
    """Request timed out."""
    def __init__(self):
        super().__init__(
            "Request taking longer than usual",
            retry_after=0,
            is_retryable=True
        )


class ServiceUnavailableError(APIError):
    """Service temporarily unavailable."""
    def __init__(self):
        super().__init__(
            "Service temporarily unavailable",
            retry_after=5,
            is_retryable=True
        )


class AuthenticationError(APIError):
    """Invalid API key."""
    def __init__(self):
        super().__init__(
            "Invalid API key - please check your configuration",
            retry_after=0,
            is_retryable=False
        )


def with_retry(
    max_retries: int = 3,
    base_delay: float = 5.0,
    max_delay: float = 45.0,
    exponential: bool = True
):
    """
    Decorator for API calls with retry logic.

    Per PRD Part 18.1:
    - Rate limit: exponential backoff 5s -> 15s -> 45s, max 3 retries
    - Server error: auto-retry once after 5s, then manual retry
    - Timeout: show "taking longer than usual" at 30s

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential: Use exponential backoff

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    last_exception = e
                    error_str = str(e).lower()

                    # Determine error type and if retryable
                    is_rate_limit = "rate" in error_str or "429" in error_str
                    is_timeout = "timeout" in error_str or "timed out" in error_str
                    is_server_error = any(code in error_str for code in ["500", "502", "503", "504"])
                    is_auth_error = "401" in error_str or "authentication" in error_str or "invalid" in error_str

                    # Don't retry auth errors
                    if is_auth_error:
                        raise AuthenticationError()

                    # Check if we should retry
                    is_retryable = is_rate_limit or is_timeout or is_server_error

                    if not is_retryable or attempt >= max_retries:
                        break

                    # Calculate delay
                    if exponential:
                        delay = min(base_delay * (3 ** attempt), max_delay)
                    else:
                        delay = base_delay

                    # Log retry (would be shown in UI)
                    print(f"API call failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {delay}s...")

                    time.sleep(delay)

            # All retries exhausted
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def get_anthropic_client_with_retry(
    model: str = "claude-sonnet-4-20250514",
    api_key: Optional[str] = None,
    max_tokens: int = 8192,
    timeout: float = 60.0
) -> ChatAnthropic:
    """
    Get Anthropic client with proper error handling configuration.

    Args:
        model: Model name
        api_key: API key (falls back to env var)
        max_tokens: Maximum tokens for response
        timeout: Request timeout in seconds

    Returns:
        Configured ChatAnthropic client

    Raises:
        AuthenticationError: If API key is missing or invalid
    """
    key = api_key or os.getenv("ANTHROPIC_API_KEY")

    if not key:
        raise AuthenticationError()

    return ChatAnthropic(
        model=model,
        api_key=key,
        max_tokens=max_tokens,
        timeout=timeout,
    )


@with_retry(max_retries=3, base_delay=5.0, exponential=True)
def call_claude_with_retry(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "claude-sonnet-4-20250514",
    api_key: Optional[str] = None,
    max_tokens: int = 8192,
    timeout: float = 60.0
) -> str:
    """
    Call Claude API with automatic retry handling.

    Args:
        prompt: User prompt
        system_prompt: Optional system prompt
        model: Model name
        api_key: API key
        max_tokens: Maximum tokens
        timeout: Request timeout

    Returns:
        Response content string

    Raises:
        Various APIError subclasses on failure
    """
    client = get_anthropic_client_with_retry(model, api_key, max_tokens, timeout)

    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    response = client.invoke(messages)
    return response.content


def validate_api_keys() -> dict:
    """
    Validate API keys on startup.

    Per PRD Part 19.3: Run on app startup.

    Returns:
        dict with status of each API provider
    """
    status = {
        "anthropic": False,
        "openai": False,
        "demo_mode": False,
        "errors": []
    }

    # Check Anthropic
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            # Minimal validation - check key format
            if anthropic_key.startswith("sk-ant-"):
                status["anthropic"] = True
            else:
                status["errors"].append("Invalid Anthropic API key format")
        except Exception as e:
            status["errors"].append(f"Anthropic validation error: {str(e)}")
    else:
        status["demo_mode"] = True

    # Check OpenAI (for Whisper - optional)
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        if openai_key.startswith("sk-"):
            status["openai"] = True

    return status


def format_error_for_user(error: Exception) -> dict:
    """
    Format an error for user-friendly display.

    Per PRD Part 18.1: User-friendly error messages.

    Args:
        error: The exception

    Returns:
        dict with user_message, is_retryable, and retry_after
    """
    if isinstance(error, APIError):
        return {
            "user_message": error.message,
            "is_retryable": error.is_retryable,
            "retry_after": error.retry_after,
            "technical_details": str(error)
        }

    error_str = str(error).lower()

    # Rate limit
    if "rate" in error_str or "429" in error_str:
        return {
            "user_message": "High demand - please wait a moment and try again",
            "is_retryable": True,
            "retry_after": 15,
            "technical_details": str(error)
        }

    # Timeout
    if "timeout" in error_str or "timed out" in error_str:
        return {
            "user_message": "Request took too long - please try again",
            "is_retryable": True,
            "retry_after": 0,
            "technical_details": str(error)
        }

    # Server error
    if any(code in error_str for code in ["500", "502", "503", "504"]):
        return {
            "user_message": "Service temporarily unavailable - please try again in a moment",
            "is_retryable": True,
            "retry_after": 5,
            "technical_details": str(error)
        }

    # Auth error
    if "401" in error_str or "authentication" in error_str:
        return {
            "user_message": "API key is invalid or expired - please check your configuration",
            "is_retryable": False,
            "retry_after": 0,
            "technical_details": str(error)
        }

    # Network error
    if "connection" in error_str or "network" in error_str:
        return {
            "user_message": "Connection lost - checking...",
            "is_retryable": True,
            "retry_after": 2,
            "technical_details": str(error)
        }

    # Generic error
    return {
        "user_message": "Something went wrong - please try again",
        "is_retryable": True,
        "retry_after": 5,
        "technical_details": str(error)
    }


def graceful_degradation(result: dict, raw_content: str = None) -> dict:
    """
    Handle parser failures gracefully.

    Per PRD Part 18.2: If regex extraction fails, store raw output.

    Args:
        result: Parsed result dict
        raw_content: Raw LLM output

    Returns:
        Updated result with degradation flags
    """
    if not result and raw_content:
        return {
            "_raw": raw_content,
            "parse_status": "raw",
            "warning": "This section needs manual review",
            "status": "partial"
        }

    # Check for empty critical fields
    critical_empty = False
    if isinstance(result, dict):
        for key in ["industry", "use_case", "jurisdiction"]:
            if key in result and not result[key]:
                critical_empty = True
                break

    if critical_empty and raw_content:
        result["_raw"] = raw_content
        result["parse_status"] = "partial"

    return result
