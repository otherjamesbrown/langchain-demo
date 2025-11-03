"""Minimum iteration middleware for research agent.

This middleware ensures the agent performs a minimum number of iterations
before allowing completion. This is particularly useful for local models
that may stop too early without structured output enforcement.
"""

from typing import Any, Dict, Optional

from langchain.agents.middleware.types import AgentMiddleware, AgentState, hook_config
from langchain_core.messages import AIMessage, HumanMessage


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
        """Reset iteration counter at start of agent execution.
        
        Args:
            state: Current agent state
            runtime: Runtime context
            
        Returns:
            None - no state modifications needed
        """
        # Reset counter for new research task
        self._iteration_count = 0
        return None
    
    @hook_config(can_jump_to=["model"])
    def after_model(self, state: AgentState, runtime: Any) -> Optional[Dict[str, Any]]:
        """Check if model is trying to finish prematurely.
        
        This hook is called after each model generation. If the model generates
        a response without tool calls (indicating it wants to finish) and we're
        below the minimum iteration threshold, we jump back to "model" to force
        another iteration with a continuation request.
        
        Uses LangChain's jump_to mechanism to repeat the model call cycle.
        
        Args:
            state: Current agent state
            runtime: Runtime context
            
        Returns:
            Modified state with jump_to if forcing continuation, None otherwise
        """
        # Increment iteration counter
        self._iteration_count += 1
        
        # Only enforce if we're below minimum iterations
        if self._iteration_count >= self.min_iterations:
            return None

        # Get messages from state
        messages = state.get("messages", [])
        if not messages:
            return None

        # Check if last message is from AI (model's response)
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
            # Model is trying to finish - force continuation using jump_to
            remaining = self.min_iterations - self._iteration_count
            
            # Create a continuation request as a HumanMessage
            continuation_request = HumanMessage(
                content=(
                    f"Your research is incomplete. You have performed {self._iteration_count} "
                    f"iteration(s) but need at least {self.min_iterations}. "
                    f"Please make {remaining} more web search(es) to gather comprehensive "
                    f"information about missing data points (competitors, revenue, funding, etc.)."
                )
            )
            
            # Replace the premature final answer with continuation request
            # and jump back to "model" to force another iteration
            modified_messages = messages[:-1] + [continuation_request]
            
            return {
                "messages": modified_messages,
                "jump_to": "model",  # Force agent to call model again
            }

        return None

    def reset(self) -> None:
        """Reset iteration counter for new research task."""
        self._iteration_count = 0

