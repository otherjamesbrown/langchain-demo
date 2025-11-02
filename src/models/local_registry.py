"""
Local LLM registry for educational multi-model support.

This module teaches how to manage multiple quantised models on disk while
keeping Streamlit demos simple. Each configuration documents why you might
choose it so learners can experiment with capabilities versus resource
requirements.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models"


@dataclass(frozen=True)
class LocalModelConfig:
    """Describe an on-disk local model available to the demo application."""

    key: str
    display_name: str
    filename: str
    description: str
    recommended_vram_gb: int
    context_window: int = 4096

    def resolve_path(self) -> Path:
        """Return the absolute path for the model file relative to ``models/``."""

        candidate = Path(self.filename)
        if candidate.is_absolute():
            return candidate
        return MODELS_DIR / candidate


def _build_registry() -> Dict[str, LocalModelConfig]:
    """Create the default registry of educational local models."""

    return {
        "llama-2-7b-chat-q4_k_m": LocalModelConfig(
            key="llama-2-7b-chat-q4_k_m",
            display_name="Llama 2 7B Chat (Q4_K_M)",
            filename="llama-2-7b-chat.Q4_K_M.gguf",
            description=(
                "Heritage baseline model used throughout earlier lessons."
                " Great for demonstrating llama.cpp integrations on modest"
                " GPU instances."
            ),
            recommended_vram_gb=8,
            context_window=4096,
        ),
        "meta-llama-3.1-8b-instruct-q4_k_m": LocalModelConfig(
            key="meta-llama-3.1-8b-instruct-q4_k_m",
            display_name="Meta Llama 3.1 8B Instruct (Q4_K_M)",
            filename="meta-llama-3.1-8b-instruct.Q4_K_M.gguf",
            description=(
                "Latest Meta Llama 3.1 instruct-tuned checkpoint. Shows the"
                " improvement in reasoning quality and instruction following"
                " when compared to Llama 2 while keeping the file size"
                " manageable."
            ),
            recommended_vram_gb=12,
            context_window=8192,
        ),
    }


LOCAL_MODEL_REGISTRY: Dict[str, LocalModelConfig] = _build_registry()
DEFAULT_LOCAL_MODEL_KEY = "llama-2-7b-chat-q4_k_m"


def list_local_models() -> List[LocalModelConfig]:
    """Return an ordered list of available local model configurations."""

    return list(LOCAL_MODEL_REGISTRY.values())


def get_local_model_config(key: str) -> LocalModelConfig:
    """Look up a local model configuration by registry key or display name."""

    normalized = key.strip().lower()
    if normalized in LOCAL_MODEL_REGISTRY:
        return LOCAL_MODEL_REGISTRY[normalized]

    for config in LOCAL_MODEL_REGISTRY.values():
        if config.display_name.lower() == normalized:
            return config

    raise KeyError(f"Unknown local model: {key}")


def guess_local_model_key(path: Path) -> str | None:
    """Best-effort mapping from a model path back to the registry key."""

    try:
        resolved = path.resolve()
    except FileNotFoundError:
        resolved = path

    for config in LOCAL_MODEL_REGISTRY.values():
        if resolved.name.lower() == Path(config.filename).name.lower():
            return config.key

    return None


def ensure_models_directory() -> Path:
    """Ensure the ``models/`` directory exists and return its path."""

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return MODELS_DIR


__all__ = [
    "LocalModelConfig",
    "DEFAULT_LOCAL_MODEL_KEY",
    "LOCAL_MODEL_REGISTRY",
    "ensure_models_directory",
    "get_local_model_config",
    "guess_local_model_key",
    "list_local_models",
]


