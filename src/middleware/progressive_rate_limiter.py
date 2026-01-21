import time
import threading
from typing import Dict, Tuple, Optional, List
from collections import defaultdict, deque
from fastapi import HTTPException, Request
from datetime import datetime, timedelta
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class SecurityEventType(Enum):
    """Types of security events for logging."""
    FAILED_LOGIN = "failed_login"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    ACCOUNT_LOCKOUT = "account_lockout"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    PROGRESSIVE_RESTRICTION = "progressive_restriction"

class ProgressiveRateLimiter:
    """
    Progressive rate limiter that increases restrictions based on failed attempts.
    Implements account lockout and progressive delays for enhanced security.
    """
    
    def __init__(self):
        self._requests: Dict[str, deque] = defaultdict(deque)
        self._failed_attempts: Dict[str, List[float]] = defaultdict(list)
        self._lockouts: Dict[str, float] = {}  # IP -> lockout end time
        self._account_lockouts: Dict[str, float] = {}  # username -> lockout end time
        self._lock = threading.RLock()
        self._cleanup_interval = 300  # Clean up every 5 minutes
        self._last_cleanup = time.time()
    
    def is_ip_locked(self, ip_address: str) -> Tuple[bool, Optional[float]]:
        """Check if IP address is currently locked out."""
        with self._lock:
            current_time = time.time()
            if ip_address in self._lockouts:
                if current_time < self._lockouts[ip_address]:
                    remaining = self._lockouts[ip_address] - current_time
                    return True, remaining
                else:
                    # Lockout expired, remove it
                    del self._lockouts[ip_address]
            return False, None
    
    def is_account_locked(self, username: str) -> Tuple[bool, Optional[float]]:
        """Check if account is currently locked out."""
        with self._lock:
            current_time = time.time()
            if username in self._account_lockouts:
                if current_time < self._account_lockouts[username]:
                    remaining = self._account_lockouts[username] - current_time
                    return True, remaining
                else:
                    # Lockout expired, remove it
                    del self._account_lockouts[username]
            return False, None
    
    def record_failed_login(self, ip_address: str, username: Optional[str] = None) -> Dict[str, any]:
        """
        Record a failed login attempt and apply progressive restrictions.
        
        Returns:
            Dict with security actions taken and current status
        """
        current_time = time.time()
        
        with self._lock:
            # Clean up old entries
            if current_time - self._last_cleanup > self._cleanup_interval:
                self._cleanup_old_entries()
                self._last_cleanup = current_time
            
            # Record failed attempt for IP
            self._failed_attempts[ip_address].append(current_time)
            
            # Remove attempts older than 1 hour
            self._failed_attempts[ip_address] = [
                t for t in self._failed_attempts[ip_address] 
                if current_time - t <= 3600
            ]
            
            failed_count = len(self._failed_attempts[ip_address])
            security_actions = {
                'ip_address': ip_address,
                'failed_count': failed_count,
                'actions': [],
                'lockout_applied': False,
                'account_lockout_applied': False
            }
            
            # Progressive restrictions based on failed attempts
            if failed_count >= 20:
                # 20+ failures: 1 hour IP lockout
                lockout_end = current_time + 3600
                self._lockouts[ip_address] = lockout_end
                security_actions['actions'].append('ip_lockout_1hour')
                security_actions['lockout_applied'] = True
                self._log_security_event(SecurityEventType.ACCOUNT_LOCKOUT, ip_address, {
                    'reason': 'excessive_failed_attempts',
                    'failed_count': failed_count,
                    'lockout_duration': '1_hour'
                })
            elif failed_count >= 10:
                # 10+ failures: 15 minute IP lockout
                lockout_end = current_time + 900
                self._lockouts[ip_address] = lockout_end
                security_actions['actions'].append('ip_lockout_15min')
                security_actions['lockout_applied'] = True
                self._log_security_event(SecurityEventType.ACCOUNT_LOCKOUT, ip_address, {
                    'reason': 'multiple_failed_attempts',
                    'failed_count': failed_count,
                    'lockout_duration': '15_minutes'
                })
            elif failed_count >= 5:
                # 5+ failures: Progressive delay + warning
                security_actions['actions'].append('progressive_delay')
                self._log_security_event(SecurityEventType.PROGRESSIVE_RESTRICTION, ip_address, {
                    'failed_count': failed_count,
                    'restriction_type': 'progressive_delay'
                })
            
            # Account-specific lockout (if username provided)
            if username:
                account_key = f"account:{username}"
                if account_key not in self._failed_attempts:
                    self._failed_attempts[account_key] = []
                
                self._failed_attempts[account_key].append(current_time)
                self._failed_attempts[account_key] = [
                    t for t in self._failed_attempts[account_key] 
                    if current_time - t <= 3600
                ]
                
                account_failed_count = len(self._failed_attempts[account_key])
                
                if account_failed_count >= 5:
                    # Account lockout: 15 minutes
                    lockout_end = current_time + 900
                    self._account_lockouts[username] = lockout_end
                    security_actions['actions'].append('account_lockout_15min')
                    security_actions['account_lockout_applied'] = True
                    self._log_security_event(SecurityEventType.ACCOUNT_LOCKOUT, ip_address, {
                        'username': username,
                        'reason': 'account_failed_attempts',
                        'failed_count': account_failed_count,
                        'lockout_duration': '15_minutes'
                    })
            
            return security_actions
    
    def reset_failed_attempts(self, ip_address: str, username: Optional[str] = None):
        """Reset failed attempts for successful login."""
        with self._lock:
            if ip_address in self._failed_attempts:
                del self._failed_attempts[ip_address]
            
            if username:
                account_key = f"account:{username}"
                if account_key in self._failed_attempts:
                    del self._failed_attempts[account_key]
    
    def check_rate_limit(self, ip_address: str, limit: int, window_seconds: int, 
                        key_suffix: str = "") -> Tuple[bool, Dict[str, any]]:
        """
        Enhanced rate limiting with progressive restrictions.
        """
        current_time = time.time()
        
        with self._lock:
            # Check if IP is locked out
            is_locked, remaining_lockout = self.is_ip_locked(ip_address)
            if is_locked:
                return False, {
                    'limit': limit,
                    'remaining': 0,
                    'reset': None,
                    'retry_after': int(remaining_lockout),
                    'lockout_reason': 'ip_locked',
                    'message': 'IP address temporarily locked due to suspicious activity'
                }
            
            # Apply progressive restrictions based on failed attempts
            failed_count = len(self._failed_attempts.get(ip_address, []))
            effective_limit = limit
            
            if failed_count >= 5:
                # Reduce rate limit by 50% after 5 failed attempts
                effective_limit = max(1, limit // 2)
            
            if failed_count >= 3:
                # Reduce rate limit by 25% after 3 failed attempts
                effective_limit = max(1, int(limit * 0.75))
            
            # Standard rate limiting logic with effective limit
            rate_limit_key = f"{ip_address}:{key_suffix}" if key_suffix else ip_address
            requests = self._requests[rate_limit_key]
            
            # Remove requests outside the current window
            while requests and requests[0] <= current_time - window_seconds:
                requests.popleft()
            
            # Check if limit is exceeded
            current_count = len(requests)
            is_allowed = current_count < effective_limit
            
            if is_allowed:
                requests.append(current_time)
            else:
                # Log rate limit violation
                self._log_security_event(SecurityEventType.RATE_LIMIT_EXCEEDED, ip_address, {
                    'limit': effective_limit,
                    'current_count': current_count,
                    'window_seconds': window_seconds,
                    'key_suffix': key_suffix,
                    'failed_attempts': failed_count
                })
            
            # Calculate reset time
            reset_time = None
            if requests:
                reset_time = int(requests[0] + window_seconds)
            
            rate_limit_info = {
                'limit': effective_limit,
                'original_limit': limit,
                'remaining': max(0, effective_limit - current_count - (1 if is_allowed else 0)),
                'reset': reset_time,
                'retry_after': None,
                'failed_attempts': failed_count,
                'progressive_restriction': effective_limit < limit
            }
            
            if not is_allowed and requests:
                rate_limit_info['retry_after'] = int(requests[0] + window_seconds - current_time)
            
            return is_allowed, rate_limit_info
    
    def get_security_status(self, ip_address: str, username: Optional[str] = None) -> Dict[str, any]:
        """Get current security status for IP/account."""
        with self._lock:
            current_time = time.time()
            
            status = {
                'ip_address': ip_address,
                'ip_locked': False,
                'account_locked': False,
                'failed_attempts': len(self._failed_attempts.get(ip_address, [])),
                'lockout_remaining': None,
                'account_lockout_remaining': None
            }
            
            # Check IP lockout
            is_locked, remaining = self.is_ip_locked(ip_address)
            if is_locked:
                status['ip_locked'] = True
                status['lockout_remaining'] = remaining
            
            # Check account lockout
            if username:
                is_account_locked, account_remaining = self.is_account_locked(username)
                if is_account_locked:
                    status['account_locked'] = True
                    status['account_lockout_remaining'] = account_remaining
                    
                account_key = f"account:{username}"
                status['account_failed_attempts'] = len(
                    self._failed_attempts.get(account_key, [])
                )
            
            return status
    
    def _log_security_event(self, event_type: SecurityEventType, ip_address: str, 
                           details: Dict[str, any]):
        """Log security events for monitoring."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type.value,
            'ip_address': ip_address,
            'details': details
        }
        
        # Log at appropriate level based on severity
        if event_type in [SecurityEventType.ACCOUNT_LOCKOUT, SecurityEventType.SUSPICIOUS_ACTIVITY]:
            logger.warning(f"SECURITY EVENT: {event_type.value} - {log_entry}")
        else:
            logger.info(f"Security event: {event_type.value} - {log_entry}")
    
    def _cleanup_old_entries(self):
        """Clean up old entries to prevent memory leaks."""
        current_time = time.time()
        
        # Clean up old failed attempts (older than 1 hour)
        for key in list(self._failed_attempts.keys()):
            self._failed_attempts[key] = [
                t for t in self._failed_attempts[key] 
                if current_time - t <= 3600
            ]
            if not self._failed_attempts[key]:
                del self._failed_attempts[key]
        
        # Clean up expired lockouts
        for ip in list(self._lockouts.keys()):
            if current_time >= self._lockouts[ip]:
                del self._lockouts[ip]
        
        for username in list(self._account_lockouts.keys()):
            if current_time >= self._account_lockouts[username]:
                del self._account_lockouts[username]
        
        # Clean up old rate limit entries
        for key in list(self._requests.keys()):
            while self._requests[key] and self._requests[key][0] <= current_time - 3600:
                self._requests[key].popleft()
            if not self._requests[key]:
                del self._requests[key]
        
        logger.debug(f"Progressive rate limiter cleanup completed")


# Global progressive rate limiter instance
progressive_rate_limiter = ProgressiveRateLimiter()


def apply_progressive_rate_limit(
    request: Request,
    limit: int,
    window_seconds: int,
    key_suffix: str = "",
    error_message: str = "Rate limit exceeded"
) -> None:
    """
    Apply progressive rate limiting to a request.
    """
    from middleware.rate_limiter import get_client_ip
    
    client_ip = get_client_ip(request)
    
    is_allowed, rate_info = progressive_rate_limiter.check_rate_limit(
        client_ip, limit, window_seconds, key_suffix
    )
    
    if not is_allowed:
        headers = {
            'X-RateLimit-Limit': str(rate_info['limit']),
            'X-RateLimit-Remaining': str(rate_info['remaining']),
            'X-RateLimit-Reset': str(rate_info['reset']) if rate_info['reset'] else '',
            'X-RateLimit-Original-Limit': str(rate_info['original_limit']),
        }
        
        if rate_info['retry_after']:
            headers['Retry-After'] = str(rate_info['retry_after'])
        
        # Enhanced error detail for progressive restrictions
        error_detail = {
            'error': 'rate_limit_exceeded',
            'message': error_message,
            'retry_after': rate_info['retry_after'],
            'progressive_restriction': rate_info['progressive_restriction']
        }
        
        if 'lockout_reason' in rate_info:
            error_detail['lockout_reason'] = rate_info['lockout_reason']
            error_detail['message'] = rate_info['message']
        
        logger.warning(
            f"Progressive rate limit exceeded for {client_ip}. "
            f"Failed attempts: {rate_info.get('failed_attempts', 0)}, "
            f"Effective limit: {rate_info['limit']}/{window_seconds}s"
        )
        
        raise HTTPException(
            status_code=429,
            detail=error_detail,
            headers=headers
        )


# Enhanced rate limiting functions for login endpoints
def rate_limit_login_progressive(request: Request):
    """Progressive rate limiting for login endpoints (5 attempts/minute base, progressive reduction)."""
    apply_progressive_rate_limit(
        request,
        500,
        6000,
        "login:progressive",
        "Too many login attempts. Please try again later."
    )


def rate_limit_registration_strict(request: Request):
    """Strict rate limiting for registration to prevent automated account creation."""
    apply_progressive_rate_limit(
        request,
        30,  # Very strict: 3 registrations per hour
        36000,
        "registration:strict",
        "Registration rate limit exceeded. Please try again later."
    ) 