from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from datetime import datetime, timezone, timedelta
import logging

from domain.entities.user import User
from middleware.auth_middleware import get_current_user, require_role
from middleware.progressive_rate_limiter import progressive_rate_limiter
from services.security_logger import security_logger
from domain.entities.user import UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/security", tags=["Security Monitoring"])

@router.get("/status")
async def get_security_status(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current security status for the requesting user.
    Available to all authenticated users for their own security status.
    """
    try:
        client_ip = request.headers.get("x-forwarded-for", 
                                      request.client.host if request.client else "unknown")
        
        # Get security status from progressive rate limiter
        security_status = progressive_rate_limiter.get_security_status(
            ip_address=client_ip,
            username=current_user.username
        )
        
        # Add user-specific security information
        user_security = {
            'user_id': current_user.id,
            'username': current_user.username,
            'account_status': current_user.status.value,
            'role': current_user.role.value,
            'two_factor_enabled': current_user.two_factor_enabled,
            'last_login': current_user.last_login.isoformat() if current_user.last_login else None,
            'failed_login_attempts': current_user.failed_login_attempts,
            'account_created': current_user.created_at.isoformat() if current_user.created_at else None,
        }
        
        # Combine all security information
        response = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_security': user_security,
            'rate_limit_status': security_status,
            'security_recommendations': []
        }
        
        # Add security recommendations
        recommendations = []
        
        if not current_user.two_factor_enabled:
            recommendations.append({
                'type': 'two_factor',
                'message': 'Enable two-factor authentication for enhanced security',
                'priority': 'high'
            })
        
        if current_user.failed_login_attempts > 0:
            recommendations.append({
                'type': 'failed_attempts',
                'message': f'You have {current_user.failed_login_attempts} recent failed login attempts',
                'priority': 'medium'
            })
        
        if security_status['failed_attempts'] > 3:
            recommendations.append({
                'type': 'ip_security',
                'message': 'Multiple failed attempts detected from your IP address',
                'priority': 'high'
            })
        
        response['security_recommendations'] = recommendations
        
        # Log security status access
        security_logger.log_data_access(
            username=current_user.username,
            ip_address=client_ip,
            data_type="security_status",
            operation="view",
            user_agent=request.headers.get("user-agent")
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting security status for user {current_user.username}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve security status"
        )

@router.get("/summary")
async def get_security_summary(
    request: Request,
    hours: int = 24,
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> Dict[str, Any]:
    """
    Get comprehensive security summary for administrators.
    Only available to admin users.
    """
    try:
        client_ip = request.headers.get("x-forwarded-for", 
                                      request.client.host if request.client else "unknown")
        
        # Get security summary from logger
        summary = security_logger.get_security_summary(hours=hours)
        
        # Add real-time security metrics
        current_time = datetime.utcnow()
        summary.update({
            'generated_at': current_time.isoformat(),
            'generated_by': current_user.username,
            'time_range': {
                'hours': hours,
                'start_time': (current_time - timedelta(hours=hours)).isoformat(),
                'end_time': current_time.isoformat()
            },
            'system_status': {
                'progressive_rate_limiter': 'active',
                'security_logging': 'active',
                'input_validation': 'active',
                'encryption_service': 'active'
            }
        })
        
        # Log admin security summary access
        security_logger.log_data_access(
            username=current_user.username,
            ip_address=client_ip,
            data_type="security_summary",
            operation="admin_view",
            record_count=1,
            user_agent=request.headers.get("user-agent")
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting security summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve security summary"
        )

@router.get("/events")
async def get_security_events(
    request: Request,
    limit: int = 50,
    event_type: Optional[str] = None,
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> Dict[str, Any]:
    """
    Get recent security events for administrators.
    Only available to admin users.
    """
    try:
        client_ip = request.headers.get("x-forwarded-for", 
                                      request.client.host if request.client else "unknown")
        
        # In a real implementation, this would query the security log database
        # For now, return a placeholder structure
        events = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_events': 0,
            'filtered_events': 0,
            'filters': {
                'limit': limit,
                'event_type': event_type
            },
            'events': [
                # Placeholder events - in real implementation, query from logs
            ],
            'pagination': {
                'current_page': 1,
                'total_pages': 1,
                'has_next': False,
                'has_previous': False
            }
        }
        
        # Log admin security events access
        security_logger.log_data_access(
            username=current_user.username,
            ip_address=client_ip,
            data_type="security_events",
            operation="admin_view",
            record_count=len(events['events']),
            user_agent=request.headers.get("user-agent")
        )
        
        return events
        
    except Exception as e:
        logger.error(f"Error getting security events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve security events"
        )

@router.post("/unlock-user/{username}")
async def unlock_user_account(
    username: str,
    request: Request,
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> Dict[str, str]:
    """
    Unlock a user account (admin only).
    """
    try:
        client_ip = request.headers.get("x-forwarded-for", 
                                      request.client.host if request.client else "unknown")
        
        # Validate username
        from middleware.input_validator import input_validator
        validated_username = input_validator.validate_username(username)
        
        # Check if account is locked in progressive rate limiter
        is_locked, remaining = progressive_rate_limiter.is_account_locked(validated_username)
        
        if is_locked:
            # Remove from account lockouts
            if validated_username in progressive_rate_limiter._account_lockouts:
                del progressive_rate_limiter._account_lockouts[validated_username]
            
            # Log administrative unlock
            security_logger.log_security_event(
                event_type=security_logger.SecurityEventType.CONFIGURATION_CHANGE,
                ip_address=client_ip,
                username=current_user.username,
                endpoint="/security/unlock-user",
                details={
                    'action': 'account_unlock',
                    'target_username': validated_username,
                    'admin_user': current_user.username,
                    'remaining_lockout_seconds': remaining
                }
            )
            
            return {
                'message': f'Account {validated_username} has been unlocked',
                'unlocked_by': current_user.username,
                'timestamp': datetime.utcnow().isoformat()
            }
        else:
            return {
                'message': f'Account {validated_username} was not locked',
                'timestamp': datetime.utcnow().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Error unlocking user account {username}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to unlock user account"
        )

@router.get("/health")
async def security_health_check() -> Dict[str, Any]:
    """
    Security system health check.
    Public endpoint for monitoring system security components.
    """
    try:
        health_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'healthy',
            'components': {
                'progressive_rate_limiter': 'active',
                'security_logger': 'active',
                'input_validator': 'active',
                'encryption_service': 'active',
                'cors_middleware': 'active'
            },
            'version': '1.0.0'
        }
        
        # Basic health checks
        try:
            # Test progressive rate limiter
            progressive_rate_limiter.get_security_status("127.0.0.1")
            health_status['components']['progressive_rate_limiter'] = 'active'
        except Exception:
            health_status['components']['progressive_rate_limiter'] = 'error'
            health_status['status'] = 'degraded'
        
        try:
            # Test input validator
            from middleware.input_validator import input_validator
            input_validator.validate_string("test", check_injections=False)
            health_status['components']['input_validator'] = 'active'
        except Exception:
            health_status['components']['input_validator'] = 'error'
            health_status['status'] = 'degraded'
        
        try:
            # Test encryption service
            from services.encryption_service import encryption_service
            test_encrypted = encryption_service.encrypt_string("test")
            encryption_service.decrypt_string(test_encrypted)
            health_status['components']['encryption_service'] = 'active'
        except Exception:
            health_status['components']['encryption_service'] = 'error'
            health_status['status'] = 'degraded'
        
        return health_status
        
    except Exception as e:
        logger.error(f"Security health check failed: {str(e)}")
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'error',
            'error': 'Health check failed',
            'components': {}
        } 