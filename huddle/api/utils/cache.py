"""Simple TTL cache for API endpoints.

Provides caching for expensive computations like standings calculations
and stats aggregations.
"""

from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Optional

# Global cache storage
_cache: dict[str, tuple[Any, datetime]] = {}


def cached(ttl_seconds: int = 30):
    """Simple TTL cache decorator.

    Caches function results for the specified duration.
    Cache key is based on function name and arguments.

    Args:
        ttl_seconds: How long to cache results (default 30 seconds)

    Example:
        @cached(ttl_seconds=60)
        def get_standings(league):
            # Expensive computation
            return standings
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from function name and arguments
            # Use id() for objects that aren't hashable
            key_parts = [func.__name__]
            for arg in args:
                try:
                    key_parts.append(str(hash(arg)))
                except TypeError:
                    key_parts.append(str(id(arg)))
            for k, v in sorted(kwargs.items()):
                try:
                    key_parts.append(f"{k}={hash(v)}")
                except TypeError:
                    key_parts.append(f"{k}={id(v)}")
            key = ":".join(key_parts)

            now = datetime.utcnow()

            # Check cache
            if key in _cache:
                value, cached_at = _cache[key]
                if now - cached_at < timedelta(seconds=ttl_seconds):
                    return value

            # Compute and cache result
            result = func(*args, **kwargs)
            _cache[key] = (result, now)
            return result
        return wrapper
    return decorator


def invalidate_cache(prefix: Optional[str] = None):
    """Clear cache entries, optionally by prefix.

    Args:
        prefix: If provided, only clear entries whose key starts with this prefix.
                If None, clear all cache entries.

    Example:
        # Clear all standings-related cache
        invalidate_cache("_get_standings")

        # Clear entire cache
        invalidate_cache()
    """
    global _cache
    if prefix:
        _cache = {k: v for k, v in _cache.items() if not k.startswith(prefix)}
    else:
        _cache.clear()


def get_cache_stats() -> dict:
    """Get cache statistics for debugging.

    Returns:
        Dict with cache size and entry details
    """
    now = datetime.utcnow()
    return {
        "size": len(_cache),
        "entries": [
            {
                "key": k[:50] + "..." if len(k) > 50 else k,
                "age_seconds": (now - cached_at).total_seconds(),
            }
            for k, (_, cached_at) in _cache.items()
        ],
    }
