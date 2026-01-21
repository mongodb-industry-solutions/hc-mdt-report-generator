from typing import Optional, List, Callable, Any
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import wraps
import logging
from datetime import datetime, timezone

from services.auth.jwt_service import jwt_service
from domain.entities.user import User, UserRole, TokenType, JWTPayload
from config.database import MongoDBConnection
from config.settings import settings

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)

class AuthenticationError(HTTPException):
    """Custom authentication error with security logging."""
    
    def __init__(self, detail: str, request: Optional[Request] = None):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
        
        # Log security event
        if settings.log_security_events and request:
            self._log_security_event(request, detail)
    
    def _log_security_event(self, request: Request, detail: str):
        """Log authentication failure for security monitoring."""
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "Unknown")
        
        logger.warning(
            f"Authentication failed: {detail} | "
            f"IP: {client_ip} | "
            f"User-Agent: {user_agent} | "
            f"Path: {request.url.path}"
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first (behind proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection IP
        return request.client.host if request.client else "unknown"

class AuthorizationError(HTTPException):
    """Custom authorization error for insufficient permissions."""
    
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """
    Dependency to get current authenticated user from JWT token.
    Implements Phase 2 authentication requirements:
    - Bearer token validation
    - Signature verification
    - Expiration checking
    - User existence confirmation
    
    Args:
        request: FastAPI request object
        credentials: HTTP Bearer credentials
        
    Returns:
        Authenticated User object
        
    Raises:
        AuthenticationError: If authentication fails
    """
    if not credentials or not credentials.credentials:
        raise AuthenticationError("Bearer token required", request)
    
    token = credentials.credentials
    
    # Verify JWT token
    payload = jwt_service.verify_token(token, TokenType.ACCESS)
    if not payload:
        raise AuthenticationError("Invalid or expired token", request)
    
    # Get user from database and verify existence and status
    try:
        with MongoDBConnection() as db:
            user_data = db.users.find_one({"_id": payload.sub})
            if not user_data:
                raise AuthenticationError("User not found", request)
            
            user = User(**user_data)
            
            # Check if user is active and not locked
            if not user.is_active():
                status_msg = "locked" if user.is_locked() else "inactive"
                raise AuthenticationError(f"User account is {status_msg}", request)
            
            # Log successful authentication
            if settings.log_auth_events:
                logger.info(f"User {user.username} authenticated successfully")
            
            return user
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error during authentication: {e}")
        raise AuthenticationError("Authentication service unavailable", request)

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get current active user (additional active check).
    
    Args:
        current_user: User from get_current_user dependency
        
    Returns:
        Active User object
        
    Raises:
        AuthenticationError: If user is not active
    """
    if not current_user.is_active():
        raise AuthenticationError("User account is not active")
    
    return current_user

def require_roles(*required_roles: UserRole):
    """
    Decorator factory for role-based access control.
    
    Args:
        *required_roles: Required user roles for access
        
    Returns:
        Decorator function
    """
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in required_roles:
            logger.warning(
                f"User {current_user.username} attempted to access resource requiring "
                f"{[role.value for role in required_roles]} but has role {current_user.role.value}"
            )
            raise AuthorizationError(
                f"Access denied. Required roles: {[role.value for role in required_roles]}"
            )
        
        return current_user
    
    return role_checker

def require_role(required_role: UserRole):
    """
    Decorator factory for single role-based access control.
    
    Args:
        required_role: Required user role for access
        
    Returns:
        Decorator function
    """
    return require_roles(required_role)

def require_admin():
    """Shortcut decorator for admin-only access."""
    return require_roles(UserRole.ADMIN)

def require_doctor():
    """Shortcut decorator for doctor-level access."""
    return require_roles(UserRole.ADMIN, UserRole.DOCTOR)

def require_medical_staff():
    """Shortcut decorator for medical staff access."""
    return require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE)

class AuthenticatedUser:
    """
    Context manager for authenticated operations.
    Useful for services that need user context.
    """
    
    def __init__(self, user: User):
        self.user = user
        self.start_time = datetime.now(timezone.utc)
    
    def __enter__(self):
        return self.user
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Log operation completion time for audit
        duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        if settings.log_auth_events:
            logger.debug(f"Operation completed for user {self.user.username} in {duration:.2f}s")

def log_api_access(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Dependency for logging API access for audit trails.
    
    Args:
        request: FastAPI request object
        current_user: Authenticated user
    """
    if settings.log_auth_events:
        client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
        logger.info(
            f"API Access: {request.method} {request.url.path} | "
            f"User: {current_user.username} | "
            f"Role: {current_user.role.value} | "
            f"IP: {client_ip}"
        )

async def validate_token_not_expired(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Additional validation for token expiration and user status.
    Can be used as an additional dependency for sensitive operations.
    
    Args:
        request: FastAPI request object
        current_user: User from authentication
        
    Returns:
        Validated User object
    """
    # Check if password change is required
    if current_user.require_password_change:
        raise AuthenticationError("Password change required", request)
    
    # Additional security checks can be added here
    # e.g., check for suspicious login patterns, device verification, etc.
    
    return current_user

class SecurityEventLogger:
    """
    Centralized security event logging for authentication and authorization.
    """
    
    @staticmethod
    def log_login_attempt(username: str, success: bool, ip_address: str, user_agent: str = ""):
        """Log login attempt for security monitoring."""
        event_type = "login_success" if success else "login_failure"
        logger.info(
            f"Security Event: {event_type} | "
            f"Username: {username} | "
            f"IP: {ip_address} | "
            f"User-Agent: {user_agent}"
        )
    
    @staticmethod
    def log_logout(username: str, ip_address: str):
        """Log logout event."""
        logger.info(
            f"Security Event: logout | "
            f"Username: {username} | "
            f"IP: {ip_address}"
        )
    
    @staticmethod
    def log_password_change(username: str, ip_address: str):
        """Log password change event."""
        logger.info(
            f"Security Event: password_change | "
            f"Username: {username} | "
            f"IP: {ip_address}"
        )
    
    @staticmethod
    def log_account_lockout(username: str, reason: str):
        """Log account lockout event."""
        logger.warning(
            f"Security Event: account_lockout | "
            f"Username: {username} | "
            f"Reason: {reason}"
        )
    
    @staticmethod
    def log_privilege_escalation_attempt(username: str, required_role: str, actual_role: str, resource: str):
        """Log unauthorized access attempt."""
        logger.warning(
            f"Security Event: privilege_escalation_attempt | "
            f"Username: {username} | "
            f"Required: {required_role} | "
            f"Actual: {actual_role} | "
            f"Resource: {resource}"
        )

# Utility functions for extracting authentication info
def extract_token_from_request(request: Request) -> Optional[str]:
    """Extract Bearer token from request headers."""
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix
    return None

def get_user_from_token(token: str) -> Optional[User]:
    """Get user object from JWT token (for background tasks)."""
    payload = jwt_service.verify_token(token, TokenType.ACCESS)
    if not payload:
        return None
    
    try:
        with MongoDBConnection() as db:
            user_data = db.users.find_one({"_id": payload.sub})
            if user_data:
                return User(**user_data)
    except Exception as e:
        logger.error(f"Failed to get user from token: {e}")
    
    return None

# Create security event logger instance
security_logger = SecurityEventLogger() 