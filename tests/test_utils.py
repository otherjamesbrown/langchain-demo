"""
Tests for utility modules (logging, metrics, monitoring).

Tests cover:
- LLM call logging
- Metrics collection
- Performance monitoring
- LangSmith integration
"""

from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.utils.llm_logger import log_llm_call, create_llm_call_log
from src.utils.metrics import LLMMetrics, calculate_cost
from src.utils.monitoring import PerformanceMonitor, SimpleCallbackHandler


@pytest.mark.unit
class TestLLMLogger:
    """Tests for LLM call logging."""

    def test_create_llm_call_log(self):
        """Test creating an LLM call log entry."""
        metrics = LLMMetrics(
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            start_time=1234567890.0,
            end_time=1234567895.5,
            generation_time=5.5,
            model_name="gpt-4",
            model_type="openai"
        )

        log_entry = create_llm_call_log(
            metrics=metrics,
            prompt="Test prompt",
            response="Test response",
            model_name="gpt-4",
            call_type="chat"
        )

        assert log_entry.model_name == "gpt-4"
        assert log_entry.model_type == "openai"
        assert log_entry.prompt_tokens == 100
        assert log_entry.completion_tokens == 200
        assert log_entry.total_tokens == 300
        assert log_entry.generation_time_seconds == 5.5
        assert log_entry.success is True

    def test_log_llm_call_success(self, test_db_session):
        """Test logging a successful LLM call."""
        metrics = LLMMetrics(
            prompt_tokens=50,
            completion_tokens=100,
            total_tokens=150,
            start_time=1234567890.0,
            end_time=1234567892.0,
            generation_time=2.0,
            model_name="gpt-3.5-turbo",
            model_type="openai"
        )

        log_entry = log_llm_call(
            metrics=metrics,
            prompt="Hello",
            response="Hi there!",
            model_name="gpt-3.5-turbo",
            call_type="chat",
            session=test_db_session
        )

        assert log_entry.id is not None
        assert log_entry.success is True
        assert log_entry.error_message is None

        # Verify it's in the database
        test_db_session.commit()
        from src.database.schema import LLMCallLog
        saved = test_db_session.query(LLMCallLog).filter_by(id=log_entry.id).first()
        assert saved is not None

    def test_log_llm_call_with_error(self, test_db_session):
        """Test logging a failed LLM call."""
        metrics = LLMMetrics(
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            start_time=1234567890.0,
            end_time=1234567891.0,
            generation_time=1.0,
            model_name="gpt-4",
            model_type="openai"
        )

        log_entry = log_llm_call(
            metrics=metrics,
            prompt="Test prompt",
            response=None,
            model_name="gpt-4",
            call_type="chat",
            session=test_db_session,
            success=False,
            error_message="API rate limit exceeded"
        )

        assert log_entry.success is False
        assert log_entry.error_message == "API rate limit exceeded"
        assert log_entry.response is None

    def test_log_llm_call_with_metadata(self, test_db_session):
        """Test logging with extra metadata."""
        metrics = LLMMetrics(
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            start_time=1234567890.0,
            end_time=1234567895.0,
            generation_time=5.0,
            model_name="claude-3-opus",
            model_type="anthropic"
        )

        extra_metadata = {
            "company": "BitMovin",
            "research_phase": "phase_2",
            "prompt_version": "1.0"
        }

        log_entry = log_llm_call(
            metrics=metrics,
            prompt="Research BitMovin",
            response="BitMovin is a video infrastructure company",
            model_name="claude-3-opus",
            call_type="research",
            session=test_db_session,
            extra_metadata=extra_metadata
        )

        assert log_entry.extra_metadata is not None
        assert log_entry.extra_metadata["company"] == "BitMovin"
        assert log_entry.extra_metadata["research_phase"] == "phase_2"


@pytest.mark.unit
class TestMetrics:
    """Tests for metrics utilities."""

    def test_llm_metrics_creation(self):
        """Test creating LLMMetrics object."""
        metrics = LLMMetrics(
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            start_time=1000.0,
            end_time=1005.5,
            generation_time=5.5,
            model_name="gpt-4",
            model_type="openai"
        )

        assert metrics.prompt_tokens == 100
        assert metrics.completion_tokens == 200
        assert metrics.total_tokens == 300
        assert metrics.generation_time == 5.5

    def test_llm_metrics_tokens_per_second(self):
        """Test calculating tokens per second."""
        metrics = LLMMetrics(
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            start_time=1000.0,
            end_time=1010.0,
            generation_time=10.0,
            model_name="gpt-4",
            model_type="openai"
        )

        assert metrics.tokens_per_second() == 30.0  # 300 tokens / 10 seconds

    def test_llm_metrics_tokens_per_second_zero_time(self):
        """Test tokens per second with zero generation time."""
        metrics = LLMMetrics(
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            start_time=1000.0,
            end_time=1000.0,
            generation_time=0.0,
            model_name="gpt-4",
            model_type="openai"
        )

        assert metrics.tokens_per_second() == 0.0

    def test_calculate_cost_openai(self):
        """Test calculating cost for OpenAI models."""
        cost = calculate_cost(
            model_name="gpt-4",
            prompt_tokens=1000,
            completion_tokens=500
        )

        # GPT-4 pricing: $0.03/1K prompt, $0.06/1K completion
        expected = (1000 * 0.03 / 1000) + (500 * 0.06 / 1000)
        assert abs(cost - expected) < 0.001

    def test_calculate_cost_gpt35(self):
        """Test calculating cost for GPT-3.5."""
        cost = calculate_cost(
            model_name="gpt-3.5-turbo",
            prompt_tokens=1000,
            completion_tokens=500
        )

        # GPT-3.5 pricing: $0.0015/1K prompt, $0.002/1K completion
        expected = (1000 * 0.0015 / 1000) + (500 * 0.002 / 1000)
        assert abs(cost - expected) < 0.001

    def test_calculate_cost_anthropic(self):
        """Test calculating cost for Anthropic models."""
        cost = calculate_cost(
            model_name="claude-3-opus-20240229",
            prompt_tokens=1000,
            completion_tokens=500
        )

        # Claude Opus pricing: $0.015/1K prompt, $0.075/1K completion
        expected = (1000 * 0.015 / 1000) + (500 * 0.075 / 1000)
        assert abs(cost - expected) < 0.001

    def test_calculate_cost_local_model(self):
        """Test calculating cost for local models (should be 0)."""
        cost = calculate_cost(
            model_name="llama-2-7b",
            prompt_tokens=1000,
            completion_tokens=500
        )

        assert cost == 0.0

    def test_calculate_cost_unknown_model(self):
        """Test calculating cost for unknown model (should be 0)."""
        cost = calculate_cost(
            model_name="unknown-model",
            prompt_tokens=1000,
            completion_tokens=500
        )

        assert cost == 0.0


@pytest.mark.unit
class TestMonitoring:
    """Tests for monitoring utilities."""

    def test_performance_monitor_start(self):
        """Test starting performance monitor."""
        monitor = PerformanceMonitor()
        monitor.start("test_operation")

        assert "test_operation" in monitor.timers
        assert monitor.timers["test_operation"]["start"] is not None
        assert monitor.timers["test_operation"]["end"] is None

    def test_performance_monitor_stop(self):
        """Test stopping performance monitor."""
        monitor = PerformanceMonitor()
        monitor.start("test_operation")

        import time
        time.sleep(0.1)  # Wait a bit

        duration = monitor.stop("test_operation")

        assert duration > 0
        assert duration >= 0.1
        assert monitor.timers["test_operation"]["end"] is not None

    def test_performance_monitor_get_duration(self):
        """Test getting duration for completed operation."""
        monitor = PerformanceMonitor()
        monitor.start("test_operation")

        import time
        time.sleep(0.05)

        monitor.stop("test_operation")
        duration = monitor.get_duration("test_operation")

        assert duration >= 0.05

    def test_performance_monitor_get_duration_not_found(self):
        """Test getting duration for non-existent operation."""
        monitor = PerformanceMonitor()
        duration = monitor.get_duration("nonexistent")

        assert duration is None

    def test_performance_monitor_get_all_metrics(self):
        """Test getting all metrics."""
        monitor = PerformanceMonitor()

        monitor.start("op1")
        monitor.stop("op1")

        monitor.start("op2")
        monitor.stop("op2")

        metrics = monitor.get_all_metrics()

        assert len(metrics) == 2
        assert "op1" in metrics
        assert "op2" in metrics
        assert metrics["op1"]["duration"] > 0

    def test_simple_callback_handler(self):
        """Test SimpleCallbackHandler initialization."""
        handler = SimpleCallbackHandler()

        assert handler is not None
        # Callback should have basic attributes
        assert hasattr(handler, "on_llm_start")
        assert hasattr(handler, "on_llm_end")
        assert hasattr(handler, "on_llm_error")

    @patch("src.utils.monitoring.LangSmithCallback")
    def test_langsmith_callback_initialization(self, mock_langsmith):
        """Test LangSmith callback initialization."""
        from src.utils.monitoring import get_langsmith_callback

        mock_instance = Mock()
        mock_langsmith.return_value = mock_instance

        callback = get_langsmith_callback(project_name="test_project")

        # Should create LangSmith callback if API key is available
        assert callback is not None


@pytest.mark.integration
class TestMetricsIntegration:
    """Integration tests for metrics collection."""

    def test_end_to_end_metrics_logging(self, test_db_session):
        """Test complete flow of metrics collection and logging."""
        import time

        # Simulate LLM call
        start_time = time.time()
        time.sleep(0.1)  # Simulate processing
        end_time = time.time()

        metrics = LLMMetrics(
            prompt_tokens=150,
            completion_tokens=250,
            total_tokens=400,
            start_time=start_time,
            end_time=end_time,
            generation_time=end_time - start_time,
            model_name="gpt-4",
            model_type="openai"
        )

        # Log to database
        log_entry = log_llm_call(
            metrics=metrics,
            prompt="Test integration",
            response="Integration successful",
            model_name="gpt-4",
            call_type="test",
            session=test_db_session
        )

        # Verify
        assert log_entry.id is not None
        assert log_entry.tokens_per_second > 0
        assert log_entry.generation_time_seconds >= 0.1

        # Calculate cost
        cost = calculate_cost(
            model_name="gpt-4",
            prompt_tokens=150,
            completion_tokens=250
        )
        assert cost > 0
