"""Minimum iteration middleware for research agent.

This middleware ensures the agent performs a minimum number of iterations
before allowing completion. This is particularly useful for local models
that may stop too early without structured output enforcement.
"""

from typing import Any, Dict, Optional

from langchain.agents.middleware.types import AgentMiddleware, AgentState
from langchain_core.messages import AIMessage


class MinimumIterationMiddleware(AgentMiddleware[AgentState, None]):
    """Middleware that prevents agent from finishing before minimum iterations.
    
    This middleware tracks the number of model calls (iterations) and prevents
    the agent from generating a final answer until the minimum threshold is met.
    
    Key behaviors:
    - Tracks iteration count via model calls
    - Detects when agent tries to finish (no tool calls in response)
    - Forces continuation by removing final answer if below minimum
    - Injects continuation message to encourage more research
    
    Args:
        min_iterations: Minimum number of iterations required (default: 3)
        enable_for_model_types: List of model types to enable for (default: ["local"])
    """

    def __init__(
        self,
        min_iterations: int = 3,
        enable_for_model_types: Optional[list[str]] = None,
    ) -> None:
        """Initialize the middleware.
        
        Args:
            min_iterations: Minimum iterations before allowing completion
            enable_for_model_types: Model types to enable this for (default: ["local"])
        """
        super().__init__()
        self.min_iterations = min_iterations
        self.enable_for_model_types = enable_for_model_types or ["local"]
        self._iteration_count = 0
        self._enabled = False

    def before_agent(self, state: AgentState, runtime: Any) -> Optional[Dict[str, Any]]:
        """Track iteration count before each agent call.
        
        Args:
            state: Current agent state
            runtime: Runtime context
            
        Returns:
            None - no state modifications needed
        """
        # Increment iteration counter
        self._iteration_count += 1
        return None

    def after_agent(self, state: AgentState, runtime: Any) -> Optional[Dict[str, Any]]:
        """Check if agent is trying to finish prematurely.
        
        If the agent generates a response without tool calls (indicating it wants
        to finish) and we're below the minimum iteration threshold, remove the
        final answer and inject a continuation message.
        
        Args:
            state: Current agent state
            runtime: Runtime context
            
        Returns:
            Modified state if forcing continuation, None otherwise
        """
        # Only enforce if we're below minimum iterations
        if self._iteration_count >= self.min_iterations:
            return None

        # Get messages from state
        messages = state.get("messages", [])
        if not messages:
            return None

        # Check if last message is from AI (agent's response)
        last_message = messages[-1]
        if not isinstance(last_message, AIMessage):
            return None

        # Check if AI is trying to finish (no tool calls)
        has_tool_calls = (
            hasattr(last_message, "tool_calls") 
            and last_message.tool_calls 
            and len(last_message.tool_calls) > 0
        )

        if not has_tool_calls:
            # Agent is trying to finish - force continuation
            remaining = self.min_iterations - self._iteration_count
            
            # Create a continuation message encouraging more research
            continuation_msg = AIMessage(
                content=(
                    f"I need to gather more comprehensive information. "
                    f"Continuing research (minimum {remaining} more iteration(s) required)."
                ),
                tool_calls=[],
            )
            
            # Replace the final answer with continuation message
            modified_messages = messages[:-1] + [continuation_msg]
            
            return {
                "messages": modified_messages,
            }

        return None

    def reset(self) -> None:
        """Reset iteration counter for new research task."""
        self._iteration_count = 0

