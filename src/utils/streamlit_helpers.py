"""
Streamlit-specific utility functions.

This module provides shared utilities for Streamlit UI pages, including
database initialization and common UI patterns.
"""

import streamlit as st
from sqlalchemy.orm import Session
from src.database.schema import create_database, get_session


@st.cache_resource
def get_streamlit_db_session() -> Session:
    """
    Get database session for Streamlit pages (cached).
    
    This function is cached using Streamlit's @st.cache_resource decorator,
    so the database connection is reused across page reloads within the same
    Streamlit session.
    
    Returns:
        SQLAlchemy Session object
        
    Raises:
        Exception: If database connection fails
        
    Example:
        ```python
        from src.utils.streamlit_helpers import get_streamlit_db_session
        
        session = get_streamlit_db_session()
        # Use session...
        ```
    """
    create_database()
    return get_session()


def init_streamlit_db() -> Session:
    """
    Initialize database for Streamlit pages with error handling.
    
    This function provides a standardized way to initialize the database
    connection in Streamlit pages, with consistent error handling and user
    feedback.
    
    **Behavior:**
    - Creates database tables if they don't exist
    - Gets a cached database session
    - Displays error message to user if connection fails
    - Stops Streamlit execution on error
    
    Returns:
        SQLAlchemy Session object
        
    Exits:
        Calls st.stop() if database connection fails, preventing further
        page execution.
        
    Example:
        ```python
        from src.utils.streamlit_helpers import init_streamlit_db
        
        # At the top of your Streamlit page
        session = init_streamlit_db()  # Handles errors internally
        
        # Rest of your page code...
        ```
    """
    try:
        return get_streamlit_db_session()
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        st.stop()
        raise  # Will never execute but helps type checkers

