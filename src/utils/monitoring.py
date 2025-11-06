"""
Monitoring utilities for tracking agent performance and execution.

This module provides callbacks and monitoring helpers for LangChain agents,
including token usage tracking and LangSmith integration.

Enhanced LangSmith Integration:
- Comprehensive callback handlers for all LangChain events
- Token usage and cost tracking
- Performance metrics (latency, tokens/sec)
- Error capture with full context
- Custom metadata tagging (company, phase, model)
- Context managers for easy tracing setup
"""

import os
import time
from contextlib import contextmanager
from typing import Optional, Any, Dict, List, Union
from datetime import datetime
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult, ChatGenerationChunk, GenerationChunk
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage


class SimpleCallbackHandler(BaseCallbackHandler):
    """
    Simple callback handler for logging agent execution.
    
    Logs agent thoughts, actions, and tool results to help debug
    agent behavior and understand decision-making process.
    """
    
    def __init__(self):
        """Initialize the callback handler."""
        super().__init__()
        self.steps = []
    
    def on_agent_action(self, action: AgentAction, **kwargs) -> None:
        """
        Called when the agent decides to take an action.
        
        Args:
            action: AgentAction object with tool name and input
            **kwargs: Additional context
        """
        step = {
            "type": "action",
            "tool": action.tool,
            "tool_input": action.tool_input,
            "log": action.log
        }
        self.steps.append(step)
        print(f"\n🤖 Agent Action: {action.tool}")
        print(f"   Input: {action.tool_input}")
    
    def on_agent_finish(self, finish: AgentFinish, **kwargs) -> None:
        """
        Called when the agent finishes execution.
        
        Args:
            finish: AgentFinish object with return values
            **kwargs: Additional context
        """
        step = {
            "type": "finish",
            "return_values": finish.return_values
        }
        self.steps.append(step)
        print(f"\n✅ Agent Finished")
        print(f"   Output: {finish.return_values.get('output', '')[:200]}")
    
    def get_steps(self) -> list[dict]:
        """
        Get all recorded steps.
        
        Returns:
            List of step dictionaries
        """
        return self.steps


class EnhancedLangSmithCallback(BaseCallbackHandler):
    """
    Comprehensive LangSmith callback handler for monitoring and debugging.
    
    Tracks all LangChain events with detailed metrics:
    - LLM calls (start, end, error) with token usage and latency
    - Tool calls (start, end, error) with execution time
    - Agent actions and reasoning steps
    - Chain execution flow
    - Custom metadata (company name, phase, model, etc.)
    
    Usage:
        callback = EnhancedLangSmithCallback(
            metadata={"company": "BitMovin", "phase": "llm-processing"}
        )
        llm.invoke(prompt, callbacks=[callback])
    """
    
    def __init__(
        self,
        metadata: Optional[Dict[str, Any]] = None,
        track_costs: bool = True,
        verbose: bool = False
    ):
        """
        Initialize the enhanced LangSmith callback.
        
        Args:
            metadata: Custom metadata to attach to all traces (e.g., company, phase)
            track_costs: Whether to calculate costs for API-based models
            verbose: Whether to print detailed logs to console
        """
        super().__init__()
        self.metadata = metadata or {}
        self.track_costs = track_costs
        self.verbose = verbose
        self.enabled = bool(os.getenv("LANGCHAIN_API_KEY"))
        
        # Tracking
        self.llm_calls = []
        self.tool_calls = []
        self.errors = []
        self.start_times = {}
        
        if self.enabled:
            if self.verbose:
                print("🔗 Enhanced LangSmith monitoring enabled")
                if self.metadata:
                    print(f"   Metadata: {self.metadata}")
        else:
            if self.verbose:
                print("⚠️  LangSmith not configured (no LANGCHAIN_API_KEY)")
    
    # ========== LLM Event Handlers ==========
    
    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any
    ) -> None:
        """
        Called when LLM starts processing.
        
        Args:
            serialized: LLM configuration
            prompts: Input prompts
            **kwargs: Additional context
        """
        run_id = kwargs.get("run_id", "unknown")
        self.start_times[run_id] = time.time()
        
        if self.verbose:
            model_name = serialized.get("name", "unknown")
            print(f"\n🤖 LLM Start: {model_name}")
            print(f"   Prompts: {len(prompts)} prompt(s)")
    
    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        **kwargs: Any
    ) -> None:
        """
        Called when chat model starts processing.
        
        Args:
            serialized: Model configuration
            messages: Input messages
            **kwargs: Additional context
        """
        run_id = kwargs.get("run_id", "unknown")
        self.start_times[run_id] = time.time()
        
        if self.verbose:
            model_name = serialized.get("name", "unknown")
            total_messages = sum(len(msg_list) for msg_list in messages)
            print(f"\n💬 Chat Model Start: {model_name}")
            print(f"   Messages: {total_messages} message(s)")
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """
        Called when LLM finishes processing.
        
        Args:
            response: LLM response with generations and metadata
            **kwargs: Additional context
        """
        run_id = kwargs.get("run_id", "unknown")
        duration = None
        if run_id in self.start_times:
            duration = time.time() - self.start_times[run_id]
            del self.start_times[run_id]
        
        # Extract token usage
        llm_output = response.llm_output or {}
        token_usage = llm_output.get("token_usage", {})
        prompt_tokens = token_usage.get("prompt_tokens", 0)
        completion_tokens = token_usage.get("completion_tokens", 0)
        total_tokens = token_usage.get("total_tokens", 0)
        
        # Calculate cost if enabled
        cost = None
        if self.track_costs and total_tokens > 0:
            model_name = llm_output.get("model_name", "unknown")
            cost = self._calculate_cost(model_name, prompt_tokens, completion_tokens)
        
        # Record call
        call_info = {
            "run_id": run_id,
            "duration": duration,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost": cost,
            "metadata": self.metadata.copy()
        }
        self.llm_calls.append(call_info)
        
        if self.verbose:
            print(f"\n✅ LLM End:")
            print(f"   Duration: {duration:.2f}s" if duration else "   Duration: unknown")
            print(f"   Tokens: {total_tokens} ({prompt_tokens} prompt + {completion_tokens} completion)")
            if cost:
                print(f"   Cost: ${cost:.4f}")
    
    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """
        Called when LLM encounters an error.
        
        Args:
            error: Exception that occurred
            **kwargs: Additional context
        """
        run_id = kwargs.get("run_id", "unknown")
        if run_id in self.start_times:
            del self.start_times[run_id]
        
        error_info = {
            "type": "llm_error",
            "run_id": run_id,
            "error": str(error),
            "error_type": type(error).__name__,
            "metadata": self.metadata.copy()
        }
        self.errors.append(error_info)
        
        if self.verbose:
            print(f"\n❌ LLM Error: {error}")
    
    # ========== Tool Event Handlers ==========
    
    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any
    ) -> None:
        """
        Called when a tool starts execution.
        
        Args:
            serialized: Tool configuration
            input_str: Tool input
            **kwargs: Additional context
        """
        run_id = kwargs.get("run_id", "unknown")
        self.start_times[run_id] = time.time()
        
        tool_name = serialized.get("name", "unknown")
        if self.verbose:
            print(f"\n🔧 Tool Start: {tool_name}")
            print(f"   Input: {input_str[:100]}...")
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """
        Called when a tool finishes execution.
        
        Args:
            output: Tool output
            **kwargs: Additional context
        """
        run_id = kwargs.get("run_id", "unknown")
        duration = None
        if run_id in self.start_times:
            duration = time.time() - self.start_times[run_id]
            del self.start_times[run_id]
        
        tool_info = {
            "run_id": run_id,
            "duration": duration,
            "output_length": len(output),
            "metadata": self.metadata.copy()
        }
        self.tool_calls.append(tool_info)
        
        if self.verbose:
            print(f"\n✅ Tool End:")
            print(f"   Duration: {duration:.2f}s" if duration else "   Duration: unknown")
            print(f"   Output: {len(output)} characters")
    
    def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        """
        Called when a tool encounters an error.
        
        Args:
            error: Exception that occurred
            **kwargs: Additional context
        """
        run_id = kwargs.get("run_id", "unknown")
        if run_id in self.start_times:
            del self.start_times[run_id]
        
        error_info = {
            "type": "tool_error",
            "run_id": run_id,
            "error": str(error),
            "error_type": type(error).__name__,
            "metadata": self.metadata.copy()
        }
        self.errors.append(error_info)
        
        if self.verbose:
            print(f"\n❌ Tool Error: {error}")
    
    # ========== Agent Event Handlers ==========
    
    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> None:
        """
        Called when agent decides on an action.
        
        Args:
            action: Agent action with tool and input
            **kwargs: Additional context
        """
        if self.verbose:
            print(f"\n🎯 Agent Action: {action.tool}")
            print(f"   Input: {action.tool_input}")
    
    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """
        Called when agent finishes execution.
        
        Args:
            finish: Agent finish with return values
            **kwargs: Additional context
        """
        if self.verbose:
            print(f"\n🏁 Agent Finish:")
            output = finish.return_values.get("output", "")
            print(f"   Output: {output[:200]}...")
    
    # ========== Chain Event Handlers ==========
    
    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        **kwargs: Any
    ) -> None:
        """
        Called when a chain starts execution.
        
        Args:
            serialized: Chain configuration
            inputs: Chain inputs
            **kwargs: Additional context
        """
        run_id = kwargs.get("run_id", "unknown")
        self.start_times[run_id] = time.time()
        
        if self.verbose:
            chain_name = serialized.get("name", "unknown")
            print(f"\n🔗 Chain Start: {chain_name}")
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """
        Called when a chain finishes execution.
        
        Args:
            outputs: Chain outputs
            **kwargs: Additional context
        """
        run_id = kwargs.get("run_id", "unknown")
        if run_id in self.start_times:
            duration = time.time() - self.start_times[run_id]
            del self.start_times[run_id]
            
            if self.verbose:
                print(f"\n✅ Chain End:")
                print(f"   Duration: {duration:.2f}s")
    
    def on_chain_error(self, error: Exception, **kwargs: Any) -> None:
        """
        Called when a chain encounters an error.
        
        Args:
            error: Exception that occurred
            **kwargs: Additional context
        """
        run_id = kwargs.get("run_id", "unknown")
        if run_id in self.start_times:
            del self.start_times[run_id]
        
        error_info = {
            "type": "chain_error",
            "run_id": run_id,
            "error": str(error),
            "error_type": type(error).__name__,
            "metadata": self.metadata.copy()
        }
        self.errors.append(error_info)
        
        if self.verbose:
            print(f"\n❌ Chain Error: {error}")
    
    # ========== Utility Methods ==========
    
    def _calculate_cost(
        self,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """
        Calculate cost for API-based models.
        
        Args:
            model_name: Name of the model
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
        
        Returns:
            Estimated cost in USD
        """
        # Cost per 1M tokens (as of 2025)
        costs = {
            # OpenAI
            "gpt-4": {"prompt": 30.0, "completion": 60.0},
            "gpt-4-turbo": {"prompt": 10.0, "completion": 30.0},
            "gpt-4-turbo-preview": {"prompt": 10.0, "completion": 30.0},
            "gpt-3.5-turbo": {"prompt": 0.5, "completion": 1.5},
            # Anthropic
            "claude-3-opus": {"prompt": 15.0, "completion": 75.0},
            "claude-3-sonnet": {"prompt": 3.0, "completion": 15.0},
            "claude-3-haiku": {"prompt": 0.25, "completion": 1.25},
            # Google Gemini
            "gemini-pro": {"prompt": 0.5, "completion": 1.5},
            "gemini-1.5-pro": {"prompt": 3.5, "completion": 10.5},
            "gemini-1.5-flash": {"prompt": 0.075, "completion": 0.3},
        }
        
        # Find matching model (case-insensitive, partial match)
        model_lower = model_name.lower()
        for key, pricing in costs.items():
            if key in model_lower:
                prompt_cost = (prompt_tokens / 1_000_000) * pricing["prompt"]
                completion_cost = (completion_tokens / 1_000_000) * pricing["completion"]
                return prompt_cost + completion_cost
        
        # Unknown model
        return 0.0
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for this callback session.
        
        Returns:
            Dictionary with summary metrics
        """
        total_tokens = sum(call["total_tokens"] for call in self.llm_calls)
        total_cost = sum(call["cost"] or 0.0 for call in self.llm_calls)
        total_duration = sum(call["duration"] or 0.0 for call in self.llm_calls)
        
        return {
            "llm_calls": len(self.llm_calls),
            "tool_calls": len(self.tool_calls),
            "errors": len(self.errors),
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "total_duration": total_duration,
            "metadata": self.metadata.copy()
        }
    
    def print_summary(self) -> None:
        """Print summary statistics to console."""
        summary = self.get_summary()
        print("\n" + "="*60)
        print("LangSmith Callback Summary")
        print("="*60)
        print(f"LLM Calls: {summary['llm_calls']}")
        print(f"Tool Calls: {summary['tool_calls']}")
        print(f"Errors: {summary['errors']}")
        print(f"Total Tokens: {summary['total_tokens']}")
        print(f"Total Cost: ${summary['total_cost']:.4f}")
        print(f"Total Duration: {summary['total_duration']:.2f}s")
        if summary['metadata']:
            print(f"Metadata: {summary['metadata']}")
        print("="*60)


# Legacy alias for backward compatibility
class LangSmithCallback(EnhancedLangSmithCallback):
    """
    Legacy alias for EnhancedLangSmithCallback.
    
    Maintained for backward compatibility. New code should use
    EnhancedLangSmithCallback directly.
    """
    pass


def configure_langsmith_tracing(
    project_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    verbose: bool = True
) -> bool:
    """
    Configure LangSmith monitoring with enhanced options.
    
    Sets up environment variables for LangSmith tracing with custom
    project name, tags, and metadata.
    
    Args:
        project_name: Custom project name (default: "research-agent")
        tags: List of tags to apply to all traces
        metadata: Dictionary of metadata to apply to all traces
        verbose: Whether to print configuration status
    
    Returns:
        bool: True if LangSmith is configured, False otherwise
    
    Example:
        configure_langsmith_tracing(
            project_name="research-agent-phase2",
            tags=["phase:llm-processing"],
            metadata={"version": "1.0"}
        )
    """
    api_key = os.getenv("LANGCHAIN_API_KEY")
    
    if not api_key:
        if verbose:
            print("⚠️  LangSmith not configured (no LANGCHAIN_API_KEY)")
        return False
    
        # Enable tracing
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        
        # Set project name
    if project_name:
        os.environ["LANGCHAIN_PROJECT"] = project_name
    elif not os.getenv("LANGCHAIN_PROJECT"):
            os.environ["LANGCHAIN_PROJECT"] = "research-agent"
        
    # Store tags and metadata for use in context managers
    if tags:
        os.environ["LANGSMITH_TAGS"] = ",".join(tags)
    
    if metadata:
        # Store as JSON string for retrieval
        import json
        os.environ["LANGSMITH_METADATA"] = json.dumps(metadata)
    
    if verbose:
        print("✅ LangSmith configured for monitoring")
        print(f"   Project: {os.getenv('LANGCHAIN_PROJECT')}")
        if tags:
            print(f"   Tags: {tags}")
        if metadata:
            print(f"   Metadata: {metadata}")
    
        return True


# Legacy function name for backward compatibility
def configure_langsmith() -> bool:
    """
    Legacy function for configuring LangSmith.
    
    For new code, use configure_langsmith_tracing() for more options.
    """
    return configure_langsmith_tracing(verbose=True)


@contextmanager
def langsmith_trace(
    name: str,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    project_name: Optional[str] = None
):
    """
    Context manager for tracing a block of code with LangSmith.
    
    Automatically captures execution time and any errors that occur.
    Requires LANGCHAIN_API_KEY to be set.
    
    Args:
        name: Name for this trace
        tags: Tags to apply to this trace
        metadata: Metadata to apply to this trace
        project_name: Override project name for this trace
    
    Yields:
        Dict with trace information
    
    Example:
        with langsmith_trace(
            name="phase2_bitmovin",
            tags=["phase:llm-processing", "company:bitmovin"],
            metadata={"model": "gpt-4"}
        ) as trace:
            # Your code here
            result = process_company(...)
    """
    start_time = time.time()
    trace_info = {
        "name": name,
        "tags": tags or [],
        "metadata": metadata or {},
        "start_time": start_time,
        "enabled": bool(os.getenv("LANGCHAIN_API_KEY"))
    }
    
    # Configure LangSmith if not already configured
    if trace_info["enabled"]:
        configure_langsmith_tracing(
            project_name=project_name,
            tags=tags,
            metadata=metadata,
            verbose=False
        )
    
    try:
        yield trace_info
        trace_info["success"] = True
        trace_info["error"] = None
    except Exception as e:
        trace_info["success"] = False
        trace_info["error"] = str(e)
        trace_info["error_type"] = type(e).__name__
        raise
    finally:
        trace_info["duration"] = time.time() - start_time
        trace_info["end_time"] = time.time()


@contextmanager
def langsmith_phase_trace(
    phase: str,
    company_name: str,
    model_name: Optional[str] = None,
    project_name: Optional[str] = None
):
    """
    Context manager for tracing research workflow phases.
    
    Specialized context manager for Phase 1 (search) and Phase 2 (LLM processing)
    that automatically sets appropriate tags and metadata.
    
    Args:
        phase: Phase name ("phase1", "phase2", or "search-collection", "llm-processing")
        company_name: Name of company being processed
        model_name: Model name (for Phase 2 only)
        project_name: Custom project name (default: "research-agent-{phase}")
    
    Yields:
        Dict with trace information
    
    Example:
        with langsmith_phase_trace("phase2", "BitMovin", "gpt-4"):
            result = process_with_llm(...)
    """
    # Normalize phase names
    phase_map = {
        "phase1": "search-collection",
        "phase2": "llm-processing",
        "search-collection": "search-collection",
        "llm-processing": "llm-processing"
    }
    normalized_phase = phase_map.get(phase.lower(), phase)
    
    # Build tags
    tags = [
        f"phase:{normalized_phase}",
        f"company:{company_name.lower().replace(' ', '-')}"
    ]
    if model_name:
        tags.append(f"model:{model_name}")
    
    # Build metadata
    metadata = {
        "phase": normalized_phase,
        "company": company_name,
        "timestamp": datetime.now().isoformat()
    }
    if model_name:
        metadata["model"] = model_name
    
    # Set project name
    if not project_name:
        project_name = f"research-agent-{normalized_phase}"
    
    # Use base trace context manager
    with langsmith_trace(
        name=f"{normalized_phase}_{company_name.lower().replace(' ', '_')}",
        tags=tags,
        metadata=metadata,
        project_name=project_name
    ) as trace:
        yield trace


class PerformanceMonitor:
    """
    Monitor agent performance metrics.
    
    Tracks execution time, token usage, and success rates
    for agent runs.
    """
    
    def __init__(self):
        """Initialize performance monitor."""
        self.executions = []
    
    def record_execution(
        self,
        company_name: str,
        success: bool,
        execution_time: float,
        num_tool_calls: int,
        error: Optional[str] = None
    ):
        """
        Record an agent execution.
        
        Args:
            company_name: Company researched
            success: Whether execution succeeded
            execution_time: Execution time in seconds
            num_tool_calls: Number of tool calls made
            error: Error message if failed
        """
        record = {
            "company_name": company_name,
            "success": success,
            "execution_time": execution_time,
            "num_tool_calls": num_tool_calls,
            "error": error
        }
        self.executions.append(record)
    
    def get_stats(self) -> dict:
        """
        Get performance statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        if not self.executions:
            return {}
        
        total = len(self.executions)
        successful = sum(1 for e in self.executions if e["success"])
        
        avg_time = sum(e["execution_time"] for e in self.executions) / total
        avg_tool_calls = sum(e["num_tool_calls"] for e in self.executions) / total
        
        return {
            "total_executions": total,
            "success_rate": f"{successful/total*100:.1f}%",
            "avg_execution_time": f"{avg_time:.2f}s",
            "avg_tool_calls": f"{avg_tool_calls:.1f}"
        }
    
    def print_stats(self):
        """Print performance statistics to console."""
        stats = self.get_stats()
        if stats:
            print("\n" + "="*60)
            print("Performance Statistics")
            print("="*60)
            for key, value in stats.items():
                print(f"{key}: {value}")
            print("="*60)

