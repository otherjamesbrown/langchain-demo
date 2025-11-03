"""
Database session management utilities.

This module provides reusable patterns for database session management,
eliminating code duplication across research and other modules.
"""

from contextlib import contextmanager
from typing import Optional
from sqlalchemy.orm import Session
from src.database.schema import get_session


@contextmanager
def get_db_session(session: Optional[Session] = None):
    """
    Context manager for database sessions.
    
    Provides automatic session cleanup and supports both new and existing sessions.
    
    **Usage:**
    
    Create and auto-close a new session:
    ```python
    from src.utils.database import get_db_session
    
    with get_db_session() as session:
        # Use session here
        records = session.query(Model).all()
    # Session automatically closed here
    ```
    
    Use an existing session (won't close it):
    ```python
    existing_session = get_session()
    try:
        with get_db_session(existing_session) as session:
            # Use session - it's the same object as existing_session
            records = session.query(Model).all()
        # Session NOT closed - you're responsible for cleanup
    finally:
        existing_session.close()
    ```
    
    Args:
        session: Optional existing Session object. If None, creates a new session
                 that will be closed on exit.
    
    Yields:
        Session: The database session to use
        
    Example:
        ```python
        from src.utils.database import get_db_session
        from src.database.schema import Company
        
        with get_db_session() as session:
            companies = session.query(Company).all()
        # Session automatically closed
        ```
    """
    if session is None:
        session = get_session()
        should_close = True
    else:
        should_close = False
    
    try:
        yield session
    finally:
        if should_close:
            session.close()

