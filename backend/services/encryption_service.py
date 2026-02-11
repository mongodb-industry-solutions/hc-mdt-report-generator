import os
import base64
import hashlib
from typing import Optional, Union, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class EncryptionError(Exception):
    """Custom exception for encryption-related errors."""
    pass

class AESEncryptionService:
    """
    AES-256 encryption service for protecting sensitive data at rest.
    Implements field-level encryption with key derivation and secure random IVs.
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption service with master key.
        
        Args:
            master_key: Base64-encoded master key. If None, uses environment variable.
        """
        if master_key:
            self.master_key = base64.b64decode(master_key)
        else:
            # Get master key from environment
            env_key = os.getenv('ENCRYPTION_MASTER_KEY')
            if not env_key:
                raise EncryptionError("No encryption master key provided")
            self.master_key = base64.b64decode(env_key)
        
        if len(self.master_key) not in [16, 24, 32]:
            raise EncryptionError("Master key must be 16, 24, or 32 bytes for AES")
        
        # Use 32-byte key for AES-256
        if len(self.master_key) < 32:
            # Derive 32-byte key using PBKDF2
            self.master_key = self._derive_key(self.master_key, b"clarityGR_encryption", 32)
        
        self.backend = default_backend()
    
    def _derive_key(self, password: bytes, salt: bytes, length: int) -> bytes:
        """Derive encryption key using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=length,
            salt=salt,
            iterations=100000,  # High iteration count for security
            backend=self.backend
        )
        return kdf.derive(password)
    
    def _generate_iv(self) -> bytes:
        """Generate a random 16-byte initialization vector."""
        return os.urandom(16)
    
    def encrypt_string(self, plaintext: str, context: str = "") -> str:
        """
        Encrypt a string using AES-256-CBC.
        
        Args:
            plaintext: The string to encrypt
            context: Optional context for key derivation (e.g., field name)
            
        Returns:
            Base64-encoded encrypted data (IV + ciphertext)
        """
        if not plaintext:
            return ""
        
        try:
            # Convert string to bytes
            plaintext_bytes = plaintext.encode('utf-8')
            
            # Generate random IV
            iv = self._generate_iv()
            
            # Derive field-specific key if context provided
            if context:
                field_key = self._derive_key(
                    self.master_key, 
                    context.encode('utf-8')[:16].ljust(16, b'\0'), 
                    32
                )
            else:
                field_key = self.master_key
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(field_key),
                modes.CBC(iv),
                backend=self.backend
            )
            encryptor = cipher.encryptor()
            
            # Apply PKCS7 padding
            padded_data = self._apply_pkcs7_padding(plaintext_bytes)
            
            # Encrypt
            ciphertext = encryptor.update(padded_data) + encryptor.finalize()
            
            # Combine IV and ciphertext
            encrypted_data = iv + ciphertext
            
            # Return base64-encoded result
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Encryption failed for context '{context}': {str(e)}")
            raise EncryptionError(f"Encryption failed: {str(e)}")
    
    def decrypt_string(self, encrypted_data: str, context: str = "") -> str:
        """
        Decrypt a string using AES-256-CBC.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            context: Optional context for key derivation (must match encryption context)
            
        Returns:
            Decrypted string
        """
        if not encrypted_data:
            return ""
        
        try:
            # Decode base64
            encrypted_bytes = base64.b64decode(encrypted_data)
            
            if len(encrypted_bytes) < 16:
                raise EncryptionError("Invalid encrypted data: too short")
            
            # Extract IV and ciphertext
            iv = encrypted_bytes[:16]
            ciphertext = encrypted_bytes[16:]
            
            # Derive field-specific key if context provided
            if context:
                field_key = self._derive_key(
                    self.master_key, 
                    context.encode('utf-8')[:16].ljust(16, b'\0'), 
                    32
                )
            else:
                field_key = self.master_key
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(field_key),
                modes.CBC(iv),
                backend=self.backend
            )
            decryptor = cipher.decryptor()
            
            # Decrypt
            padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Remove PKCS7 padding
            plaintext_bytes = self._remove_pkcs7_padding(padded_plaintext)
            
            # Convert to string
            return plaintext_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Decryption failed for context '{context}': {str(e)}")
            raise EncryptionError(f"Decryption failed: {str(e)}")
    
    def encrypt_dict(self, data: Dict[str, Any], sensitive_fields: list) -> Dict[str, Any]:
        """
        Encrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing data to encrypt
            sensitive_fields: List of field names to encrypt
            
        Returns:
            Dictionary with encrypted sensitive fields
        """
        result = data.copy()
        
        for field in sensitive_fields:
            if field in result and result[field] is not None:
                if isinstance(result[field], str):
                    result[field] = self.encrypt_string(result[field], field)
                else:
                    # Convert to JSON string before encryption
                    json_str = json.dumps(result[field], default=str)
                    result[field] = self.encrypt_string(json_str, field)
        
        return result
    
    def decrypt_dict(self, data: Dict[str, Any], sensitive_fields: list) -> Dict[str, Any]:
        """
        Decrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing encrypted data
            sensitive_fields: List of field names to decrypt
            
        Returns:
            Dictionary with decrypted sensitive fields
        """
        result = data.copy()
        
        for field in sensitive_fields:
            if field in result and result[field] is not None:
                try:
                    decrypted = self.decrypt_string(result[field], field)
                    
                    # Try to parse as JSON if it looks like JSON
                    if decrypted.startswith(('{', '[', '"')) or decrypted in ('true', 'false', 'null'):
                        try:
                            result[field] = json.loads(decrypted)
                        except json.JSONDecodeError:
                            result[field] = decrypted
                    else:
                        result[field] = decrypted
                        
                except EncryptionError as e:
                    logger.warning(f"Failed to decrypt field '{field}': {str(e)}")
                    # Keep encrypted value if decryption fails
                    pass
        
        return result
    
    def _apply_pkcs7_padding(self, data: bytes) -> bytes:
        """Apply PKCS7 padding to data."""
        pad_length = 16 - (len(data) % 16)
        padding = bytes([pad_length] * pad_length)
        return data + padding
    
    def _remove_pkcs7_padding(self, padded_data: bytes) -> bytes:
        """Remove PKCS7 padding from data."""
        if len(padded_data) == 0:
            raise EncryptionError("Cannot remove padding from empty data")
        
        pad_length = padded_data[-1]
        
        if pad_length < 1 or pad_length > 16:
            raise EncryptionError("Invalid padding")
        
        if len(padded_data) < pad_length:
            raise EncryptionError("Invalid padding length")
        
        # Check padding bytes
        for i in range(pad_length):
            if padded_data[-(i + 1)] != pad_length:
                raise EncryptionError("Invalid padding bytes")
        
        return padded_data[:-pad_length]
    
    def generate_master_key(self) -> str:
        """Generate a new random 32-byte master key."""
        key = os.urandom(32)
        return base64.b64encode(key).decode('utf-8')
    
    def create_encrypted_index_value(self, plaintext: str, context: str = "") -> str:
        """
        Create a deterministic hash for encrypted fields to enable indexing.
        This is a one-way operation for database indexes on encrypted fields.
        
        Args:
            plaintext: The original value
            context: Context for key derivation
            
        Returns:
            Hex-encoded hash suitable for database indexing
        """
        # Use HMAC-SHA256 with context-specific key for deterministic hashing
        if context:
            hmac_key = self._derive_key(
                self.master_key, 
                f"index_{context}".encode('utf-8')[:16].ljust(16, b'\0'), 
                32
            )
        else:
            hmac_key = self.master_key
        
        import hmac
        hash_value = hmac.new(
            hmac_key,
            plaintext.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hash_value


class SensitiveDataManager:
    """
    Manager for handling sensitive data encryption in the application.
    Provides high-level methods for common data protection patterns.
    """
    
    def __init__(self, encryption_service: AESEncryptionService):
        self.encryption_service = encryption_service
        
        # Define which fields are considered sensitive
        self.sensitive_user_fields = [
            'email',  # Email addresses
            'phone',  # Phone numbers
            'address',  # Physical addresses
            'ssn',    # Social security numbers
            'medical_id',  # Medical record numbers
            'emergency_contact',  # Emergency contact info
        ]
        
        self.sensitive_medical_fields = [
            'patient_name',
            'patient_dob',
            'patient_ssn',
            'diagnosis',
            'medical_notes',
            'prescription_details',
            'treatment_plan',
        ]
        
        self.sensitive_document_fields = [
            'content',  # Document content might contain PII
            'metadata',  # Metadata might contain sensitive info
            'extracted_entities',  # Extracted medical entities
        ]
    
    def encrypt_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive fields in user data."""
        return self.encryption_service.encrypt_dict(user_data, self.sensitive_user_fields)
    
    def decrypt_user_data(self, encrypted_user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive fields in user data."""
        return self.encryption_service.decrypt_dict(encrypted_user_data, self.sensitive_user_fields)
    
    def encrypt_medical_data(self, medical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive fields in medical data."""
        return self.encryption_service.encrypt_dict(medical_data, self.sensitive_medical_fields)
    
    def decrypt_medical_data(self, encrypted_medical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive fields in medical data."""
        return self.encryption_service.decrypt_dict(encrypted_medical_data, self.sensitive_medical_fields)
    
    def encrypt_document_data(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive fields in document data."""
        return self.encryption_service.encrypt_dict(document_data, self.sensitive_document_fields)
    
    def decrypt_document_data(self, encrypted_document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive fields in document data."""
        return self.encryption_service.decrypt_dict(encrypted_document_data, self.sensitive_document_fields)
    
    def create_searchable_hash(self, value: str, field_type: str) -> str:
        """
        Create a searchable hash for encrypted fields.
        This allows database queries on encrypted data.
        """
        return self.encryption_service.create_encrypted_index_value(value, field_type)
    
    def log_encryption_event(self, operation: str, data_type: str, 
                            field_count: int = 1, user_id: Optional[str] = None):
        """Log encryption/decryption events for audit trail."""
        from services.security_logger import security_logger, SecurityEventType
        
        event_type = (SecurityEventType.DATA_ENCRYPTION_EVENT 
                     if operation == 'encrypt' 
                     else SecurityEventType.DATA_DECRYPTION_EVENT)
        
        details = {
            'operation': operation,
            'data_type': data_type,
            'field_count': field_count,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        security_logger.log_security_event(
            event_type=event_type,
            ip_address="system",  # Internal system operation
            username=user_id,
            details=details
        )


# Initialize global encryption services
def get_encryption_service() -> AESEncryptionService:
    """Get the global encryption service instance."""
    try:
        return AESEncryptionService()
    except EncryptionError:
        # Generate a new master key if none exists (development only)
        logger.warning("No encryption master key found, generating new one for development")
        import os
        # Generate a temporary key for development
        temp_key = os.urandom(32)
        temp_key_b64 = base64.b64encode(temp_key).decode('utf-8')
        logger.info("Generated temporary encryption key for development")
        logger.warning("IMPORTANT: This is a temporary key - configure ENCRYPTION_MASTER_KEY environment variable")
        return AESEncryptionService(temp_key_b64)

# Global instances
encryption_service = get_encryption_service()
sensitive_data_manager = SensitiveDataManager(encryption_service) 