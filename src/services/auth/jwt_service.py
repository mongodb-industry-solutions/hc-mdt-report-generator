from typing import Optional, Dict, Any, Set
from datetime import datetime, timezone, timedelta
import secrets
import logging
from jose import JWTError, jwt
from config.settings import settings
from domain.entities.user import User, TokenType, JWTPayload, TokenResponse
from config.database import MongoDBConnection

logger = logging.getLogger(__name__)

class JWTTokenService:
    """
    JWT Token Service implementing Phase 2 requirements:
    - HS256 algorithm with 256-bit minimum secret keys
    - Access tokens: 30 minutes expiration
    - Refresh tokens: 7 days maximum expiration
    - Token blacklisting for immediate logout
    - Signature verification and expiration checking
    - User existence confirmation
    """
    
    def __init__(self):
        # Validate secret key meets minimum requirements (256 bits = 32 characters)
        if not settings.validate_secret_key_length():
            raise ValueError("JWT secret key must be at least 256 bits (32 characters)")
        
        self.secret_key = settings.get_jwt_secret_key()
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.jwt_access_token_expire_minutes
        self.refresh_token_expire_days = settings.jwt_refresh_token_expire_days
        
        # In-memory token blacklist (in production, use Redis or database)
        self._blacklisted_tokens: Set[str] = set()
        
        logger.info(f"JWT service initialized with {self.algorithm} algorithm")
    
    def create_access_token(self, user: User) -> str:
        """
        Create JWT access token for authenticated user.
        
        Args:
            user: Authenticated user object
            
        Returns:
            JWT access token string
            
        Raises:
            ValueError: If user is invalid or inactive
        """
        if not user or not user.is_active():
            raise ValueError("Cannot create token for inactive user")
        
        # Generate unique JWT ID for blacklisting capability
        jti = secrets.token_urlsafe(32)
        
        # Current timestamp
        now = datetime.now(timezone.utc)
        expires_delta = timedelta(minutes=self.access_token_expire_minutes)
        expire = now + expires_delta
        
        # Create JWT payload
        payload = {
            "sub": str(user.id),  # Subject (user ID)
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "token_type": TokenType.ACCESS.value,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "jti": jti  # JWT ID for blacklisting
        }
        
        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Access token created for user {user.username}")
            return token
        except Exception as e:
            logger.error(f"Failed to create access token: {e}")
            raise ValueError("Failed to create access token")
    
    def create_refresh_token(self, user: User) -> str:
        """
        Create JWT refresh token for token renewal.
        
        Args:
            user: Authenticated user object
            
        Returns:
            JWT refresh token string
            
        Raises:
            ValueError: If user is invalid or inactive
        """
        if not user or not user.is_active():
            raise ValueError("Cannot create refresh token for inactive user")
        
        # Generate unique JWT ID for blacklisting capability
        jti = secrets.token_urlsafe(32)
        
        # Current timestamp
        now = datetime.now(timezone.utc)
        expires_delta = timedelta(days=self.refresh_token_expire_days)
        expire = now + expires_delta
        
        # Create JWT payload (minimal for refresh tokens)
        payload = {
            "sub": str(user.id),  # Subject (user ID)
            "username": user.username,
            "token_type": TokenType.REFRESH.value,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "jti": jti  # JWT ID for blacklisting
        }
        
        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Refresh token created for user {user.username}")
            return token
        except Exception as e:
            logger.error(f"Failed to create refresh token: {e}")
            raise ValueError("Failed to create refresh token")
    
    def create_token_pair(self, user: User) -> TokenResponse:
        """
        Create both access and refresh tokens for user.
        
        Args:
            user: Authenticated user object
            
        Returns:
            TokenResponse with both tokens and metadata
        """
        access_token = self.create_access_token(user)
        refresh_token = self.create_refresh_token(user)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.access_token_expire_minutes * 60  # Convert to seconds
        )
    
    def verify_token(self, token: str, expected_type: Optional[TokenType] = None) -> Optional[JWTPayload]:
        """
        Verify and decode JWT token with comprehensive validation.
        
        Args:
            token: JWT token string to verify
            expected_type: Expected token type (access or refresh)
            
        Returns:
            JWTPayload if valid, None if invalid
        """
        try:
            # Check if token is blacklisted
            if self.is_token_blacklisted(token):
                logger.warning("Attempted to use blacklisted token")
                return None
            
            # Decode and verify token
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": True, "verify_signature": True}
            )
            
            # Validate required fields
            required_fields = ["sub", "username", "token_type", "exp", "iat", "jti"]
            for field in required_fields:
                if field not in payload:
                    logger.warning(f"Token missing required field: {field}")
                    return None
            
            # Validate token type if specified
            if expected_type and payload.get("token_type") != expected_type.value:
                logger.warning(f"Token type mismatch. Expected: {expected_type.value}, Got: {payload.get('token_type')}")
                return None
            
            # Create and return JWT payload object
            jwt_payload = JWTPayload(
                sub=payload["sub"],
                username=payload["username"],
                email=payload.get("email", ""),
                role=payload.get("role", "user"),
                token_type=TokenType(payload["token_type"]),
                exp=payload["exp"],
                iat=payload["iat"],
                jti=payload["jti"]
            )
            
            logger.debug(f"Token verified successfully for user {jwt_payload.username}")
            return jwt_payload
            
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[TokenResponse]:
        """
        Create new access token using valid refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New TokenResponse with fresh access token, None if invalid
        """
        # Verify refresh token
        payload = self.verify_token(refresh_token, TokenType.REFRESH)
        if not payload:
            logger.warning("Invalid refresh token provided for token refresh")
            return None
        
        # Get user from database to ensure they still exist and are active
        user = self._get_user_by_id(payload.sub)
        if not user or not user.is_active():
            logger.warning(f"User {payload.username} not found or inactive during token refresh")
            return None
        
        # Create new access token (keep the same refresh token)
        access_token = self.create_access_token(user)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,  # Return the same refresh token
            token_type="bearer",
            expires_in=self.access_token_expire_minutes * 60
        )
    
    def blacklist_token(self, token: str) -> bool:
        """
        Add token to blacklist for immediate invalidation.
        
        Args:
            token: JWT token to blacklist
            
        Returns:
            True if successfully blacklisted, False otherwise
        """
        try:
            # Extract JTI from token for blacklisting
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": False}  # Don't check expiration for blacklisting
            )
            
            jti = payload.get("jti")
            if jti:
                self._blacklisted_tokens.add(jti)
                
                # In production, persist to database/Redis
                self._persist_blacklisted_token(jti, payload.get("exp", 0))
                
                logger.info(f"Token blacklisted successfully: {jti[:8]}...")
                return True
                
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")
        
        return False
    
    def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if token is in blacklist.
        
        Args:
            token: JWT token to check
            
        Returns:
            True if blacklisted, False otherwise
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": False, "verify_signature": False}
            )
            
            jti = payload.get("jti")
            return jti in self._blacklisted_tokens if jti else False
            
        except Exception:
            return True  # If we can't decode, consider it blacklisted for safety
    
    def logout_user(self, access_token: str, refresh_token: Optional[str] = None) -> bool:
        """
        Logout user by blacklisting their tokens.
        
        Args:
            access_token: User's access token
            refresh_token: User's refresh token (optional)
            
        Returns:
            True if logout successful, False otherwise
        """
        success = True
        
        # Blacklist access token
        if not self.blacklist_token(access_token):
            success = False
            logger.error("Failed to blacklist access token during logout")
        
        # Blacklist refresh token if provided
        if refresh_token and not self.blacklist_token(refresh_token):
            success = False
            logger.error("Failed to blacklist refresh token during logout")
        
        if success:
            logger.info("User logged out successfully")
        
        return success
    
    def _get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Fetch user from database by ID for token validation.
        
        Args:
            user_id: User ID from token
            
        Returns:
            User object if found, None otherwise
        """
        try:
            with MongoDBConnection() as db:
                user_data = db.users.find_one({"_id": user_id})
                if user_data:
                    return User(**user_data)
        except Exception as e:
            logger.error(f"Failed to fetch user {user_id}: {e}")
        
        return None
    
    def _persist_blacklisted_token(self, jti: str, exp: int) -> None:
        """
        Persist blacklisted token to database for distributed systems.
        
        Args:
            jti: JWT ID to blacklist
            exp: Token expiration timestamp
        """
        try:
            with MongoDBConnection() as db:
                # Store blacklisted token with expiration
                db.blacklisted_tokens.insert_one({
                    "jti": jti,
                    "blacklisted_at": datetime.now(timezone.utc),
                    "expires_at": datetime.fromtimestamp(exp, timezone.utc)
                })
                
                # Create TTL index for automatic cleanup
                db.blacklisted_tokens.create_index(
                    "expires_at", 
                    expireAfterSeconds=0,
                    background=True
                )
                
        except Exception as e:
            logger.error(f"Failed to persist blacklisted token: {e}")
    
    def load_blacklisted_tokens(self) -> None:
        """
        Load blacklisted tokens from database on service startup.
        """
        try:
            with MongoDBConnection() as db:
                # Load non-expired blacklisted tokens
                now = datetime.now(timezone.utc)
                blacklisted = db.blacklisted_tokens.find({
                    "expires_at": {"$gt": now}
                })
                
                for token_doc in blacklisted:
                    self._blacklisted_tokens.add(token_doc["jti"])
                
                logger.info(f"Loaded {len(self._blacklisted_tokens)} blacklisted tokens")
                
        except Exception as e:
            logger.error(f"Failed to load blacklisted tokens: {e}")
    
    def cleanup_expired_tokens(self) -> None:
        """
        Clean up expired tokens from memory blacklist.
        """
        # In production with Redis/database, this would be handled by TTL
        # For in-memory implementation, we'd need to track expiration times
        pass

# Global JWT service instance
jwt_service = JWTTokenService() 