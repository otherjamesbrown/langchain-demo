"""
Structured Output Strategy Selector for LangChain Agents

This module provides a centralized way to select the appropriate structured output
strategy based on the model's capabilities. LangChain v1 provides two strategies:

1. **ProviderStrategy**: Uses the model provider's native structured output API
   - More efficient and reliable
   - Only works with specific models (GPT-4o, GPT-4 Turbo, Claude 3, Gemini)

2. **ToolStrategy**: Uses artificial tool calling to generate structured output
   - Works with any model that supports tool calling
   - Less efficient but more compatible

3. **None**: No structured output (rely on prompt engineering and manual parsing)
   - Required for local models (ChatLlamaCpp) that don't support either strategy

Educational Focus:
- Shows how different models have different capabilities
- Demonstrates fallback strategies when native features aren't available
- Helps learners understand the tradeoffs between strategies
"""

from __future__ import annotations

import re
from typing import Optional, Any
from langchain.agents.structured_output import ProviderStrategy, ToolStrategy
from langchain_core.language_models.chat_models import BaseChatModel

from src.tools.models import CompanyInfo


class StructuredOutputSelector:
    """
    Centralized selector for choosing the best structured output strategy.
    
    This class encapsulates the logic for determining which strategy to use
    based on the model's provider and capabilities. It helps avoid hardcoding
    strategy selection throughout the codebase.
    
    Usage:
        selector = StructuredOutputSelector()
        strategy = selector.select_strategy(model=chat_model, model_type="openai")
        agent = create_agent(..., response_format=strategy)
    """
    
    # Models that support ProviderStrategy (native structured output)
    PROVIDER_STRATEGY_MODELS = {
        # OpenAI models with native structured output support
        "gpt-4o",
        "gpt-4o-2024-05-13",
        "gpt-4-turbo",
        "gpt-4-turbo-preview",
        "gpt-4-0125-preview",
        "gpt-4",
        "gpt-4-0613",
        "gpt-3.5-turbo",  # With structured output mode enabled
        
        # Anthropic Claude models
        "claude-3-opus-20240229",
        "claude-3-opus",
        "claude-3-sonnet-20240229",
        "claude-3-sonnet",
        "claude-3-haiku-20240307",
        "claude-3-haiku",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet",
        
        # Google Gemini models
        "gemini-pro",
        "gemini-pro-latest",
        "gemini-flash",
        "gemini-flash-latest",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    }
    
    # Models that don't support ProviderStrategy but support ToolStrategy
    TOOL_STRATEGY_MODELS = {
        # OpenAI models without native structured output
        "gpt-4o-mini",
        "gpt-3.5-turbo-16k",
    }
    
    # Providers that never support structured output
    NO_STRATEGY_PROVIDERS = {
        "local",  # ChatLlamaCpp doesn't support tool_choice parameter
    }
    
    @classmethod
    def select_strategy(
        cls,
        model: BaseChatModel,
        model_type: str,
        schema: type = CompanyInfo,
        model_name: Optional[str] = None,
    ) -> Optional[ProviderStrategy | ToolStrategy]:
        """
        Select the best structured output strategy for the given model.
        
        Selection Logic:
        1. Local models (ChatLlamaCpp): No strategy (returns None)
           - ChatLlamaCpp doesn't support tool_choice parameter
           - ChatLlamaCpp doesn't have native structured output
        2. Models with native support: ProviderStrategy
           - More efficient and reliable
           - Used for GPT-4o, GPT-4 Turbo, Claude 3, Gemini
        3. Models with tool calling but no native support: ToolStrategy
           - Fallback for models like GPT-4o-mini
        4. Unknown models: Try ProviderStrategy first (LangChain auto-selects)
        
        Args:
            model: The LangChain chat model instance
            model_type: Provider type ("local", "openai", "anthropic", "gemini")
            schema: Pydantic model class defining the output schema
            model_name: Optional specific model name (e.g., "gpt-4o-mini")
        
        Returns:
            ProviderStrategy, ToolStrategy, or None
            - ProviderStrategy: For models with native structured output
            - ToolStrategy: For models with tool calling but no native support
            - None: For models that cannot use structured output (e.g., ChatLlamaCpp)
        
        Examples:
            >>> from src.models.model_factory import get_chat_model
            >>> model = get_chat_model(model_type="openai", model_name="gpt-4o")
            >>> strategy = StructuredOutputSelector.select_strategy(
            ...     model=model, model_type="openai", model_name="gpt-4o"
            ... )
            >>> # Returns ProviderStrategy(CompanyInfo)
            
            >>> local_model = get_chat_model(model_type="local")
            >>> strategy = StructuredOutputSelector.select_strategy(
            ...     model=local_model, model_type="local"
            ... )
            >>> # Returns None (ChatLlamaCpp doesn't support structured output)
        """
        # Local models cannot use structured output strategies
        if model_type == "local":
            return None
        
        # Try to determine model name if not provided
        resolved_model_name = model_name or cls._extract_model_name(model, model_type)
        
        # Check if model supports ProviderStrategy (native structured output)
        if resolved_model_name and resolved_model_name.lower() in cls.PROVIDER_STRATEGY_MODELS:
            return ProviderStrategy(schema)
        
        # Check if model explicitly requires ToolStrategy
        if resolved_model_name and resolved_model_name.lower() in cls.TOOL_STRATEGY_MODELS:
            return ToolStrategy(schema)
        
        # For remote providers, default to ProviderStrategy and let LangChain handle it
        # LangChain's create_agent will auto-select the best strategy if the model
        # supports it, or fall back to ToolStrategy if needed
        if model_type in ["openai", "anthropic", "gemini"]:
            # Try ProviderStrategy first - LangChain will handle compatibility
            # If the model doesn't support it, LangChain may auto-fallback to ToolStrategy
            return ProviderStrategy(schema)
        
        # Unknown provider or model - no structured output
        return None
    
    @classmethod
    def _extract_model_name(cls, model: BaseChatModel, model_type: str) -> Optional[str]:
        """
        Extract the model name from a LangChain model instance.
        
        This is a helper method to inspect the model and determine its
        specific name (e.g., "gpt-4o", "claude-3-opus") for capability detection.
        
        Different LangChain provider classes store the model name in different
        attributes, so we check multiple possibilities.
        """
        # Common attribute names across providers
        common_attrs = ["model_name", "model", "model_id"]
        for attr in common_attrs:
            if hasattr(model, attr):
                value = getattr(model, attr, None)
                if value:
                    return str(value)
        
        # Provider-specific extraction
        if model_type == "openai":
            # ChatOpenAI uses 'model' attribute
            if hasattr(model, "model"):
                return str(model.model)
            # Sometimes stored in client
            if hasattr(model, "client") and hasattr(model.client, "model"):
                try:
                    return str(model.client.model)
                except (AttributeError, TypeError):
                    pass
        
        if model_type == "anthropic":
            # ChatAnthropic uses 'model' attribute
            if hasattr(model, "model"):
                return str(model.model)
        
        if model_type == "gemini":
            # ChatGoogleGenerativeAI uses 'model' or 'model_name'
            if hasattr(model, "model_name"):
                return str(model.model_name)
            if hasattr(model, "model"):
                return str(model.model)
        
        # Last resort: try to inspect the model's string representation
        model_str = str(model)
        # Look for common patterns like "ChatOpenAI(model='gpt-4o')"
        match = re.search(r"model[=:]?\s*['\"]?([\w-]+)['\"]?", model_str, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None
    
    @classmethod
    def get_strategy_info(
        cls,
        model_type: str,
        model_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Get information about which strategy would be selected.
        
        Useful for debugging and educational purposes - shows why a particular
        strategy was chosen without actually creating the strategy object.
        
        Args:
            model_type: Provider type
            model_name: Optional specific model name
        
        Returns:
            Dictionary with strategy information:
            - "strategy": Strategy name ("provider", "tool", or "none")
            - "reason": Explanation of why this strategy was chosen
            - "supported": Whether structured output is supported
        """
        if model_type == "local":
            return {
                "strategy": "none",
                "reason": (
                    "ChatLlamaCpp doesn't support tool_choice parameter "
                    "(required by ToolStrategy) and doesn't have native "
                    "structured output (required by ProviderStrategy)"
                ),
                "supported": False,
            }
        
        resolved_name = model_name.lower() if model_name else None
        
        if resolved_name and resolved_name in cls.PROVIDER_STRATEGY_MODELS:
            return {
                "strategy": "provider",
                "reason": f"Model {model_name} supports native structured output",
                "supported": True,
            }
        
        if resolved_name and resolved_name in cls.TOOL_STRATEGY_MODELS:
            return {
                "strategy": "tool",
                "reason": (
                    f"Model {model_name} doesn't support native structured output, "
                    "but supports tool calling (will use ToolStrategy)"
                ),
                "supported": True,
            }
        
        if model_type in ["openai", "anthropic", "gemini"]:
            return {
                "strategy": "provider",
                "reason": (
                    f"Provider {model_type} generally supports ProviderStrategy. "
                    "LangChain will auto-select the best strategy for the specific model."
                ),
                "supported": True,
            }
        
        return {
            "strategy": "none",
            "reason": f"Unknown provider {model_type} - structured output not available",
            "supported": False,
        }


def select_structured_output_strategy(
    model: BaseChatModel,
    model_type: str,
    schema: type = CompanyInfo,
    model_name: Optional[str] = None,
) -> Optional[ProviderStrategy | ToolStrategy]:
    """
    Convenience function for selecting structured output strategy.
    
    This is a simple wrapper around StructuredOutputSelector.select_strategy()
    that provides a function-based API for easier importing.
    
    Args:
        model: The LangChain chat model instance
        model_type: Provider type ("local", "openai", "anthropic", "gemini")
        schema: Pydantic model class defining the output schema
        model_name: Optional specific model name
    
    Returns:
        ProviderStrategy, ToolStrategy, or None
    
    Example:
        >>> strategy = select_structured_output_strategy(
        ...     model=chat_model,
        ...     model_type="openai",
        ...     model_name="gpt-4o"
        ... )
        >>> agent = create_agent(model=chat_model, response_format=strategy, ...)
    """
    return StructuredOutputSelector.select_strategy(
        model=model,
        model_type=model_type,
        schema=schema,
        model_name=model_name,
    )

