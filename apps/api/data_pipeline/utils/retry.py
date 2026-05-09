"""Retry decorator with exponential backoff"""
import asyncio
import logging
from functools import wraps
from dataclasses import dataclass
from typing import Callable, TypeVar, Any

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    exceptions: tuple = (Exception,)


def retry_async(config: RetryConfig | None = None):
    """Async retry decorator with exponential backoff.

    Usage:
        @retry_async(RetryConfig(max_attempts=5))
        async def fetch_data():
            ...
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except config.exceptions as e:
                    last_exception = e

                    if attempt == config.max_attempts - 1:
                        logger.error(
                            f"{func.__name__} failed after {config.max_attempts} attempts: {e}"
                        )
                        raise

                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )

                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{config.max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )

                    await asyncio.sleep(delay)

            raise last_exception

        return wrapper
    return decorator
