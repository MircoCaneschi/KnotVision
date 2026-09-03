"""
Custom exceptions for LocalKnot application.

Provides a unified exception hierarchy for catching and handling specific 
application and database errors throughout the ViewModels.
"""
# (originally the app should have been named LocalKnot. It was changed in KnotVision later)
# (I didn't care enough to find every LocalKnot reference and change them. Thus, this may happen)
class LocalKnotError(Exception):
    """Base exception class for all LocalKnot custom exceptions."""
    pass

class DatabaseError(LocalKnotError):
    """Raised when a generic database operation fails."""
    pass

class DuplicateEntityError(DatabaseError):
    """Raised when attempting to create an entity that already exists (UNIQUE constraint violation)."""
    pass

class ForeignKeyError(DatabaseError):
    """Raised when an operation fails due to missing references (FOREIGN KEY constraint violation)."""
    pass

class EntityNotFoundError(DatabaseError):
    """Raised when a requested entity cannot be found in the database."""
    pass
