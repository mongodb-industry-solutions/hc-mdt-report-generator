import time
import threading
from typing import Dict, Tuple, Optional
from collections import defaultdict, deque
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter using sliding window algorithm.
    Thread-safe implementation for single-server deployments.
    """
    
    def __init__(self):
        self._requests: Dict[str, deque] = defaultdict(deque)
        self._lock = threading.RLock()
        self._cleanup_interval = 300  # Clean up old entries every 5 minutes
        self._last_cleanup = time.time()
    
    def is_allowed(self, key: str, limit: int, window_seconds: int) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is allowed based on rate limit.
        
        Args:
            key: Unique identifier for the rate limit (e.g., IP address, user ID)
            limit: Maximum number of requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        current_time = time.time()
        
        with self._lock:
            # Clean up old entries periodically
            if current_time - self._last_cleanup > self._cleanup_interval:
                self._cleanup_old_entries()
                self._last_cleanup = current_time
            
            # Get request history for this key
            requests = self._requests[key]
            
            # Remove requests outside the current window
            while requests and requests[0] <= current_time - window_seconds:
                requests.popleft()
            
            # Check if limit is exceeded
            current_count = len(requests)
            is_allowed = current_count < limit
            
            if is_allowed:
                # Add current request timestamp
                requests.append(current_time)
            
            # Calculate reset time (when oldest request in window expires)
            reset_time = None
            if requests:
                reset_time = int(requests[0] + window_seconds)
            
            rate_limit_info = {
                'limit': limit,
                'remaining': max(0, limit - current_count - (1 if is_allowed else 0)),
                'reset': reset_time,
                'retry_after': None
            }
            
            if not is_allowed:
                # Calculate retry after (when next slot becomes available)
                if requests:
                    rate_limit_info['retry_after'] = int(requests[0] + window_seconds - current_time)
            
            return is_allowed, rate_limit_info
    
    def _cleanup_old_entries(self):
        """Remove empty deques and old timestamps to prevent memory leaks."""
        current_time = time.time()
        keys_to_remove = []
        
        for key, requests in self._requests.items():
            # Remove requests older than 1 hour (conservative cleanup)
            while requests and requests[0] <= current_time - 3600:
                requests.popleft()
            
            # Mark empty deques for removal
            if not requests:
                keys_to_remove.append(key)
        
        # Remove empty entries
        for key in keys_to_remove:
            del self._requests[key]
        
        logger.debug(f"Rate limiter cleanup: removed {len(keys_to_remove)} empty entries")


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


class RateLimitConfig:
    """Rate limiting configuration for different endpoints."""
    
    # General API rate limits (per IP)
    GENERAL_REQUESTS_PER_MINUTE = 60000
    GENERAL_REQUESTS_PER_HOUR = 1000000
    
    # Authentication endpoint limits (per IP)
    AUTH_REQUESTS_PER_MINUTE = 1000
    AUTH_REQUESTS_PER_HOUR = 10000
    
    # Failed login attempts (per IP)
    FAILED_LOGIN_ATTEMPTS_PER_MINUTE = 5
    FAILED_LOGIN_ATTEMPTS_PER_HOUR = 20
    
    # Registration limits (per IP)
    REGISTRATION_REQUESTS_PER_HOUR = 50
    REGISTRATION_REQUESTS_PER_DAY = 100


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    # Check for forwarded headers (when behind proxy)
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip
    
    # Fallback to direct client IP
    return request.client.host if request.client else 'unknown'


def apply_rate_limit(
    request: Request,
    limit: int,
    window_seconds: int,
    key_suffix: str = "",
    error_message: str = "Rate limit exceeded"
) -> None:
    """
    Apply rate limiting to a request.
    
    Args:
        request: FastAPI request object
        limit: Maximum number of requests allowed
        window_seconds: Time window in seconds
        key_suffix: Additional suffix for rate limit key
        error_message: Custom error message
        
    Raises:
        HTTPException: If rate limit is exceeded
    """
    client_ip = get_client_ip(request)
    rate_limit_key = f"{client_ip}:{key_suffix}" if key_suffix else client_ip
    
    is_allowed, rate_info = rate_limiter.is_allowed(rate_limit_key, limit, window_seconds)
    
    if not is_allowed:
        logger.warning(
            f"Rate limit exceeded for {client_ip} on {request.url.path}. "
            f"Key: {rate_limit_key}, Limit: {limit}/{window_seconds}s"
        )
        
        headers = {
            'X-RateLimit-Limit': str(rate_info['limit']),
            'X-RateLimit-Remaining': str(rate_info['remaining']),
            'X-RateLimit-Reset': str(rate_info['reset']) if rate_info['reset'] else '',
        }
        
        if rate_info['retry_after']:
            headers['Retry-After'] = str(rate_info['retry_after'])
        
        raise HTTPException(
            status_code=429,
            detail={
                'error': 'rate_limit_exceeded',
                'message': error_message,
                'retry_after': rate_info['retry_after']
            },
            headers=headers
        )


# Rate limiting decorators for common use cases

def rate_limit_general(request: Request):
    """General API rate limiting (60/minute, 1000/hour)."""
    # Check minute limit
    apply_rate_limit(
        request, 
        RateLimitConfig.GENERAL_REQUESTS_PER_MINUTE, 
        60, 
        "general:minute",
        "Too many requests. Please try again in a minute."
    )
    
    # Check hour limit
    apply_rate_limit(
        request, 
        RateLimitConfig.GENERAL_REQUESTS_PER_HOUR, 
        3600, 
        "general:hour",
        "Hourly rate limit exceeded. Please try again later."
    )


def rate_limit_auth(request: Request):
    """Authentication endpoint rate limiting (10/minute, 100/hour)."""
    # Check minute limit
    apply_rate_limit(
        request, 
        RateLimitConfig.AUTH_REQUESTS_PER_MINUTE, 
        60, 
        "auth:minute",
        "Too many authentication attempts. Please try again in a minute."
    )
    
    # Check hour limit
    apply_rate_limit(
        request, 
        RateLimitConfig.AUTH_REQUESTS_PER_HOUR, 
        3600, 
        "auth:hour",
        "Hourly authentication limit exceeded. Please try again later."
    )


def rate_limit_registration(request: Request):
    """Registration endpoint rate limiting (5/hour, 10/day)."""
    # Check hour limit
    apply_rate_limit(
        request, 
        RateLimitConfig.REGISTRATION_REQUESTS_PER_HOUR, 
        3600, 
        "registration:hour",
        "Too many registration attempts. Please try again later."
    )
    
    # Check day limit
    apply_rate_limit(
        request, 
        RateLimitConfig.REGISTRATION_REQUESTS_PER_DAY, 
        86400, 
        "registration:day",
        "Daily registration limit exceeded. Please try again tomorrow."
    )


def rate_limit_failed_login(request: Request):
    """Failed login attempt rate limiting (5/minute, 20/hour)."""
    # Check minute limit
    apply_rate_limit(
        request, 
        RateLimitConfig.FAILED_LOGIN_ATTEMPTS_PER_MINUTE, 
        60, 
        "failed_login:minute",
        "Too many failed login attempts. Please try again in a minute."
    )
    
    # Check hour limit
    apply_rate_limit(
        request, 
        RateLimitConfig.FAILED_LOGIN_ATTEMPTS_PER_HOUR, 
        3600, 
        "failed_login:hour",
        "Too many failed login attempts. Account temporarily restricted."
    ) 