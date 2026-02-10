from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List, Optional

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Includes security and authentication configuration for Phase 2.
    """
    # Database Configuration
    mongodb_uri: str = Field(default="mongodb://localhost:27017/", alias="MONGODB_URI")
    mongodb_db: str = Field(default="clarityGR", alias="MONGODB_DB")
    
    # Core Application Security
    secret_key: str = Field(default="supersecret", alias="SECRET_KEY")
    environment: str = Field(default="development", alias="ENV")
    
    # JWT Authentication Configuration (Phase 2)
    jwt_secret_key: str = Field(default="", alias="JWT_SECRET_KEY")  # Will use SECRET_KEY if not provided
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=30, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Password Security Configuration
    password_min_length: int = Field(default=12, alias="PASSWORD_MIN_LENGTH")
    password_require_uppercase: bool = Field(default=True, alias="PASSWORD_REQUIRE_UPPERCASE")
    password_require_lowercase: bool = Field(default=True, alias="PASSWORD_REQUIRE_LOWERCASE")
    password_require_numbers: bool = Field(default=True, alias="PASSWORD_REQUIRE_NUMBERS")
    password_require_special: bool = Field(default=True, alias="PASSWORD_REQUIRE_SPECIAL")
    bcrypt_rounds: int = Field(default=12, alias="BCRYPT_ROUNDS")
    
    # CORS Configuration - Restrictive for security
    allowed_origins_str: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000", 
        alias="ALLOWED_ORIGINS"
    )
    allowed_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"], 
        alias="ALLOWED_METHODS"
    )
    allowed_headers: List[str] = Field(
        default=["Content-Type", "Authorization", "X-Requested-With"], 
        alias="ALLOWED_HEADERS"
    )
    allow_credentials: bool = Field(default=True, alias="ALLOW_CREDENTIALS")
    max_age: int = Field(default=3600, alias="CORS_MAX_AGE")
    
    # Rate Limiting Configuration (for Phase 3)
    rate_limit_login_attempts: int = Field(default=5, alias="RATE_LIMIT_LOGIN_ATTEMPTS")
    rate_limit_login_window_minutes: int = Field(default=1, alias="RATE_LIMIT_LOGIN_WINDOW_MINUTES")
    
    @property
    def allowed_origins(self) -> List[str]:
        """Parse comma-separated origins string into list."""
        return [origin.strip() for origin in self.allowed_origins_str.split(",") if origin.strip()]
    account_lockout_duration_minutes: int = Field(default=15, alias="ACCOUNT_LOCKOUT_DURATION_MINUTES")
    rate_limit_registration_per_hour: int = Field(default=10, alias="RATE_LIMIT_REGISTRATION_PER_HOUR")
    
    # Token Blacklist Configuration
    token_blacklist_enabled: bool = Field(default=True, alias="TOKEN_BLACKLIST_ENABLED")
    
    # Security Headers Configuration
    security_headers_enabled: bool = Field(default=True, alias="SECURITY_HEADERS_ENABLED")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_auth_events: bool = Field(default=True, alias="LOG_AUTH_EVENTS")
    log_security_events: bool = Field(default=True, alias="LOG_SECURITY_EVENTS")
    
    # Mistral Configuration
    mistral_mode: str = Field(default="api", alias="MISTRAL_MODE")  # 'api' or 'local'
    mistral_api_key: str = Field(default="", alias="MISTRAL_API_KEY")  # Only required for API mode
    mistral_model: str = Field(default="mistral-small-latest", alias="MISTRAL_MODEL")
    
    # Local Mistral Configuration
    mistral_local_gpu_memory_utilization: float = Field(default=0.9, alias="MISTRAL_LOCAL_GPU_MEMORY_UTILIZATION")
    # Tensor parallel size is now always 1 (single GPU) - multi-GPU support removed
    mistral_local_max_tokens: int = Field(default=10000, alias="MISTRAL_LOCAL_MAX_TOKENS")
    
    # Mistral settings are optional; no strict validation enforced anymore
    
    # GPT-Open Configuration
    gpt_open_base_url: str = Field(default="http://localhost:8080", alias="GPT_OPEN_BASE_URL")
    gpt_open_timeout: float = Field(default=300.0, alias="GPT_OPEN_TIMEOUT")
    gpt_open_model: Optional[str] = Field(default=None, alias="GPT_OPEN_MODEL")
    


    def get_jwt_secret_key(self) -> str:
        """Get JWT secret key, fallback to main secret key if not provided."""
        return self.jwt_secret_key or self.secret_key
    
    def validate_secret_key_length(self) -> bool:
        """Validate that secret key meets minimum length requirement (256 bits = 32 chars)."""
        key = self.get_jwt_secret_key()
        return len(key.encode()) >= 32  # 256 bits minimum
    
    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from string or return list."""
        if isinstance(self.allowed_origins, str):
            return [origin.strip() for origin in self.allowed_origins.split(",")]
        return self.allowed_origins
    
    def get_cors_methods(self) -> List[str]:
        """Parse CORS methods from string or return list."""
        if isinstance(self.allowed_methods, str):
            return [method.strip() for method in self.allowed_methods.split(",")]
        return self.allowed_methods
    
    def get_cors_headers(self) -> List[str]:
        """Parse CORS headers from string or return list."""
        if isinstance(self.allowed_headers, str):
            return [header.strip() for header in self.allowed_headers.split(",")]
        return self.allowed_headers

    model_config = {
        "env_file": "../.env",
        "extra": "ignore"
    }

# Global settings instance
settings = Settings() 