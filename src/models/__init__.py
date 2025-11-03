"""
Model utilities for LangChain demo project.

This package provides:
- Model factory functions for creating LLM instances (model_factory)
- Local model registry and configuration (local_registry)
- Structured output strategy selection (structured_output)
"""

from src.models.model_factory import (
    get_llm,
    get_chat_model,
    list_available_providers,
    ModelType,
)
from src.models.structured_output import (
    StructuredOutputSelector,
    select_structured_output_strategy,
)

__all__ = [
    "get_llm",
    "get_chat_model",
    "list_available_providers",
    "ModelType",
    "StructuredOutputSelector",
    "select_structured_output_strategy",
]
