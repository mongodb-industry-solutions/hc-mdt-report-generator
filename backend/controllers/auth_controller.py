from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.security import HTTPAuthorizationCredentials
import logging
from datetime import datetime, timezone

from domain.entities.user import (
    User, UserCreate, UserLogin, UserResponse, TokenResponse, 
    TokenRefresh, PasswordChange, UserRole
)
from services.auth.jwt_service import jwt_service
from services.auth.password_service import password_service
from repositories.user_repository import user_repository
from middleware.auth_middleware import (
    get_current_user, get_current_active_user, security_logger,
    extract_token_from_request, security, AuthenticationError
)
from middleware.rate_limiter import rate_limit_auth, rate_limit_registration, rate_limit_failed_login
from middleware.progressive_rate_limiter import (
    progressive_rate_limiter, rate_limit_login_progressive, 
    rate_limit_registration_strict, SecurityEventType
)
from services.security_logger import security_logger
from middleware.input_validator import validate_request_data, SecurityViolation
from config.settings import settings
from utils.exceptions import ValidationException, DatabaseException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    user_create: UserCreate
) -> UserResponse:
    """
    Register new user with secure password validation.
    
    Phase 2 Implementation:
    - Password complexity validation (12+ chars, upper, lower, numbers, special)
    - bcrypt hashing with 12+ rounds
    - Unique username and email validation
    - Security event logging
    """
    try:
        # Apply strict rate limiting for registration to prevent automated account creation
        rate_limit_registration_strict(request)
        
        # Get client IP for logging
        client_ip = request.headers.get("x-forwarded-for", 
                                      request.client.host if request.client else "unknown")
        user_agent = request.headers.get("user-agent", "Unknown")
        
        # Validate input data
        try:
            validation_rules = {
                'username': {'type': 'username', 'required': True},
                'email': {'type': 'email', 'required': True},
                'password': {'type': 'string', 'required': True, 'max_length': 128},
                'first_name': {'type': 'string', 'required': True, 'max_length': 100},
                'last_name': {'type': 'string', 'required': True, 'max_length': 100}
            }
            validated_data = validate_request_data(user_create.dict(), validation_rules)
        except SecurityViolation as e:
            security_logger.log_input_validation_failure(
                ip_address=client_ip,
                endpoint="/auth/register",
                validation_error=f"{e.violation_type}: {e.details}",
                user_agent=user_agent
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid input data"
            )
        
        # Validate password complexity
        complexity_result = password_service.validate_password_complexity(user_create.password)
        if not complexity_result.is_valid:
            missing_requirements = ", ".join(complexity_result.missing_requirements)
            logger.warning(f"Registration failed - weak password for {user_create.username}: {missing_requirements}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Password does not meet complexity requirements",
                    "missing_requirements": complexity_result.missing_requirements,
                    "suggestions": complexity_result.suggestions,
                    "strength_score": complexity_result.score
                }
            )
        
        # Check if username or email already exists
        existing_user = await user_repository.get_user_by_username(user_create.username)
        if existing_user:
            logger.warning(f"Registration failed - username already exists: {user_create.username}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{user_create.username}' already exists"
            )
        
        existing_email = await user_repository.get_user_by_email(user_create.email)
        if existing_email:
            logger.warning(f"Registration failed - email already exists: {user_create.email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{user_create.email}' already exists"
            )
        
        # Create user with secure password hashing
        user = await user_repository.create_user(user_create)
        
        # Log successful registration
        security_logger.log_login_attempt(
            username=user.username,
            success=True,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        logger.info(f"User registered successfully: {user.username}")
        
        # Return user response (without sensitive data)
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            status=user.status,
            last_login=user.last_login,
            created_at=user.created_at,
            two_factor_enabled=user.two_factor_enabled
        )
        
    except HTTPException:
        raise
    except ValidationException as e:
        logger.warning(f"Registration validation failed for {user_create.username}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DatabaseException as e:
        logger.error(f"Database error during registration for {user_create.username}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                          detail="Registration service temporarily unavailable")
    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                          detail="Registration failed due to internal error")

@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    user_login: UserLogin
) -> TokenResponse:
    """
    Authenticate user and return JWT tokens.
    
    Phase 2 Implementation:
    - bcrypt password verification
    - Failed login attempt tracking (5 attempts trigger lockout)
    - Account lockout (15 minutes after 5 failed attempts)
    - JWT token generation (30-minute access, 7-day refresh)
    - Security event logging
    """
    try:
        # Apply progressive rate limiting for login attempts
        rate_limit_login_progressive(request)
        
        # Get client information for logging
        client_ip = request.headers.get("x-forwarded-for", 
                                      request.client.host if request.client else "unknown")
        user_agent = request.headers.get("user-agent", "Unknown")
        
        # Validate input data
        try:
            validation_rules = {
                'username': {'type': 'username', 'required': True},
                'password': {'type': 'string', 'required': True, 'max_length': 128}
            }
            validated_data = validate_request_data(user_login.dict(), validation_rules)
            validated_username = validated_data['username']
        except SecurityViolation as e:
            security_logger.log_input_validation_failure(
                ip_address=client_ip,
                endpoint="/auth/login",
                validation_error=f"{e.violation_type}: {e.details}",
                user_agent=user_agent
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid input data"
            )
        
        # Get user by username
        user = await user_repository.get_user_by_username(user_login.username)
        if not user:
            # Log failed login attempt without revealing username validity
            security_logger.log_login_attempt(
                username=user_login.username,
                success=False,
                ip_address=client_ip,
                user_agent=user_agent
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if account is locked
        if user.is_locked():
            security_logger.log_login_attempt(
                username=user_login.username,
                success=False,
                ip_address=client_ip,
                user_agent=user_agent
            )
            logger.warning(f"Login attempt on locked account: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is temporarily locked due to multiple failed login attempts"
            )
        
        # Check if account is active
        if not user.is_active():
            security_logger.log_login_attempt(
                username=user_login.username,
                success=False,
                ip_address=client_ip,
                user_agent=user_agent
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is not active"
            )
        
        # Verify password
        if not password_service.verify_password(user_login.password, user.password_hash):
            # Record failed login attempt with progressive restrictions
            security_actions = progressive_rate_limiter.record_failed_login(
                ip_address=client_ip,
                username=user.username
            )
            
            # Increment failed login attempts in database
            await user_repository.increment_failed_login(user.id)
            
            # Check if account should be locked (5 failed attempts)
            user.increment_failed_login()
            if user.failed_login_attempts >= settings.rate_limit_login_attempts:
                await user_repository.lock_account(
                    user.id, 
                    settings.account_lockout_duration_minutes
                )
                
                # Log account lockout with detailed information
                security_logger.log_account_lockout(
                    username=user.username,
                    ip_address=client_ip,
                    reason=f"Exceeded {settings.rate_limit_login_attempts} failed login attempts",
                    lockout_duration_minutes=settings.account_lockout_duration_minutes,
                    failed_attempts=user.failed_login_attempts
                )
                logger.warning(f"Account locked due to failed attempts: {user.username}")
            
            # Log failed login with enhanced details
            security_logger.log_login_attempt(
                username=user_login.username,
                success=False,
                ip_address=client_ip,
                user_agent=user_agent,
                failure_reason="invalid_credentials"
            )
            
            # Check for suspicious activity patterns
            if security_actions['failed_count'] >= 10:
                security_logger.log_suspicious_activity(
                    ip_address=client_ip,
                    activity_type="potential_brute_force",
                    details={
                        'failed_attempts': security_actions['failed_count'],
                        'target_username': user.username,
                        'time_window': '1_hour',
                        'security_actions': security_actions['actions']
                    },
                    username=user.username,
                    user_agent=user_agent
                )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Successful login - reset failed attempts and update last login
        await user_repository.reset_failed_login(user.id)
        
        # Reset progressive rate limiter failed attempts
        progressive_rate_limiter.reset_failed_attempts(client_ip, user.username)
        
        # Generate JWT token pair
        token_response = jwt_service.create_token_pair(user)
        
        # Log successful login with enhanced details
        security_logger.log_login_attempt(
            username=user.username,
            success=True,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        # Log data access for audit trail
        security_logger.log_data_access(
            username=user.username,
            ip_address=client_ip,
            data_type="user_authentication",
            operation="successful_login",
            user_agent=user_agent
        )
        
        logger.info(f"User logged in successfully: {user.username}")
        
        return token_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login service temporarily unavailable"
        )

@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, str]:
    """
    Logout user by blacklisting their tokens.
    
    Phase 2 Implementation:
    - Immediate token invalidation through blacklisting
    - Optional refresh token blacklisting
    - Security event logging
    """
    try:
        client_ip = request.headers.get("x-forwarded-for", 
                                      request.client.host if request.client else "unknown")
        
        access_token = credentials.credentials
        
        # Extract refresh token from request body if provided
        refresh_token = None
        if hasattr(request, 'json'):
            try:
                body = await request.json()
                refresh_token = body.get('refresh_token')
            except:
                pass
        
        # Blacklist tokens
        success = jwt_service.logout_user(access_token, refresh_token)
        
        if success:
            security_logger.log_logout(current_user.username, client_ip)
            logger.info(f"User logged out successfully: {current_user.username}")
            return {"message": "Logged out successfully"}
        else:
            logger.error(f"Failed to logout user: {current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout failed"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout service temporarily unavailable"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    token_refresh: TokenRefresh
) -> TokenResponse:
    """
    Refresh access token using valid refresh token.
    
    Phase 2 Implementation:
    - Refresh token validation
    - New access token generation
    - User existence confirmation
    """
    try:
        # Apply rate limiting for authentication
        rate_limit_auth(request)
        
        client_ip = request.headers.get("x-forwarded-for", 
                                      request.client.host if request.client else "unknown")
        
        # Refresh access token
        token_response = jwt_service.refresh_access_token(token_refresh.refresh_token)
        
        if not token_response:
            logger.warning(f"Invalid refresh token used from IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        logger.info(f"Token refreshed successfully from IP: {client_ip}")
        return token_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during token refresh: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh service temporarily unavailable"
        )

@router.post("/change-password")
async def change_password(
    request: Request,
    password_change: PasswordChange,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """
    Change user password with security validation.
    
    Phase 2 Implementation:
    - Current password verification
    - New password complexity validation
    - Secure password hashing
    - Security event logging
    """
    try:
        client_ip = request.headers.get("x-forwarded-for", 
                                      request.client.host if request.client else "unknown")
        
        # Verify current password
        if not password_service.verify_password(password_change.current_password, current_user.password_hash):
            logger.warning(f"Invalid current password for password change: {current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )
        
        # Validate new password complexity
        complexity_result = password_service.validate_password_complexity(password_change.new_password)
        if not complexity_result.is_valid:
            missing_requirements = ", ".join(complexity_result.missing_requirements)
            logger.warning(f"Password change failed - weak password for {current_user.username}: {missing_requirements}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "New password does not meet complexity requirements",
                    "missing_requirements": complexity_result.missing_requirements,
                    "suggestions": complexity_result.suggestions,
                    "strength_score": complexity_result.score
                }
            )
        
        # Update password
        success = await user_repository.update_password(
            current_user.id, 
            password_change.new_password,
            current_user.id
        )
        
        if success:
            security_logger.log_password_change(current_user.username, client_ip)
            logger.info(f"Password changed successfully for user: {current_user.username}")
            return {"message": "Password changed successfully"}
        else:
            logger.error(f"Failed to update password for user: {current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during password change: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change service temporarily unavailable"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get current user information.
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.role,
        status=current_user.status,
        last_login=current_user.last_login,
        created_at=current_user.created_at,
        two_factor_enabled=current_user.two_factor_enabled
    )

@router.post("/validate-password")
async def validate_password(
    request: Request,
    password: str = Form(...),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Validate password strength and complexity.
    
    Returns password strength analysis without storing the password.
    """
    try:
        complexity_result = password_service.validate_password_complexity(password)
        strength = password_service.check_password_strength(password)
        
        return {
            "is_valid": complexity_result.is_valid,
            "strength": strength,
            "score": complexity_result.score,
            "missing_requirements": complexity_result.missing_requirements,
            "suggestions": complexity_result.suggestions
        }
        
    except Exception as e:
        logger.error(f"Error validating password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password validation service temporarily unavailable"
        )

@router.get("/check-username/{username}")
async def check_username_availability(username: str) -> Dict[str, bool]:
    """
    Check if username is available for registration.
    """
    try:
        existing_user = await user_repository.get_user_by_username(username)
        return {"available": existing_user is None}
        
    except Exception as e:
        logger.error(f"Error checking username availability: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Username check service temporarily unavailable"
        )

@router.get("/check-email/{email}")
async def check_email_availability(email: str) -> Dict[str, bool]:
    """
    Check if email is available for registration.
    """
    try:
        existing_user = await user_repository.get_user_by_email(email)
        return {"available": existing_user is None}
        
    except Exception as e:
        logger.error(f"Error checking email availability: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email check service temporarily unavailable"
        ) 