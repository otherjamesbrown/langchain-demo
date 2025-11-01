"""
Tests for model factory and LLM integrations.

Tests cover:
- Model factory initialization
- Local LLM loading
- Remote API integrations (OpenAI, Anthropic, Gemini)
- Model configuration validation
"""

import os
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.models.model_factory import (
    get_llm,
    ModelType,
    list_available_providers,
    validate_model_config,
)


@pytest.mark.unit
class TestModelFactory:
    """Tests for the model factory."""

    def test_list_available_providers(self):
        """Test listing all available providers."""
        providers = list_available_providers()

        assert "local" in providers
        assert "openai" in providers
        assert "anthropic" in providers
        assert "gemini" in providers
        assert len(providers) == 4

    def test_validate_model_config_local_missing_path(self):
        """Test validation fails when local model path is missing."""
        with pytest.raises(ValueError, match="MODEL_PATH.*required"):
            validate_model_config(model_type="local", model_path=None)

    def test_validate_model_config_local_file_not_exists(self):
        """Test validation fails when local model file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            validate_model_config(
                model_type="local", model_path="/nonexistent/model.gguf"
            )

    def test_validate_model_config_openai_missing_key(self, monkeypatch):
        """Test validation fails when OpenAI API key is missing."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            validate_model_config(model_type="openai")

    def test_validate_model_config_anthropic_missing_key(self, monkeypatch):
        """Test validation fails when Anthropic API key is missing."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            validate_model_config(model_type="anthropic")

    def test_validate_model_config_gemini_missing_key(self, monkeypatch):
        """Test validation fails when Google API key is missing."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            validate_model_config(model_type="gemini")


@pytest.mark.unit
@pytest.mark.requires_model
class TestLocalLLM:
    """Tests for local LLM loading."""

    @patch("src.models.model_factory.LlamaCpp")
    def test_get_local_llm(self, mock_llama, tmp_path):
        """Test loading a local LLM model."""
        # Create a fake model file
        model_path = tmp_path / "test-model.gguf"
        model_path.write_text("fake model data")

        # Mock LlamaCpp
        mock_instance = Mock()
        mock_llama.return_value = mock_instance

        # Get LLM
        llm = get_llm(model_type="local", model_path=str(model_path))

        # Verify LlamaCpp was called
        mock_llama.assert_called_once()
        call_kwargs = mock_llama.call_args[1]

        assert call_kwargs["model_path"] == str(model_path)
        assert call_kwargs["n_ctx"] == 2048
        assert call_kwargs["n_gpu_layers"] > 0  # GPU layers enabled
        assert llm == mock_instance

    @patch("src.models.model_factory.LlamaCpp")
    def test_get_local_llm_custom_params(self, mock_llama, tmp_path):
        """Test loading local LLM with custom parameters."""
        model_path = tmp_path / "test-model.gguf"
        model_path.write_text("fake model data")

        mock_instance = Mock()
        mock_llama.return_value = mock_instance

        # Get LLM with custom params
        llm = get_llm(
            model_type="local",
            model_path=str(model_path),
            temperature=0.9,
            max_tokens=1024,
        )

        call_kwargs = mock_llama.call_args[1]
        assert call_kwargs["temperature"] == 0.9
        assert call_kwargs["max_tokens"] == 1024


@pytest.mark.unit
@pytest.mark.requires_api
class TestRemoteLLMs:
    """Tests for remote LLM APIs."""

    @patch("src.models.model_factory.ChatOpenAI")
    def test_get_openai_llm(self, mock_openai, mock_env_vars):
        """Test loading OpenAI LLM."""
        mock_instance = Mock()
        mock_openai.return_value = mock_instance

        llm = get_llm(model_type="openai", model="gpt-4")

        mock_openai.assert_called_once()
        call_kwargs = mock_openai.call_args[1]

        assert call_kwargs["model"] == "gpt-4"
        assert call_kwargs["temperature"] == 0.7
        assert llm == mock_instance

    @patch("src.models.model_factory.ChatAnthropic")
    def test_get_anthropic_llm(self, mock_anthropic, mock_env_vars):
        """Test loading Anthropic LLM."""
        mock_instance = Mock()
        mock_anthropic.return_value = mock_instance

        llm = get_llm(model_type="anthropic", model="claude-3-opus-20240229")

        mock_anthropic.assert_called_once()
        call_kwargs = mock_anthropic.call_args[1]

        assert call_kwargs["model"] == "claude-3-opus-20240229"
        assert call_kwargs["temperature"] == 0.7
        assert llm == mock_instance

    @patch("src.models.model_factory.ChatGoogleGenerativeAI")
    def test_get_gemini_llm(self, mock_gemini, mock_env_vars):
        """Test loading Gemini LLM."""
        mock_instance = Mock()
        mock_gemini.return_value = mock_instance

        llm = get_llm(model_type="gemini", model="gemini-pro")

        mock_gemini.assert_called_once()
        call_kwargs = mock_gemini.call_args[1]

        assert call_kwargs["model"] == "gemini-pro"
        assert call_kwargs["temperature"] == 0.7
        assert llm == mock_instance

    @patch("src.models.model_factory.ChatOpenAI")
    def test_get_openai_llm_custom_params(self, mock_openai, mock_env_vars):
        """Test OpenAI LLM with custom parameters."""
        mock_instance = Mock()
        mock_openai.return_value = mock_instance

        llm = get_llm(
            model_type="openai",
            model="gpt-3.5-turbo",
            temperature=0.2,
            max_tokens=500,
        )

        call_kwargs = mock_openai.call_args[1]
        assert call_kwargs["model"] == "gpt-3.5-turbo"
        assert call_kwargs["temperature"] == 0.2
        assert call_kwargs["max_tokens"] == 500


@pytest.mark.unit
class TestModelTypeEnum:
    """Tests for ModelType enum."""

    def test_model_type_values(self):
        """Test that all expected model types exist."""
        assert hasattr(ModelType, "LOCAL")
        assert hasattr(ModelType, "OPENAI")
        assert hasattr(ModelType, "ANTHROPIC")
        assert hasattr(ModelType, "GEMINI")

    def test_model_type_string_values(self):
        """Test model type string values."""
        assert ModelType.LOCAL == "local"
        assert ModelType.OPENAI == "openai"
        assert ModelType.ANTHROPIC == "anthropic"
        assert ModelType.GEMINI == "gemini"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.requires_api
class TestLLMIntegration:
    """Integration tests for LLM models (requires actual API keys)."""

    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"), reason="OpenAI API key not available"
    )
    def test_openai_llm_invoke(self):
        """Test actual OpenAI LLM invocation."""
        llm = get_llm(model_type="openai", model="gpt-3.5-turbo")
        response = llm.invoke("Say 'test successful' and nothing else.")

        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"), reason="Anthropic API key not available"
    )
    def test_anthropic_llm_invoke(self):
        """Test actual Anthropic LLM invocation."""
        llm = get_llm(model_type="anthropic", model="claude-3-haiku-20240307")
        response = llm.invoke("Say 'test successful' and nothing else.")

        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0

    @pytest.mark.skipif(
        not os.getenv("GOOGLE_API_KEY"), reason="Google API key not available"
    )
    def test_gemini_llm_invoke(self):
        """Test actual Gemini LLM invocation."""
        llm = get_llm(model_type="gemini", model="gemini-pro")
        response = llm.invoke("Say 'test successful' and nothing else.")

        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
