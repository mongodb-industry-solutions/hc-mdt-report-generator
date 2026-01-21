import re
import html
import json
from typing import Any, Dict, List, Optional, Union
from fastapi import Request, HTTPException
from pydantic import BaseModel, validator
import logging
from urllib.parse import unquote
import base64

logger = logging.getLogger(__name__)

class SecurityViolation(Exception):
    """Exception raised when security validation fails."""
    def __init__(self, violation_type: str, details: str):
        self.violation_type = violation_type
        self.details = details
        super().__init__(f"Security violation: {violation_type} - {details}")

class InputValidator:
    """
    Comprehensive input validator to prevent injection attacks and
    validate all user input across the application.
    """
    
    def __init__(self):
        # SQL injection patterns
        self.sql_patterns = [
            r"(\b(select|insert|update|delete|drop|create|alter|exec|execute|union|or|and)\b)",
            r"(['\"]\s*(or|and)\s+['\"]\s*=\s*['\"])",
            r"(;\s*(drop|delete|insert|update|create|alter))",
            r"(\b(information_schema|sys\.tables|sys\.columns)\b)",
            r"(0x[0-9a-f]+)",  # Hex encoding
            r"(\b(char|ascii|substring|length|concat)\s*\()",
            r"(@@version|@@user|@@database)",
            r"(\bunion\s+select\b)",
            r"(\bwaitfor\s+delay\b)",
            r"(\bconvert\s*\()",
        ]
        
        # NoSQL injection patterns (for MongoDB)
        self.nosql_patterns = [
            r"(\$where|\$regex|\$ne|\$gt|\$lt|\$gte|\$lte|\$in|\$nin)",
            r"(javascript:|eval\s*\()",
            r"(\bMapReduce\b|\bmapreduce\b)",
            r"(\$exists|\$type|\$size)",
            r"(this\.|function\s*\()",
        ]
        
        # XSS patterns
        self.xss_patterns = [
            r"(<script[^>]*>.*?</script>)",
            r"(javascript\s*:)",
            r"(on\w+\s*=)",
            r"(<iframe[^>]*>)",
            r"(<object[^>]*>)",
            r"(<embed[^>]*>)",
            r"(<link[^>]*>)",
            r"(<meta[^>]*>)",
            r"(expression\s*\()",
            r"(url\s*\([^)]*javascript)",
            r"(<img[^>]*onerror)",
            r"(<svg[^>]*onload)",
        ]
        
        # Command injection patterns
        self.command_patterns = [
            r"(;\s*[a-z]+)",
            r"(\|\s*[a-z]+)",
            r"(`[^`]*`)",
            r"(\$\([^)]*\))",
            r"(\{[^}]*\})",
            r"(&&|\|\|)",
            r"(>|<|>>)",
            r"(\.\./|\.\.\\)",
            r"(/etc/passwd|/etc/shadow|/etc/hosts)",
            r"(cmd\.exe|powershell|bash|sh)",
        ]
        
        # Path traversal patterns
        self.path_traversal_patterns = [
            r"(\.\./|\.\.\\)",
            r"(\.\.%2f|\.\.%5c)",
            r"(%2e%2e%2f|%2e%2e%5c)",
            r"(\\\.\\\.\\|/\.\./)",
            r"(file://|ftp://)",
        ]
        
        # LDAP injection patterns
        self.ldap_patterns = [
            r"(\*|\(|\)|&|\|)",
            r"(cn=|uid=|ou=|dc=)",
            r"(objectClass=)",
        ]
        
        # Compile all patterns
        self.compiled_sql = [re.compile(pattern, re.IGNORECASE) for pattern in self.sql_patterns]
        self.compiled_nosql = [re.compile(pattern, re.IGNORECASE) for pattern in self.nosql_patterns]
        self.compiled_xss = [re.compile(pattern, re.IGNORECASE) for pattern in self.xss_patterns]
        self.compiled_command = [re.compile(pattern, re.IGNORECASE) for pattern in self.command_patterns]
        self.compiled_path = [re.compile(pattern, re.IGNORECASE) for pattern in self.path_traversal_patterns]
        self.compiled_ldap = [re.compile(pattern, re.IGNORECASE) for pattern in self.ldap_patterns]
        
        # Common malicious file extensions
        self.dangerous_extensions = {
            '.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.vbs', '.js', '.jar',
            '.asp', '.aspx', '.php', '.jsp', '.py', '.rb', '.pl', '.sh', '.ps1'
        }
        
        # Maximum input lengths
        self.max_lengths = {
            'username': 50,
            'email': 254,
            'password': 128,
            'name': 100,
            'description': 1000,
            'filename': 255,
            'url': 2048,
            'general_text': 5000
        }
    
    def validate_string(self, value: str, field_name: str = "input", 
                       max_length: Optional[int] = None,
                       allow_html: bool = False,
                       check_injections: bool = True) -> str:
        """
        Validate a string input against various security threats.
        
        Args:
            value: The string to validate
            field_name: Name of the field for error reporting
            max_length: Maximum allowed length
            allow_html: Whether to allow HTML content
            check_injections: Whether to check for injection attacks
            
        Returns:
            Sanitized string
            
        Raises:
            SecurityViolation: If validation fails
        """
        if not isinstance(value, str):
            raise SecurityViolation("invalid_type", f"{field_name} must be a string")
        
        original_value = value
        
        # URL decode to catch encoded attacks
        try:
            decoded_value = unquote(value)
        except Exception:
            decoded_value = value
        
        # Check length
        if max_length and len(value) > max_length:
            raise SecurityViolation("length_exceeded", 
                                   f"{field_name} exceeds maximum length of {max_length}")
        
        # Check for null bytes
        if '\x00' in value:
            raise SecurityViolation("null_byte", f"{field_name} contains null bytes")
        
        if check_injections:
            # Check for SQL injection
            for pattern in self.compiled_sql:
                if pattern.search(value) or pattern.search(decoded_value):
                    self._log_security_violation("sql_injection", field_name, value)
                    raise SecurityViolation("sql_injection", 
                                           f"{field_name} contains potential SQL injection")
            
            # Check for NoSQL injection
            for pattern in self.compiled_nosql:
                if pattern.search(value) or pattern.search(decoded_value):
                    self._log_security_violation("nosql_injection", field_name, value)
                    raise SecurityViolation("nosql_injection", 
                                           f"{field_name} contains potential NoSQL injection")
            
            # Check for command injection
            for pattern in self.compiled_command:
                if pattern.search(value) or pattern.search(decoded_value):
                    self._log_security_violation("command_injection", field_name, value)
                    raise SecurityViolation("command_injection", 
                                           f"{field_name} contains potential command injection")
            
            # Check for path traversal
            for pattern in self.compiled_path:
                if pattern.search(value) or pattern.search(decoded_value):
                    self._log_security_violation("path_traversal", field_name, value)
                    raise SecurityViolation("path_traversal", 
                                           f"{field_name} contains potential path traversal")
            
            # Check for LDAP injection
            for pattern in self.compiled_ldap:
                if pattern.search(value) or pattern.search(decoded_value):
                    self._log_security_violation("ldap_injection", field_name, value)
                    raise SecurityViolation("ldap_injection", 
                                           f"{field_name} contains potential LDAP injection")
        
        # Handle HTML content
        if not allow_html:
            # Check for XSS
            for pattern in self.compiled_xss:
                if pattern.search(value) or pattern.search(decoded_value):
                    self._log_security_violation("xss_attempt", field_name, value)
                    raise SecurityViolation("xss_attempt", 
                                           f"{field_name} contains potential XSS")
            
            # Escape HTML entities
            value = html.escape(value)
        else:
            # Even if HTML is allowed, check for dangerous scripts
            dangerous_xss = [
                r"(<script[^>]*>.*?</script>)",
                r"(javascript\s*:)",
                r"(on\w+\s*=)"
            ]
            for pattern_str in dangerous_xss:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                if pattern.search(value):
                    self._log_security_violation("dangerous_html", field_name, value)
                    raise SecurityViolation("dangerous_html", 
                                           f"{field_name} contains dangerous HTML")
        
        return value.strip()
    
    def validate_email(self, email: str) -> str:
        """Validate email address format and security."""
        email = self.validate_string(email, "email", max_length=254)
        
        # Email format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise SecurityViolation("invalid_format", "Invalid email format")
        
        # Check for suspicious email patterns
        suspicious_patterns = [
            r'.*\+.*\+.*',  # Multiple plus signs
            r'.*\.{2,}.*',  # Multiple consecutive dots
            r'.*@.*@.*',    # Multiple @ signs
        ]
        
        for pattern_str in suspicious_patterns:
            if re.match(pattern_str, email):
                raise SecurityViolation("suspicious_email", "Email format appears suspicious")
        
        return email.lower()
    
    def validate_username(self, username: str) -> str:
        """Validate username format and security."""
        username = self.validate_string(username, "username", max_length=50)
        
        # Username format validation (alphanumeric, underscore, hyphen)
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise SecurityViolation("invalid_format", 
                                   "Username can only contain letters, numbers, underscore, and hyphen")
        
        # Minimum length
        if len(username) < 3:
            raise SecurityViolation("too_short", "Username must be at least 3 characters")
        
        # Check for reserved words
        reserved_words = {
            'admin', 'root', 'system', 'administrator', 'user', 'guest', 
            'test', 'demo', 'api', 'null', 'undefined', 'anonymous'
        }
        if username.lower() in reserved_words:
            raise SecurityViolation("reserved_word", "Username is reserved")
        
        return username
    
    def validate_filename(self, filename: str) -> str:
        """Validate file name for security."""
        filename = self.validate_string(filename, "filename", max_length=255)
        
        # Check for dangerous extensions
        file_extension = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        if file_extension in self.dangerous_extensions:
            raise SecurityViolation("dangerous_extension", 
                                   f"File extension {file_extension} is not allowed")
        
        # Check for dangerous filename patterns
        dangerous_patterns = [
            r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\.|$)',  # Windows reserved names
            r'^\.',  # Hidden files starting with dot
            r'.*\.(bat|cmd|exe|com|scr|pif)$',  # Executable extensions
        ]
        
        for pattern_str in dangerous_patterns:
            if re.match(pattern_str, filename, re.IGNORECASE):
                raise SecurityViolation("dangerous_filename", "Filename pattern not allowed")
        
        return filename
    
    def validate_json(self, json_data: Union[str, dict], max_size: int = 10000) -> dict:
        """Validate JSON data for security."""
        if isinstance(json_data, str):
            # Check size before parsing
            if len(json_data) > max_size:
                raise SecurityViolation("json_too_large", f"JSON data exceeds {max_size} bytes")
            
            try:
                data = json.loads(json_data)
            except json.JSONDecodeError as e:
                raise SecurityViolation("invalid_json", f"Invalid JSON format: {str(e)}")
        else:
            data = json_data
        
        # Check for deeply nested objects (potential DoS)
        max_depth = 10
        if self._get_json_depth(data) > max_depth:
            raise SecurityViolation("json_too_deep", f"JSON nesting exceeds {max_depth} levels")
        
        # Validate all string values in the JSON
        self._validate_json_recursive(data)
        
        return data
    
    def validate_base64(self, data: str, max_size: int = 1000000) -> bytes:
        """Validate and decode base64 data."""
        data = self.validate_string(data, "base64_data", check_injections=False)
        
        if len(data) > max_size:
            raise SecurityViolation("data_too_large", f"Base64 data exceeds {max_size} bytes")
        
        try:
            decoded = base64.b64decode(data)
        except Exception as e:
            raise SecurityViolation("invalid_base64", f"Invalid base64 encoding: {str(e)}")
        
        return decoded
    
    def validate_url(self, url: str) -> str:
        """Validate URL for security."""
        url = self.validate_string(url, "url", max_length=2048)
        
        # Basic URL format check
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, url):
            raise SecurityViolation("invalid_url", "Invalid URL format")
        
        # Check for dangerous protocols
        dangerous_protocols = ['javascript:', 'data:', 'file:', 'ftp:']
        for protocol in dangerous_protocols:
            if url.lower().startswith(protocol):
                raise SecurityViolation("dangerous_protocol", f"Protocol {protocol} not allowed")
        
        # Check for localhost/internal IPs (optional security measure)
        internal_patterns = [
            r'://localhost[:/]',
            r'://127\.0\.0\.1[:/]',
            r'://10\.\d+\.\d+\.\d+[:/]',
            r'://192\.168\.\d+\.\d+[:/]',
            r'://172\.(1[6-9]|2\d|3[01])\.\d+\.\d+[:/]',
        ]
        
        for pattern_str in internal_patterns:
            if re.search(pattern_str, url, re.IGNORECASE):
                raise SecurityViolation("internal_url", "Internal URLs not allowed")
        
        return url
    
    def _get_json_depth(self, obj: Any, depth: int = 0) -> int:
        """Calculate the depth of nested JSON objects."""
        if isinstance(obj, dict):
            return max([self._get_json_depth(v, depth + 1) for v in obj.values()] + [depth])
        elif isinstance(obj, list):
            return max([self._get_json_depth(item, depth + 1) for item in obj] + [depth])
        else:
            return depth
    
    def _validate_json_recursive(self, obj: Any, path: str = "root"):
        """Recursively validate all string values in JSON data."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                # Validate keys
                if isinstance(key, str):
                    self.validate_string(key, f"{path}.{key}_key", max_length=100)
                self._validate_json_recursive(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                self._validate_json_recursive(item, f"{path}[{i}]")
        elif isinstance(obj, str):
            # Validate string values
            self.validate_string(obj, path, max_length=5000)
    
    def _log_security_violation(self, violation_type: str, field_name: str, value: str):
        """Log security violations for monitoring."""
        # Truncate value for logging
        log_value = value[:100] + "..." if len(value) > 100 else value
        logger.warning(f"Security violation: {violation_type} in field {field_name}, value: {log_value}")


# Global input validator instance
input_validator = InputValidator()


def validate_request_data(request_data: Dict[str, Any], 
                         validation_rules: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate request data according to specified rules.
    
    Args:
        request_data: The data to validate
        validation_rules: Dictionary of field validation rules
        
    Returns:
        Validated and sanitized data
        
    Example:
        rules = {
            'username': {'type': 'username', 'required': True},
            'email': {'type': 'email', 'required': True},
            'description': {'type': 'string', 'max_length': 500, 'allow_html': True}
        }
    """
    validated_data = {}
    
    for field_name, rules in validation_rules.items():
        value = request_data.get(field_name)
        
        # Check required fields
        if rules.get('required', False) and value is None:
            raise SecurityViolation("missing_required", f"Field {field_name} is required")
        
        if value is None:
            continue
        
        field_type = rules.get('type', 'string')
        
        try:
            if field_type == 'username':
                validated_data[field_name] = input_validator.validate_username(value)
            elif field_type == 'email':
                validated_data[field_name] = input_validator.validate_email(value)
            elif field_type == 'filename':
                validated_data[field_name] = input_validator.validate_filename(value)
            elif field_type == 'url':
                validated_data[field_name] = input_validator.validate_url(value)
            elif field_type == 'json':
                max_size = rules.get('max_size', 10000)
                validated_data[field_name] = input_validator.validate_json(value, max_size)
            elif field_type == 'base64':
                max_size = rules.get('max_size', 1000000)
                validated_data[field_name] = input_validator.validate_base64(value, max_size)
            else:  # string
                max_length = rules.get('max_length')
                allow_html = rules.get('allow_html', False)
                check_injections = rules.get('check_injections', True)
                validated_data[field_name] = input_validator.validate_string(
                    value, field_name, max_length, allow_html, check_injections
                )
        
        except SecurityViolation:
            raise
        except Exception as e:
            logger.error(f"Validation error for field {field_name}: {str(e)}")
            raise SecurityViolation("validation_error", f"Invalid {field_name}: {str(e)}")
    
    return validated_data 