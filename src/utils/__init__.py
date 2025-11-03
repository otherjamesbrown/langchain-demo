"""
utils: Shared utilities and helpers

This module contains shared utilities for:
- Model configuration and availability
- Database operations
- Monitoring utilities
- Streamlit helpers
"""

from src.utils.model_availability import (
    get_available_models,
    check_provider_packages_installed,
    is_placeholder_api_key,
    is_local_model_usable,
    is_remote_model_usable,
)
from src.utils.database import get_db_session
from src.utils.streamlit_helpers import (
    get_streamlit_db_session,
    init_streamlit_db,
)

__all__ = [
    "get_available_models",
    "check_provider_packages_installed",
    "is_placeholder_api_key",
    "is_local_model_usable",
    "is_remote_model_usable",
    "get_db_session",
    "get_streamlit_db_session",
    "init_streamlit_db",
]

