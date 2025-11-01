"""
LLM Metrics Tracking Utility

This module provides utilities for tracking LLM usage metrics including:
- Token usage (prompt, completion, total)
- Generation time
- Model information
- Cost estimation (for remote APIs)
"""

import time
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class LLMMetrics:
    """Container for LLM usage metrics."""
    
    # Token counts
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    # Timing
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    generation_time: float = 0.0
    
    # Model info
    model_name: str = ""
    model_type: str = "local"  # local, openai, anthropic, gemini
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate total tokens and generation time."""
        if self.prompt_tokens and self.completion_tokens:
            self.total_tokens = self.prompt_tokens + self.completion_tokens
        
        if self.start_time and self.end_time:
            self.generation_time = self.end_time - self.start_time
    
    def tokens_per_second(self) -> float:
        """Calculate tokens generated per second."""
        if self.generation_time > 0 and self.completion_tokens > 0:
            return self.completion_tokens / self.generation_time
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "generation_time": round(self.generation_time, 2),
            "tokens_per_second": round(self.tokens_per_second(), 2),
            "model_name": self.model_name,
            "model_type": self.model_type,
            "timestamp": datetime.now().isoformat(),
            **self.metadata
        }
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"Tokens: {self.total_tokens} (prompt: {self.prompt_tokens}, "
            f"completion: {self.completion_tokens}) | "
            f"Time: {self.generation_time:.2f}s | "
            f"Speed: {self.tokens_per_second():.2f} tok/s"
        )


class MetricsTracker:
    """Track and aggregate LLM metrics across multiple calls."""
    
    def __init__(self):
        """Initialize metrics tracker."""
        self.metrics: list[LLMMetrics] = []
    
    def record(self, metrics: LLMMetrics) -> None:
        """Record a set of metrics."""
        self.metrics.append(metrics)
    
    def extract_from_llama_result(self, result: Dict[str, Any], 
                                  model_path: str = "",
                                  generation_time: float = 0.0) -> LLMMetrics:
        """
        Extract metrics from llama-cpp-python result.
        
        Args:
            result: Result dictionary from llama_cpp.Llama.__call__()
            model_path: Path to the model file
            generation_time: Time taken for generation in seconds
            
        Returns:
            LLMMetrics object with extracted data
        """
        usage = result.get("usage", {})
        
        return LLMMetrics(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            generation_time=generation_time,
            model_name=model_path or result.get("model", "unknown"),
            model_type="local",
            metadata={
                "model_id": result.get("id", ""),
                "finish_reason": result.get("choices", [{}])[0].get("finish_reason", "")
            }
        )
    
    def extract_from_langchain_response(self, response: Any,
                                        model_name: str = "",
                                        model_type: str = "local",
                                        generation_time: float = 0.0) -> Optional[LLMMetrics]:
        """
        Extract metrics from LangChain LLM response.
        
        Args:
            response: LangChain LLM response object
            model_name: Name of the model used
            model_type: Type of model (local, openai, etc.)
            generation_time: Time taken for generation
            
        Returns:
            LLMMetrics object if available, None otherwise
        """
        # Check if response has llm_output with usage info
        if hasattr(response, "llm_output") and response.llm_output:
            usage = response.llm_output.get("token_usage", {})
            return LLMMetrics(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                generation_time=generation_time,
                model_name=model_name,
                model_type=model_type
            )
        
        return None
    
    def summary(self) -> Dict[str, Any]:
        """Get summary statistics across all recorded metrics."""
        if not self.metrics:
            return {}
        
        total_prompt = sum(m.prompt_tokens for m in self.metrics)
        total_completion = sum(m.completion_tokens for m in self.metrics)
        total_tokens = sum(m.total_tokens for m in self.metrics)
        total_time = sum(m.generation_time for m in self.metrics)
        avg_speed = total_completion / total_time if total_time > 0 else 0
        
        return {
            "total_calls": len(self.metrics),
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_tokens,
            "total_time": round(total_time, 2),
            "average_tokens_per_second": round(avg_speed, 2),
            "average_tokens_per_call": round(total_tokens / len(self.metrics), 2) if self.metrics else 0
        }
    
    def reset(self) -> None:
        """Reset all recorded metrics."""
        self.metrics = []


def track_llm_call(func):
    """
    Decorator to automatically track LLM call metrics.
    
    Usage:
        @track_llm_call
        def my_llm_call(prompt):
            return llm.invoke(prompt)
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        # Call the function
        result = func(*args, **kwargs)
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        # Try to extract metrics from result
        tracker = MetricsTracker()
        if isinstance(result, dict) and "usage" in result:
            metrics = tracker.extract_from_llama_result(result, generation_time=generation_time)
            tracker.record(metrics)
            print(f"Metrics: {metrics}")
        
        return result
    
    return wrapper

