import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, asdict
import hashlib
import re
from pathlib import Path

class SecurityEventType(Enum):
    """Security event types for comprehensive logging."""
    # Authentication Events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_INVALID = "token_invalid"
    
    # Authorization Events
    AUTHORIZATION_FAILURE = "authorization_failure"
    PRIVILEGE_ESCALATION_ATTEMPT = "privilege_escalation_attempt"
    UNAUTHORIZED_ACCESS_ATTEMPT = "unauthorized_access_attempt"
    
    # Rate Limiting Events
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    PROGRESSIVE_RESTRICTION_APPLIED = "progressive_restriction_applied"
    IP_LOCKOUT = "ip_lockout"
    ACCOUNT_LOCKOUT = "account_lockout"
    
    # Suspicious Activities
    SUSPICIOUS_LOGIN_PATTERN = "suspicious_login_pattern"
    MULTIPLE_FAILED_ATTEMPTS = "multiple_failed_attempts"
    UNUSUAL_ACCESS_PATTERN = "unusual_access_pattern"
    POTENTIAL_BRUTE_FORCE = "potential_brute_force"
    
    # Data Protection Events
    SENSITIVE_DATA_ACCESS = "sensitive_data_access"
    DATA_ENCRYPTION_EVENT = "data_encryption_event"
    DATA_DECRYPTION_EVENT = "data_decryption_event"
    
    # System Security Events
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_POLICY_VIOLATION = "security_policy_violation"
    INPUT_VALIDATION_FAILURE = "input_validation_failure"

@dataclass
class SecurityEvent:
    """Security event data structure."""
    event_type: SecurityEventType
    timestamp: datetime
    ip_address: str
    user_agent: Optional[str] = None
    username: Optional[str] = None  # Will be hashed for privacy
    user_id: Optional[str] = None  # Will be hashed for privacy
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    severity: str = "INFO"  # INFO, WARNING, ERROR, CRITICAL
    session_id: Optional[str] = None  # Will be hashed
    correlation_id: Optional[str] = None

class SecurityLogger:
    """
    Comprehensive security logger that tracks all security events
    while protecting sensitive information.
    """
    
    def __init__(self, log_file_path: Optional[str] = None):
        self.logger = logging.getLogger("security_events")
        self.logger.setLevel(logging.INFO)
        
        # Configure security log file handler
        if log_file_path:
            log_path = Path(log_file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(logging.INFO)
            
            # JSON formatter for structured logging
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # Console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # Only warnings and above to console
        self.logger.addHandler(console_handler)
        
        # Sensitive data patterns to filter
        self.sensitive_patterns = [
            r'password["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)',
            r'token["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)',
            r'secret["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)',
            r'key["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)',
            r'authorization["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)',
        ]
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.sensitive_patterns]
    
    def _hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data for privacy while maintaining trackability."""
        if not data:
            return ""
        return hashlib.sha256(data.encode()).hexdigest()[:16]  # First 16 chars for brevity
    
    def _sanitize_data(self, data: Any) -> Any:
        """Remove or hash sensitive data from log entries."""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                key_lower = key.lower()
                if any(sensitive in key_lower for sensitive in ['password', 'token', 'secret', 'key']):
                    if isinstance(value, str) and value:
                        sanitized[key] = f"***{self._hash_sensitive_data(value)}"
                    else:
                        sanitized[key] = "***REDACTED***"
                else:
                    sanitized[key] = self._sanitize_data(value)
            return sanitized
        elif isinstance(data, str):
            # Check for sensitive patterns in strings
            sanitized = data
            for pattern in self.compiled_patterns:
                sanitized = pattern.sub(lambda m: f'***{self._hash_sensitive_data(m.group(1))}', sanitized)
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        else:
            return data
    
    def _determine_severity(self, event_type: SecurityEventType) -> str:
        """Determine the severity level based on event type."""
        critical_events = [
            SecurityEventType.PRIVILEGE_ESCALATION_ATTEMPT,
            SecurityEventType.POTENTIAL_BRUTE_FORCE,
            SecurityEventType.ACCOUNT_LOCKOUT
        ]
        
        error_events = [
            SecurityEventType.AUTHORIZATION_FAILURE,
            SecurityEventType.UNAUTHORIZED_ACCESS_ATTEMPT,
            SecurityEventType.IP_LOCKOUT,
            SecurityEventType.SECURITY_POLICY_VIOLATION
        ]
        
        warning_events = [
            SecurityEventType.LOGIN_FAILURE,
            SecurityEventType.RATE_LIMIT_EXCEEDED,
            SecurityEventType.SUSPICIOUS_LOGIN_PATTERN,
            SecurityEventType.MULTIPLE_FAILED_ATTEMPTS,
            SecurityEventType.INPUT_VALIDATION_FAILURE
        ]
        
        if event_type in critical_events:
            return "CRITICAL"
        elif event_type in error_events:
            return "ERROR"
        elif event_type in warning_events:
            return "WARNING"
        else:
            return "INFO"
    
    def log_security_event(
        self,
        event_type: SecurityEventType,
        ip_address: str,
        username: Optional[str] = None,
        user_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ):
        """Log a security event with comprehensive details."""
        
        # Create security event
        event = SecurityEvent(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            ip_address=ip_address,
            user_agent=user_agent,
            username=self._hash_sensitive_data(username) if username else None,
            user_id=self._hash_sensitive_data(user_id) if user_id else None,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            details=self._sanitize_data(details) if details else None,
            severity=self._determine_severity(event_type),
            session_id=self._hash_sensitive_data(session_id) if session_id else None,
            correlation_id=correlation_id
        )
        
        # Convert to dict and create log message
        event_dict = asdict(event)
        event_dict['timestamp'] = event.timestamp.isoformat()
        event_dict['event_type'] = event.event_type.value
        
        log_message = json.dumps(event_dict, default=str)
        
        # Log at appropriate level
        if event.severity == "CRITICAL":
            self.logger.critical(log_message)
        elif event.severity == "ERROR":
            self.logger.error(log_message)
        elif event.severity == "WARNING":
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def log_login_attempt(
        self,
        username: str,
        success: bool,
        ip_address: str,
        user_agent: Optional[str] = None,
        failure_reason: Optional[str] = None
    ):
        """Log login attempts with security analysis."""
        event_type = SecurityEventType.LOGIN_SUCCESS if success else SecurityEventType.LOGIN_FAILURE
        
        details = {
            'success': success,
            'failure_reason': failure_reason
        }
        
        self.log_security_event(
            event_type=event_type,
            ip_address=ip_address,
            username=username,
            user_agent=user_agent,
            endpoint="/auth/login",
            method="POST",
            status_code=200 if success else 401,
            details=details
        )
    
    def log_authorization_failure(
        self,
        username: str,
        ip_address: str,
        endpoint: str,
        required_role: str,
        user_role: str,
        user_agent: Optional[str] = None
    ):
        """Log authorization failures."""
        details = {
            'required_role': required_role,
            'user_role': user_role,
            'access_denied': True
        }
        
        self.log_security_event(
            event_type=SecurityEventType.AUTHORIZATION_FAILURE,
            ip_address=ip_address,
            username=username,
            endpoint=endpoint,
            user_agent=user_agent,
            status_code=403,
            details=details
        )
    
    def log_rate_limit_violation(
        self,
        ip_address: str,
        endpoint: str,
        limit: int,
        window_seconds: int,
        current_count: int,
        user_agent: Optional[str] = None
    ):
        """Log rate limit violations."""
        details = {
            'limit': limit,
            'window_seconds': window_seconds,
            'current_count': current_count,
            'violation_type': 'rate_limit_exceeded'
        }
        
        self.log_security_event(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            ip_address=ip_address,
            endpoint=endpoint,
            user_agent=user_agent,
            status_code=429,
            details=details
        )
    
    def log_account_lockout(
        self,
        username: str,
        ip_address: str,
        reason: str,
        lockout_duration_minutes: int = 15,
        failed_attempts: int = 0
    ):
        """Log account lockout events."""
        details = {
            'lockout_reason': reason,
            'lockout_duration_minutes': lockout_duration_minutes,
            'failed_attempts': failed_attempts,
            'lockout_type': 'account_lockout'
        }
        
        self.log_security_event(
            event_type=SecurityEventType.ACCOUNT_LOCKOUT,
            ip_address=ip_address,
            username=username,
            details=details
        )
    
    def log_suspicious_activity(
        self,
        ip_address: str,
        activity_type: str,
        details: Dict[str, Any],
        username: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log suspicious activities."""
        enhanced_details = {
            'activity_type': activity_type,
            'suspicious_indicators': details,
            'requires_investigation': True
        }
        
        event_type = SecurityEventType.SUSPICIOUS_LOGIN_PATTERN
        if 'brute_force' in activity_type.lower():
            event_type = SecurityEventType.POTENTIAL_BRUTE_FORCE
        elif 'unusual_access' in activity_type.lower():
            event_type = SecurityEventType.UNUSUAL_ACCESS_PATTERN
        
        self.log_security_event(
            event_type=event_type,
            ip_address=ip_address,
            username=username,
            user_agent=user_agent,
            details=enhanced_details
        )
    
    def log_input_validation_failure(
        self,
        ip_address: str,
        endpoint: str,
        validation_error: str,
        input_data: Optional[Dict[str, Any]] = None,
        user_agent: Optional[str] = None
    ):
        """Log input validation failures."""
        details = {
            'validation_error': validation_error,
            'input_data': input_data,
            'potential_attack': 'injection_attempt' in validation_error.lower()
        }
        
        self.log_security_event(
            event_type=SecurityEventType.INPUT_VALIDATION_FAILURE,
            ip_address=ip_address,
            endpoint=endpoint,
            user_agent=user_agent,
            status_code=400,
            details=details
        )
    
    def log_data_access(
        self,
        username: str,
        ip_address: str,
        data_type: str,
        operation: str,
        record_count: Optional[int] = None,
        user_agent: Optional[str] = None
    ):
        """Log sensitive data access."""
        details = {
            'data_type': data_type,
            'operation': operation,
            'record_count': record_count,
            'data_sensitivity': 'high' if 'patient' in data_type.lower() else 'medium'
        }
        
        self.log_security_event(
            event_type=SecurityEventType.SENSITIVE_DATA_ACCESS,
            ip_address=ip_address,
            username=username,
            user_agent=user_agent,
            details=details
        )
    
    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get security event summary for monitoring dashboard."""
        # This would typically query a database or log aggregation system
        # For now, return a placeholder structure
        return {
            'timeframe_hours': hours,
            'total_events': 0,
            'critical_events': 0,
            'failed_logins': 0,
            'rate_limit_violations': 0,
            'account_lockouts': 0,
            'suspicious_activities': 0,
            'top_blocked_ips': [],
            'security_trends': {
                'increasing_failed_attempts': False,
                'unusual_access_patterns': False,
                'potential_attacks_detected': False
            }
        }


# Global security logger instance - use /tmp for logs in container
try:
    security_logger = SecurityLogger(log_file_path="/tmp/app/security_events.log")
except Exception:
    # Fallback to console-only logging if file creation fails
    security_logger = SecurityLogger() 