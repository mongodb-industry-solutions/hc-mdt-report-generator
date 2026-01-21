from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging
from pymongo.errors import DuplicateKeyError
from bson import ObjectId

from config.database import MongoDBConnection
from domain.entities.user import User, UserCreate, UserUpdate, UserStatus
from services.auth.password_service import password_service
from utils.exceptions import DatabaseException, ValidationException, NotFoundException

logger = logging.getLogger(__name__)

class UserRepository:
    """
    User repository for secure database operations.
    Implements Phase 2 security requirements for user management.
    """
    
    def __init__(self):
        self.collection_name = "users"
    
    async def create_user(self, user_create: UserCreate, created_by: Optional[str] = None) -> User:
        """
        Create new user with secure password hashing.
        
        Args:
            user_create: User creation data
            created_by: ID of user creating this user (for audit)
            
        Returns:
            Created User object
            
        Raises:
            ValidationException: If user data is invalid
            DatabaseException: If database operation fails
        """
        try:
            # Hash password with bcrypt
            password_hash = password_service.hash_password(user_create.password)
            
            # Create user document
            now = datetime.now(timezone.utc)
            user_doc = {
                "_id": str(ObjectId()),
                "username": user_create.username,
                "email": user_create.email,
                "password_hash": password_hash,
                "first_name": user_create.first_name,
                "last_name": user_create.last_name,
                "role": user_create.role.value,
                "status": UserStatus.ACTIVE.value,
                "failed_login_attempts": 0,
                "account_locked_until": None,
                "last_login": None,
                "password_changed_at": now,
                "created_at": now,
                "updated_at": now,
                "created_by": created_by,
                "updated_by": created_by,
                "require_password_change": False,
                "two_factor_enabled": False
            }
            
            with MongoDBConnection() as db:
                collection = db[self.collection_name]
                
                # Insert user with unique constraint handling
                try:
                    result = collection.insert_one(user_doc)
                    logger.info(f"User created successfully: {user_create.username}")
                    
                    # Return created user
                    created_user_doc = collection.find_one({"_id": result.inserted_id})
                    return User(**created_user_doc)
                    
                except DuplicateKeyError as e:
                    error_msg = "Username or email already exists"
                    if "username" in str(e):
                        error_msg = f"Username '{user_create.username}' already exists"
                    elif "email" in str(e):
                        error_msg = f"Email '{user_create.email}' already exists"
                    
                    logger.warning(f"User creation failed - duplicate: {error_msg}")
                    raise ValidationException(error_msg)
                
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Failed to create user {user_create.username}: {e}")
            raise DatabaseException(f"Failed to create user: {str(e)}")
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID to find
            
        Returns:
            User object if found, None otherwise
        """
        try:
            with MongoDBConnection() as db:
                collection = db[self.collection_name]
                user_doc = collection.find_one({"_id": user_id})
                
                if user_doc:
                    return User(**user_doc)
                    
        except Exception as e:
            logger.error(f"Failed to get user by ID {user_id}: {e}")
        
        return None
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username for authentication.
        
        Args:
            username: Username to find
            
        Returns:
            User object if found, None otherwise
        """
        try:
            with MongoDBConnection() as db:
                collection = db[self.collection_name]
                user_doc = collection.find_one({"username": username})
                
                if user_doc:
                    return User(**user_doc)
                    
        except Exception as e:
            logger.error(f"Failed to get user by username {username}: {e}")
        
        return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: Email address to find
            
        Returns:
            User object if found, None otherwise
        """
        try:
            with MongoDBConnection() as db:
                collection = db[self.collection_name]
                user_doc = collection.find_one({"email": email})
                
                if user_doc:
                    return User(**user_doc)
                    
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
        
        return None
    
    async def update_user(self, user_id: str, user_update: UserUpdate, updated_by: Optional[str] = None) -> Optional[User]:
        """
        Update user information.
        
        Args:
            user_id: User ID to update
            user_update: Update data
            updated_by: ID of user making the update
            
        Returns:
            Updated User object if successful, None otherwise
        """
        try:
            update_data = {}
            
            # Build update document
            if user_update.first_name is not None:
                update_data["first_name"] = user_update.first_name
            if user_update.last_name is not None:
                update_data["last_name"] = user_update.last_name
            if user_update.email is not None:
                update_data["email"] = user_update.email
            if user_update.role is not None:
                update_data["role"] = user_update.role.value
            if user_update.status is not None:
                update_data["status"] = user_update.status.value
            
            if not update_data:
                return await self.get_user_by_id(user_id)
            
            # Add audit fields
            update_data["updated_at"] = datetime.now(timezone.utc)
            if updated_by:
                update_data["updated_by"] = updated_by
            
            with MongoDBConnection() as db:
                collection = db[self.collection_name]
                
                result = collection.update_one(
                    {"_id": user_id},
                    {"$set": update_data}
                )
                
                if result.modified_count > 0:
                    logger.info(f"User {user_id} updated successfully")
                    return await self.get_user_by_id(user_id)
                    
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
        
        return None
    
    async def update_password(self, user_id: str, new_password: str, updated_by: Optional[str] = None) -> bool:
        """
        Update user password with secure hashing.
        
        Args:
            user_id: User ID to update
            new_password: New plain text password
            updated_by: ID of user making the update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Hash new password
            password_hash = password_service.hash_password(new_password)
            
            update_data = {
                "password_hash": password_hash,
                "password_changed_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "require_password_change": False
            }
            
            if updated_by:
                update_data["updated_by"] = updated_by
            
            with MongoDBConnection() as db:
                collection = db[self.collection_name]
                
                result = collection.update_one(
                    {"_id": user_id},
                    {"$set": update_data}
                )
                
                if result.modified_count > 0:
                    logger.info(f"Password updated for user {user_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to update password for user {user_id}: {e}")
        
        return False
    
    async def increment_failed_login(self, user_id: str) -> bool:
        """
        Increment failed login attempts counter.
        
        Args:
            user_id: User ID to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with MongoDBConnection() as db:
                collection = db[self.collection_name]
                
                result = collection.update_one(
                    {"_id": user_id},
                    {
                        "$inc": {"failed_login_attempts": 1},
                        "$set": {"updated_at": datetime.now(timezone.utc)}
                    }
                )
                
                return result.modified_count > 0
                
        except Exception as e:
            logger.error(f"Failed to increment failed login for user {user_id}: {e}")
            return False
    
    async def reset_failed_login(self, user_id: str) -> bool:
        """
        Reset failed login attempts and update last login.
        
        Args:
            user_id: User ID to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            now = datetime.now(timezone.utc)
            
            with MongoDBConnection() as db:
                collection = db[self.collection_name]
                
                result = collection.update_one(
                    {"_id": user_id},
                    {
                        "$set": {
                            "failed_login_attempts": 0,
                            "last_login": now,
                            "updated_at": now
                        }
                    }
                )
                
                return result.modified_count > 0
                
        except Exception as e:
            logger.error(f"Failed to reset failed login for user {user_id}: {e}")
            return False
    
    async def lock_account(self, user_id: str, duration_minutes: int = 15) -> bool:
        """
        Lock user account for specified duration.
        
        Args:
            user_id: User ID to lock
            duration_minutes: Lock duration in minutes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from datetime import timedelta
            lock_until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
            
            with MongoDBConnection() as db:
                collection = db[self.collection_name]
                
                result = collection.update_one(
                    {"_id": user_id},
                    {
                        "$set": {
                            "account_locked_until": lock_until,
                            "status": UserStatus.LOCKED.value,
                            "updated_at": datetime.now(timezone.utc)
                        }
                    }
                )
                
                if result.modified_count > 0:
                    logger.warning(f"Account locked for user {user_id} until {lock_until}")
                    return True
                
        except Exception as e:
            logger.error(f"Failed to lock account for user {user_id}: {e}")
        
        return False
    
    async def unlock_account(self, user_id: str) -> bool:
        """
        Unlock user account and reset failed attempts.
        
        Args:
            user_id: User ID to unlock
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with MongoDBConnection() as db:
                collection = db[self.collection_name]
                
                result = collection.update_one(
                    {"_id": user_id},
                    {
                        "$set": {
                            "account_locked_until": None,
                            "failed_login_attempts": 0,
                            "status": UserStatus.ACTIVE.value,
                            "updated_at": datetime.now(timezone.utc)
                        }
                    }
                )
                
                if result.modified_count > 0:
                    logger.info(f"Account unlocked for user {user_id}")
                    return True
                
        except Exception as e:
            logger.error(f"Failed to unlock account for user {user_id}: {e}")
        
        return False
    
    async def delete_user(self, user_id: str) -> bool:
        """
        Soft delete user by setting status to inactive.
        
        Args:
            user_id: User ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with MongoDBConnection() as db:
                collection = db[self.collection_name]
                
                result = collection.update_one(
                    {"_id": user_id},
                    {
                        "$set": {
                            "status": UserStatus.INACTIVE.value,
                            "updated_at": datetime.now(timezone.utc)
                        }
                    }
                )
                
                if result.modified_count > 0:
                    logger.info(f"User {user_id} soft deleted")
                    return True
                
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
        
        return False
    
    async def list_users(self, limit: int = 100, offset: int = 0, filters: Optional[Dict[str, Any]] = None) -> List[User]:
        """
        List users with pagination and filtering.
        
        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            filters: Optional filters to apply
            
        Returns:
            List of User objects
        """
        try:
            query = {}
            
            # Apply filters
            if filters:
                if "status" in filters:
                    query["status"] = filters["status"]
                if "role" in filters:
                    query["role"] = filters["role"]
                if "search" in filters:
                    # Search in username, email, first_name, last_name
                    search_term = filters["search"]
                    query["$or"] = [
                        {"username": {"$regex": search_term, "$options": "i"}},
                        {"email": {"$regex": search_term, "$options": "i"}},
                        {"first_name": {"$regex": search_term, "$options": "i"}},
                        {"last_name": {"$regex": search_term, "$options": "i"}}
                    ]
            
            with MongoDBConnection() as db:
                collection = db[self.collection_name]
                
                cursor = collection.find(query).skip(offset).limit(limit).sort("created_at", -1)
                users = []
                
                for user_doc in cursor:
                    users.append(User(**user_doc))
                
                return users
                
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            return []
    
    async def count_users(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count users with optional filtering.
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            Number of users matching criteria
        """
        try:
            query = {}
            
            if filters:
                if "status" in filters:
                    query["status"] = filters["status"]
                if "role" in filters:
                    query["role"] = filters["role"]
            
            with MongoDBConnection() as db:
                collection = db[self.collection_name]
                return collection.count_documents(query)
                
        except Exception as e:
            logger.error(f"Failed to count users: {e}")
            return 0

# Global user repository instance
user_repository = UserRepository() 