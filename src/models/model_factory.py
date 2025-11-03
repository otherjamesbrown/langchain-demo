"""
Model factory for abstracting local and remote LLM providers.

This module provides a unified interface for working with different LLM providers,
allowing easy switching between local models (Llama) and remote APIs (OpenAI, Anthropic).
"""

import os
from pathlib import Path
from typing import Literal
from langchain_core.language_models import BaseLanguageModel
from langchain_core.language_models.chat_models import BaseChatModel

from src.models.local_registry import (
    DEFAULT_LOCAL_MODEL_KEY,
    get_local_model_config,
    guess_local_model_key,
    list_local_models,
)

# Import LLM providers
try:
    from langchain_community.llms import LlamaCpp
except ImportError:
    LlamaCpp = None

try:
    from langchain_community.chat_models import ChatLlamaCpp
except ImportError:
    ChatLlamaCpp = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None


ModelType = Literal["local", "openai", "anthropic", "gemini"]


def _fetch_api_key(provider: str) -> str | None:
    """Retrieve an API key from the database (primary) or environment (fallback)."""

    try:
        from src.database.operations import get_api_key
    except ImportError:
        return None

    try:
        # Try database first
        db_key = get_api_key(provider)
        if db_key:
            return db_key
    except Exception:
        pass
    
    # Fallback to environment variable
    env_vars = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GOOGLE_API_KEY",
    }
    env_var = env_vars.get(provider)
    if env_var:
        return os.getenv(env_var)
    
    return None


def _fetch_app_setting(key: str, default: str | None = None) -> str | None:
    """Retrieve an app setting from the database (primary) or environment (fallback)."""
    
    try:
        from src.database.operations import get_app_setting
        db_value = get_app_setting(key)
        if db_value:
            return db_value
    except Exception:
        pass
    
    # Fallback to environment variable
    return os.getenv(key, default)


def get_llm(
    model_type: ModelType | None = None,
    model_path: str | None = None,
    temperature: float = 0.7,
    local_model_name: str | None = None,
    **kwargs
) -> BaseLanguageModel:
    """
    Factory function to create an LLM instance based on configuration.
    
    Args:
        model_type: Type of model to use ('local', 'openai', 'anthropic', 'gemini')
                   If None, reads from MODEL_TYPE environment variable
        model_path: Path to local model file (required for 'local' type)
                    If None, reads from MODEL_PATH environment variable
        temperature: Sampling temperature (0-2), default 0.7
        **kwargs: Additional model-specific parameters
        
    Returns:
        BaseLanguageModel instance configured for the specified provider
        
    Raises:
        ValueError: If model_type or required configuration is invalid
        ImportError: If required packages are not installed
    """
    # Get model type: parameter > database > env > default
    if model_type is None:
        db_model_type = _fetch_app_setting("MODEL_TYPE")
        model_type = (db_model_type or os.getenv("MODEL_TYPE", "local")).lower()
    
    if model_type not in ["local", "openai", "anthropic", "gemini"]:
        raise ValueError(f"Invalid model_type: {model_type}")
    
    # Get temperature: parameter > database > env > default
    temp_str = _fetch_app_setting("TEMPERATURE") or os.getenv("TEMPERATURE")
    if temp_str:
        temp = float(temp_str)
    else:
        temp = temperature
    
    # Create appropriate LLM instance
    if model_type == "local":
        return _create_local_llm(
            model_path=model_path,
            temperature=temp,
            local_model_name=local_model_name,
            **kwargs,
        )
    elif model_type == "openai":
        return _create_openai_llm(temp, **kwargs)
    elif model_type == "anthropic":
        return _create_anthropic_llm(temp, **kwargs)
    elif model_type == "gemini":
        return _create_gemini_llm(temp, **kwargs)
    else:
        raise ValueError(f"Unknown model type: {model_type}")


def get_chat_model(
    model_type: ModelType | None = None,
    model_path: str | None = None,
    temperature: float = 0.7,
    local_model_name: str | None = None,
    **kwargs
) -> BaseChatModel:
    """Create a chat-compatible LLM instance for agent workflows.

    This helper mirrors :func:`get_llm` but guarantees the returned
    model implements the chat model interface required by LangChain's
    agent factory. It keeps configuration in one place so educational
    examples can highlight the difference between text-completion and
    chat-first APIs.

    Args:
        model_type: Provider identifier. Falls back to ``MODEL_TYPE`` env var.
        model_path: Local model path when using the ``local`` provider.
        temperature: Sampling temperature.
        **kwargs: Provider-specific overrides (e.g., ``n_gpu_layers`` for LlamaCpp).

    Returns:
        A :class:`BaseChatModel` ready for agent execution.

    Raises:
        ValueError: If configuration is incomplete.
        ImportError: If the required provider package is missing.
    """
    # Get model type: parameter > database > env > default
    if model_type is None:
        db_model_type = _fetch_app_setting("MODEL_TYPE")
        model_type = (db_model_type or os.getenv("MODEL_TYPE", "local")).lower()

    if model_type not in ["local", "openai", "anthropic", "gemini"]:
        raise ValueError(f"Invalid model_type: {model_type}")

    # Get temperature: parameter > database > env > default
    temp_str = _fetch_app_setting("TEMPERATURE") or os.getenv("TEMPERATURE")
    if temp_str:
        temp = float(temp_str)
    else:
        temp = temperature

    if model_type == "local":
        return _create_local_chat_model(
            model_path=model_path,
            temperature=temp,
            local_model_name=local_model_name,
            **kwargs,
        )
    if model_type == "openai":
        return _create_openai_llm(temp, **kwargs)
    if model_type == "anthropic":
        return _create_anthropic_llm(temp, **kwargs)
    if model_type == "gemini":
        return _create_gemini_llm(temp, **kwargs)

    raise ValueError(f"Unknown model type: {model_type}")


def _select_local_model(
    model_path: str | None,
    local_model_name: str | None,
) -> tuple[Path, str, int | None, str | None, str | None]:
    """
    Resolve the local model to use and return metadata for downstream use.
    
    Priority order:
    1. Function parameters (model_path or local_model_name)
    2. Database (last used model configuration)
    3. Environment variables (MODEL_PATH or LOCAL_MODEL_NAME)
    4. Code registry default
    """
    
    # First, try to get model from database (last used model)
    try:
        from src.database.operations import get_default_model_configuration
        db_model = get_default_model_configuration()
        if db_model and db_model.provider == "local":
            # Database has a local model configured
            if db_model.model_path:
                resolved = Path(db_model.model_path).expanduser()
                if not resolved.is_absolute():
                    resolved = Path(__file__).resolve().parent.parent.parent / resolved
                resolved = resolved.resolve()
                
                # Get metadata from database or registry
                metadata = db_model.extra_metadata or {}
                context_window = metadata.get("context_window")
                chat_format = metadata.get("chat_format")
                display_name = db_model.name
                registry_key = db_model.model_key
                
                # If no registry key, try to guess from path
                if not registry_key:
                    registry_key = guess_local_model_key(resolved)
                
                return resolved, display_name, context_window, registry_key, chat_format
    except Exception:
        pass  # Fallback to other sources
    
    # Fallback to parameter or environment
    candidate_path = model_path or os.getenv("MODEL_PATH")
    if candidate_path:
        resolved = Path(candidate_path).expanduser()
        if not resolved.is_absolute():
            resolved = Path(__file__).resolve().parent.parent.parent / resolved
        resolved = resolved.resolve()
        registry_key = guess_local_model_key(resolved)
        context_window: int | None = None
        display_name = resolved.name
        chat_format: str | None = None
        if registry_key:
            try:
                config = get_local_model_config(registry_key)
                context_window = config.context_window
                display_name = config.display_name
                chat_format = config.chat_format
            except KeyError:
                pass
        return resolved, display_name, context_window, registry_key, chat_format

    # Fallback to registry key from parameter or env
    registry_key = (
        local_model_name
        or os.getenv("LOCAL_MODEL_NAME")
        or DEFAULT_LOCAL_MODEL_KEY
    ).strip()
    normalized_key = registry_key.lower()

    try:
        config = get_local_model_config(normalized_key)
    except KeyError as exc:
        available = ", ".join(cfg.key for cfg in list_local_models())
        raise ValueError(
            f"Unknown local model '{registry_key}'. Available options: {available}"
        ) from exc

    resolved = config.resolve_path().expanduser().resolve()
    return resolved, config.display_name, config.context_window, config.key, config.chat_format


def _create_local_llm(
    model_path: str | None,
    temperature: float,
    local_model_name: str | None = None,
    **kwargs
) -> BaseLanguageModel:
    """Create a local LlamaCpp LLM instance."""
    if LlamaCpp is None:
        raise ImportError(
            "LlamaCpp is not installed. Install with: pip install llama-cpp-python"
        )
    
    resolved_path, _, suggested_ctx, _, _ = _select_local_model(
        model_path=model_path,
        local_model_name=local_model_name,
    )

    if not resolved_path.exists():
        raise FileNotFoundError(
            "Model file not found: "
            f"{resolved_path}. Download the model or update the registry entry."
        )

    # LlamaCpp parameters
    llama_params = {
        "model_path": str(resolved_path),
        "temperature": temperature,
        "n_ctx": kwargs.get("n_ctx", suggested_ctx or 4096),  # Context window
        "n_gpu_layers": kwargs.get("n_gpu_layers", -1),  # Use all GPU layers
        "verbose": kwargs.get("verbose", False),
        "n_batch": kwargs.get("n_batch", 512),  # Batch size for processing
    }
    
    return LlamaCpp(**llama_params)


def _create_local_chat_model(
    model_path: str | None,
    temperature: float,
    local_model_name: str | None = None,
    **kwargs
) -> BaseChatModel:
    """Create a local ChatLlamaCpp instance for agent interactions."""
    if ChatLlamaCpp is None:
        raise ImportError(
            "ChatLlamaCpp is not installed. Install with: pip install llama-cpp-python"
        )

    resolved_path, _, suggested_ctx, _, chat_format = _select_local_model(
        model_path=model_path,
        local_model_name=local_model_name,
    )

    if not resolved_path.exists():
        raise FileNotFoundError(
            "Model file not found: "
            f"{resolved_path}. Download the model or update the registry entry."
        )

    llama_params = {
        "model_path": str(resolved_path),
        "temperature": temperature,
        "n_ctx": kwargs.get("n_ctx", suggested_ctx or 4096),
        "n_gpu_layers": kwargs.get("n_gpu_layers", -1),
        "verbose": kwargs.get("verbose", False),
        "n_batch": kwargs.get("n_batch", 512),
    }

    # Set n_predict directly in constructor - this is what llama-cpp-python uses
    # n_predict controls the maximum number of tokens to generate (prevents truncation)
    if "max_tokens" in kwargs:
        # Pass n_predict directly to ChatLlamaCpp constructor
        # This is the parameter name that llama-cpp-python actually uses
        llama_params["n_predict"] = kwargs["max_tokens"]
    elif suggested_ctx:
        # Default to half the context window if not specified
        # This matches the default used in database operations
        llama_params["n_predict"] = max(suggested_ctx // 2, 512)

    if chat_format and "chat_format" not in kwargs:
        llama_params["chat_format"] = chat_format

    return ChatLlamaCpp(**llama_params)


def _create_openai_llm(temperature: float, **kwargs) -> BaseLanguageModel:
    """Create an OpenAI Chat model instance."""
    if ChatOpenAI is None:
        raise ImportError(
            "OpenAI is not installed. Install with: pip install langchain-openai"
        )
    
    api_key = _fetch_api_key("openai")
    if not api_key:
        raise ValueError(
            "OpenAI API key is required. Set it in the database or OPENAI_API_KEY environment variable"
        )
    
    # Get model name: parameter > database config > env > default
    model_name = kwargs.get("model_name")
    if not model_name:
        # Try to get from database model configuration
        try:
            from src.database.operations import get_default_model_configuration
            db_model = get_default_model_configuration()
            if db_model and db_model.provider == "openai" and db_model.api_identifier:
                model_name = db_model.api_identifier
        except Exception:
            pass
        
        if not model_name:
            model_name = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        **{k: v for k, v in kwargs.items() if k not in ["model_name"]}
    )


def _create_anthropic_llm(temperature: float, **kwargs) -> BaseLanguageModel:
    """Create an Anthropic Claude Chat model instance."""
    if ChatAnthropic is None:
        raise ImportError(
            "Anthropic is not installed. Install with: pip install langchain-anthropic"
        )
    
    api_key = _fetch_api_key("anthropic")
    if not api_key:
        raise ValueError(
            "Anthropic API key is required. Set it in the database or ANTHROPIC_API_KEY environment variable"
        )
    
    # Get model name: parameter > database config > env > default
    model_name = kwargs.get("model_name")
    if not model_name:
        # Try to get from database model configuration
        try:
            from src.database.operations import get_default_model_configuration
            db_model = get_default_model_configuration()
            if db_model and db_model.provider == "anthropic" and db_model.api_identifier:
                model_name = db_model.api_identifier
        except Exception:
            pass
        
        if not model_name:
            model_name = os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
    
    return ChatAnthropic(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        **{k: v for k, v in kwargs.items() if k not in ["model_name"]}
    )


def _create_gemini_llm(temperature: float, **kwargs) -> BaseLanguageModel:
    """Create a Google Gemini Chat model instance."""
    if ChatGoogleGenerativeAI is None:
        raise ImportError(
            "Google Generative AI is not installed. Install with: pip install langchain-google-genai"
        )
    
    api_key = _fetch_api_key("gemini")
    if not api_key:
        raise ValueError(
            "Google API key is required. Set it in the database or GOOGLE_API_KEY environment variable"
        )
    
    # Get model name: parameter > database config > env > default
    model_name = kwargs.get("model") or kwargs.get("model_name")
    if not model_name:
        # Try to get from database model configuration
        try:
            from src.database.operations import get_default_model_configuration
            db_model = get_default_model_configuration()
            if db_model and db_model.provider == "gemini" and db_model.api_identifier:
                model_name = db_model.api_identifier
        except Exception:
            pass
        
        if not model_name:
            model_name = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        google_api_key=api_key,
        **{k: v for k, v in kwargs.items() if k not in ["model", "model_name"]}
    )


def list_available_providers() -> list[str]:
    """
    List available LLM providers based on installed packages.
    
    Returns:
        List of provider names that are available
    """
    providers = []
    
    if LlamaCpp is not None:
        providers.append("local")
    
    if ChatOpenAI is not None:
        providers.append("openai")
    
    if ChatAnthropic is not None:
        providers.append("anthropic")
    
    if ChatGoogleGenerativeAI is not None:
        providers.append("gemini")
    
    return providers

