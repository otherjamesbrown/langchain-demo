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
    """Retrieve an API key from the database if available."""

    try:
        from src.database.operations import get_api_key
    except ImportError:
        return None

    try:
        return get_api_key(provider)
    except Exception:
        return None


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
    # Get model type from env or parameter
    if model_type is None:
        model_type = os.getenv("MODEL_TYPE", "local").lower()
    
    if model_type not in ["local", "openai", "anthropic", "gemini"]:
        raise ValueError(f"Invalid model_type: {model_type}")
    
    # Get temperature from env or parameter
    temp = float(os.getenv("TEMPERATURE", temperature))
    
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
    if model_type is None:
        model_type = os.getenv("MODEL_TYPE", "local").lower()

    if model_type not in ["local", "openai", "anthropic", "gemini"]:
        raise ValueError(f"Invalid model_type: {model_type}")

    temp = float(os.getenv("TEMPERATURE", temperature))

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
    """Resolve the local model to use and return metadata for downstream use."""

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

    if chat_format and "chat_format" not in kwargs:
        llama_params["chat_format"] = chat_format

    return ChatLlamaCpp(**llama_params)


def _create_openai_llm(temperature: float, **kwargs) -> BaseLanguageModel:
    """Create an OpenAI Chat model instance."""
    if ChatOpenAI is None:
        raise ImportError(
            "OpenAI is not installed. Install with: pip install langchain-openai"
        )
    
    api_key = os.getenv("OPENAI_API_KEY") or _fetch_api_key("openai")
    if not api_key:
        raise ValueError(
            "OpenAI API key is required. Set OPENAI_API_KEY environment variable"
        )
    
    model_name = kwargs.get("model_name", os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"))
    
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
    
    api_key = os.getenv("ANTHROPIC_API_KEY") or _fetch_api_key("anthropic")
    if not api_key:
        raise ValueError(
            "Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable"
        )
    
    model_name = kwargs.get("model_name", os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229"))
    
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
    
    api_key = os.getenv("GOOGLE_API_KEY") or _fetch_api_key("gemini")
    if not api_key:
        raise ValueError(
            "Google API key is required. Set GOOGLE_API_KEY environment variable"
        )
    
    # Support both 'model' and 'model_name' kwargs for consistency
    model_name = kwargs.get("model") or kwargs.get("model_name", os.getenv("GEMINI_MODEL", "gemini-flash-latest"))
    
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

