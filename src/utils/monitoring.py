"""
Monitoring utilities for tracking agent performance and execution.

This module provides callbacks and monitoring helpers for LangChain agents,
including token usage tracking and LangSmith integration.
"""

import os
from typing import Optional, Any, Dict, List
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.agents import AgentAction, AgentFinish


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


class LangSmithCallback(BaseCallbackHandler):
    """
    LangSmith callback handler for monitoring and debugging.
    
    Automatically enabled if LANGCHAIN_API_KEY is set in environment.
    Provides tracing and monitoring capabilities through LangSmith.
    """
    
    def __init__(self):
        """Initialize LangSmith callback."""
        super().__init__()
        self.enabled = bool(os.getenv("LANGCHAIN_API_KEY"))
        if self.enabled:
            print("🔗 LangSmith monitoring enabled")
    
    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """Called when LLM finishes a request."""
        if self.enabled:
            # LangSmith automatically tracks this
            pass


def configure_langsmith():
    """
    Configure LangSmith monitoring if API key is available.
    
    Sets up environment variables for LangSmith tracing.
    """
    api_key = os.getenv("LANGCHAIN_API_KEY")
    
    if api_key:
        # Enable tracing
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        
        # Set project name
        if not os.getenv("LANGCHAIN_PROJECT"):
            os.environ["LANGCHAIN_PROJECT"] = "research-agent"
        
        print("✅ LangSmith configured for monitoring")
        return True
    else:
        print("⚠️  LangSmith not configured (no API key)")
        return False


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

