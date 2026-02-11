class NotFoundException(Exception):
    """Exception raised when a resource is not found."""
    def __init__(self, message: str):
        super().__init__(message)

class ValidationException(Exception):
    """Exception raised for validation errors."""
    def __init__(self, message: str):
        super().__init__(message)

class DatabaseException(Exception):
    """Exception raised for database errors."""
    def __init__(self, message: str):
        super().__init__(message) 