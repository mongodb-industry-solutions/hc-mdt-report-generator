from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, EmailStr, validator
from enum import Enum
import re

class UserRole(str, Enum):
    """User roles for role-based access control."""
    ADMIN = "admin"
    DOCTOR = "doctor"
    NURSE = "nurse"
    TECHNICIAN = "technician"
    USER = "user"

class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    SUSPENDED = "suspended"

class TokenType(str, Enum):
    """JWT token types."""
    ACCESS = "access"
    REFRESH = "refresh"

class PasswordComplexityResult(BaseModel):
    """Password complexity validation result."""
    is_valid: bool
    score: int = Field(ge=0, le=100)  # 0-100 password strength score
    missing_requirements: List[str] = []
    suggestions: List[str] = []

class User(BaseModel):
    """
    User domain entity with secure authentication features.
    Implements Phase 2 security requirements for authentication.
    """
    id: Optional[str] = Field(None, alias="_id")
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password_hash: str = Field(..., exclude=True)  # Never expose in API responses
    
    # User Profile
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = Field(default=UserRole.USER)
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    
    # Security Fields
    failed_login_attempts: int = Field(default=0, ge=0)
    account_locked_until: Optional[datetime] = None
    last_login: Optional[datetime] = None
    password_changed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Audit Fields
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    # Settings
    require_password_change: bool = Field(default=False)
    two_factor_enabled: bool = Field(default=False)
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format and security requirements."""
        if not v.strip():
            raise ValueError('Username cannot be empty')
        
        # Username format validation
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError('Username can only contain letters, numbers, dots, hyphens, and underscores')
        
        # Security: prevent problematic usernames
        forbidden_usernames = {'admin', 'root', 'system', 'administrator', 'test', 'user'}
        if v.lower() in forbidden_usernames:
            raise ValueError('Username not allowed')
        
        return v.strip()
    
    @validator('password_hash')
    def validate_password_hash(cls, v):
        """Validate that password hash is properly formatted bcrypt hash."""
        if not v.startswith('$2b$'):
            raise ValueError('Password hash must be a valid bcrypt hash')
        return v
    
    def is_active(self) -> bool:
        """Check if user account is active and not locked."""
        if self.status != UserStatus.ACTIVE:
            return False
        
        if self.account_locked_until:
            return datetime.now(timezone.utc) > self.account_locked_until
        
        return True
    
    def is_locked(self) -> bool:
        """Check if user account is currently locked."""
        if self.account_locked_until:
            return datetime.now(timezone.utc) <= self.account_locked_until
        return False
    
    def lock_account(self, duration_minutes: int = 15) -> None:
        """Lock user account for specified duration."""
        from datetime import timedelta
        self.account_locked_until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        self.status = UserStatus.LOCKED
        self.updated_at = datetime.now(timezone.utc)
    
    def unlock_account(self) -> None:
        """Unlock user account and reset failed attempts."""
        self.account_locked_until = None
        self.failed_login_attempts = 0
        if self.status == UserStatus.LOCKED:
            self.status = UserStatus.ACTIVE
        self.updated_at = datetime.now(timezone.utc)
    
    def increment_failed_login(self) -> None:
        """Increment failed login attempts counter."""
        self.failed_login_attempts += 1
        self.updated_at = datetime.now(timezone.utc)
    
    def reset_failed_login(self) -> None:
        """Reset failed login attempts after successful login."""
        self.failed_login_attempts = 0
        self.last_login = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def update_password_changed(self) -> None:
        """Update password changed timestamp."""
        self.password_changed_at = datetime.now(timezone.utc)
        self.require_password_change = False
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self, exclude_sensitive: bool = True) -> Dict[str, Any]:
        """Convert to dictionary, optionally excluding sensitive fields."""
        data = self.dict(by_alias=True)
        
        if exclude_sensitive:
            # Remove sensitive fields from API responses
            sensitive_fields = ['password_hash']
            for field in sensitive_fields:
                data.pop(field, None)
        
        return data

class UserCreate(BaseModel):
    """User creation request model with password validation."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=12)  # Will be validated for complexity
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = Field(default=UserRole.USER)
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format."""
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError('Username can only contain letters, numbers, dots, hyphens, and underscores')
        
        forbidden_usernames = {'admin', 'root', 'system', 'administrator', 'test', 'user'}
        if v.lower() in forbidden_usernames:
            raise ValueError('Username not allowed')
        
        return v.strip()

class UserUpdate(BaseModel):
    """User update request model."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None

class PasswordChange(BaseModel):
    """Password change request model."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=12)
    confirm_password: str = Field(..., min_length=12)
    
    @validator('confirm_password')
    def validate_password_match(cls, v, values):
        """Validate that passwords match."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

class UserLogin(BaseModel):
    """User login request model."""
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

class TokenResponse(BaseModel):
    """JWT token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires
    
class TokenRefresh(BaseModel):
    """Token refresh request model."""
    refresh_token: str = Field(..., min_length=1)

class UserResponse(BaseModel):
    """User response model for API responses."""
    id: str = Field(..., alias="_id")
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    status: UserStatus
    last_login: Optional[datetime]
    created_at: datetime
    two_factor_enabled: bool
    
    class Config:
        allow_population_by_field_name = True

class JWTPayload(BaseModel):
    """JWT token payload structure."""
    sub: str  # user ID (subject)
    username: str
    email: str
    role: str
    token_type: TokenType
    exp: int  # expiration timestamp
    iat: int  # issued at timestamp
    jti: str  # JWT ID for blacklisting 