#!/usr/bin/env python3
"""
Model Availability Utilities

Centralized module for validating and retrieving available models from the database.
This provides a single source of truth for:
- Checking if provider packages are installed
- Validating API keys (not placeholders)
- Checking if local model files exist
- Getting filtered lists of available models

Educational Focus:
- Demonstrates DRY (Don't Repeat Yourself) principle
- Shows how to create reusable validation utilities
- Centralizes business logic for easier maintenance
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from sqlalchemy.orm import Session

from src.database.schema import get_session, create_database
from src.database.operations import (
    get_model_configurations,
    get_api_key,
    ensure_default_configuration,
)


# Placeholder keys that should be filtered out
PLACEHOLDER_API_KEYS = [
    "",
    "your_openai_api_key_here",
    "your_anthropic_key_here",
    "your_gemini_api_key_here",
    "sk-your_openai_key_here",
    "sk-ant-your_anthropic_key_here",
]


def is_placeholder_api_key(api_key: str) -> bool:
    """
    Check if an API key is a placeholder value.
    
    Educational: This function helps distinguish between real API keys
    and placeholder values that might be in the database. This is important
    for filtering out models that can't actually be used.
    
    Args:
        api_key: The API key to check
        
    Returns:
        True if the key is a placeholder, False otherwise
    """
    if not api_key or not api_key.strip():
        return True
    
    # Check against known placeholders
    if api_key in PLACEHOLDER_API_KEYS:
        return True
    
    # Check for common placeholder patterns
    placeholder_patterns = [
        "placeholder",
        "your_",
        "sk-ant-your_",
        "api_key_here",
    ]
    
    api_key_lower = api_key.lower()
    for pattern in placeholder_patterns:
        if pattern in api_key_lower:
            return True
    
    return False


def check_provider_packages_installed(provider: str) -> bool:
    """
    Check if required packages are installed for a provider.
    
    Educational: This validates that the necessary Python packages are
    available before trying to use a model from that provider. Different
    providers require different LangChain integration packages.
    
    Args:
        provider: Provider name ("local", "openai", "anthropic", "gemini")
        
    Returns:
        True if packages are installed, False otherwise
    """
    try:
        if provider == "openai":
            try:
                __import__("langchain_openai")
                return True
            except ImportError:
                try:
                    __import__("openai")
                    return True
                except ImportError:
                    return False
        
        elif provider == "anthropic":
            try:
                __import__("langchain_anthropic")
                return True
            except ImportError:
                try:
                    __import__("anthropic")
                    return True
                except ImportError:
                    return False
        
        elif provider == "gemini":
            try:
                __import__("langchain_google_genai")
                return True
            except ImportError:
                try:
                    __import__("google.generativeai")
                    return True
                except ImportError:
                    return False
        
        elif provider == "local":
            try:
                __import__("llama_cpp")
                return True
            except ImportError:
                try:
                    __import__("llama_cpp_python")
                    return True
                except ImportError:
                    return False
        
    except ImportError:
        return False
    
    return False


def is_local_model_usable(model_path: Optional[str]) -> bool:
    """
    Check if a local model file exists and is usable.
    
    Educational: Local models require the actual model file (.gguf) to exist
    on disk. This function validates both direct paths and paths with home
    directory expansion (~).
    
    Args:
        model_path: Path to the model file (may include ~ expansion)
        
    Returns:
        True if model file exists, False otherwise
    """
    if not model_path:
        return False
    
    # Try direct path
    if os.path.exists(model_path):
        return True
    
    # Try expanding user home directory (~)
    expanded_path = os.path.expanduser(model_path)
    if os.path.exists(expanded_path):
        return True
    
    return False


def is_remote_model_usable(
    provider: str,
    session: Optional[Session] = None
) -> bool:
    """
    Check if a remote model has a valid (non-placeholder) API key.
    
    Educational: Remote models require API keys from their respective providers.
    This function checks both that a key exists in the database and that it's
    not just a placeholder value.
    
    Args:
        provider: Provider name ("openai", "anthropic", "gemini")
        session: Optional database session (creates new one if not provided)
        
    Returns:
        True if valid API key exists, False otherwise
    """
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    
    try:
        api_key = get_api_key(provider, session=session)
        return api_key is not None and not is_placeholder_api_key(api_key)
    finally:
        if close_session:
            session.close()


def get_available_models(
    provider_filter: Optional[List[str]] = None,
    session: Optional[Session] = None,
    include_reasons: bool = False,
) -> List[Dict[str, Any]] | Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Get available model configurations from database.
    
    Educational: This is the central function for getting usable models.
    It validates:
    1. Required packages are installed
    2. Local models have existing model files
    3. Remote models have valid (non-placeholder) API keys
    
    This function serves as the single source of truth for model availability
    across CLI tools, UI pages, and test scripts.
    
    Args:
        provider_filter: Optional list of provider names to filter by
        session: Optional database session (creates new one if not provided)
        include_reasons: If True, return tuple of (models, skip_reasons)
        
    Returns:
        If include_reasons=False: List of model configuration dicts
        If include_reasons=True: Tuple of (models, skip_reasons dict)
        
        Each model dict contains:
        - name: Model display name
        - provider: Provider type ("local", "openai", "anthropic", "gemini")
        - config_id: Database ID of the model configuration
        - model_path: Path for local models (if applicable)
        - model_key: Model key for local models (if applicable)
        - api_identifier: API model identifier for remote models (if applicable)
    """
    close_session = False
    if session is None:
        create_database()
        session = get_session()
        close_session = True
    
    try:
        # Sync default configurations from code registry and env vars
        ensure_default_configuration(session=session)
        session.commit()
        
        # Get all active model configurations
        model_configs = get_model_configurations(session=session)
        
        available_models = []
        skip_reasons = {}
        
        for config in model_configs:
            # Apply provider filter if specified
            if provider_filter and config.provider not in provider_filter:
                continue
            
            # Check if required packages are installed
            if not check_provider_packages_installed(config.provider):
                if include_reasons:
                    skip_reasons[config.name] = (
                        f"Required packages not installed for {config.provider}"
                    )
                continue
            
            # Check if model is usable
            is_usable = False
            reason = ""
            
            if config.provider == "local":
                if is_local_model_usable(config.model_path):
                    is_usable = True
                else:
                    reason = (
                        f"Model file not found: {config.model_path}"
                        if config.model_path
                        else "No model_path configured"
                    )
            else:
                if is_remote_model_usable(config.provider, session=session):
                    is_usable = True
                else:
                    reason = f"API key not found or is placeholder for {config.provider}"
            
            if is_usable:
                model_dict = {
                    "name": config.name,
                    "provider": config.provider,
                    "config_id": config.id,
                }
                
                if config.provider == "local":
                    if config.model_path:
                        model_dict["model_path"] = config.model_path
                    if config.model_key:
                        model_dict["model_key"] = config.model_key
                else:
                    if config.api_identifier:
                        model_dict["api_identifier"] = config.api_identifier
                
                available_models.append(model_dict)
            elif include_reasons:
                skip_reasons[config.name] = reason
        
        if include_reasons:
            return available_models, skip_reasons
        
        return available_models
    
    finally:
        if close_session:
            session.close()

