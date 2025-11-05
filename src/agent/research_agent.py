#!/usr/bin/env python3
"""Educational research agent built on LangChain's agent runtime.

This module shows how to migrate from the legacy ``create_react_agent`` helper
to the modern ``create_agent`` factory introduced in LangChain 0.3+. The agent
follows the ReAct pattern, mixing reasoning with the custom Tavily-powered web
search tool defined in ``src.tools.web_search``. The implementation focuses on
teaching:

1. How to prepare chat models for different providers using a factory helper
2. How to assemble a LangChain agent graph with middleware for safety limits
3. How to observe intermediate reasoning steps for instructional dashboards

The Streamlit UI imports :class:`ResearchAgent` and calls
:meth:`ResearchAgent.research_company` to execute a full research loop.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain.agents import create_agent
from langchain.agents.middleware.model_call_limit import ModelCallLimitMiddleware
from langchain.agents.middleware.tool_call_limit import ToolCallLimitMiddleware
from langchain.agents.middleware.types import AgentMiddleware, AgentState
from langchain.agents.middleware.types import ToolCallRequest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.prompts import PromptTemplate
from pydantic import ValidationError

from src.agent.min_iteration_middleware import MinimumIterationMiddleware  # type: ignore[import]
from src.models.model_factory import get_chat_model  # type: ignore[import]
from src.models.local_registry import (  # type: ignore[import]
    DEFAULT_LOCAL_MODEL_KEY,
    get_local_model_config,
    guess_local_model_key,
)
from src.models.structured_output import select_structured_output_strategy  # type: ignore[import]
from src.tools.models import CompanyInfo
from src.tools.web_search import TOOLS


@dataclass
class ResearchAgentResult:
    """Structured result of a research run for a single company."""

    company_name: str
    success: bool
    raw_output: str
    execution_time_seconds: float
    iterations: int
    model_input: Dict[str, Any] = field(default_factory=dict)
    company_info: Optional[CompanyInfo] = None
    intermediate_steps: List[Dict[str, Any]] = field(default_factory=list)
    model_display_name: Optional[str] = None
    model_key: Optional[str] = None
    model_kwargs: Dict[str, Any] = field(default_factory=dict)


class StepTrackerMiddleware(AgentMiddleware[AgentState, None]):
    """Middleware that captures intermediate thoughts and tool calls.

    By inheriting from :class:`AgentMiddleware` we can hook into the agent loop
    without modifying LangChain internals. The Streamlit dashboard displays
    ``intermediate_steps`` to help learners follow the ReAct cycle.
    """

    def __init__(self, enable_diagnostics: bool = False) -> None:
        self._current_steps: List[Dict[str, Any]] = []
        self.last_run_steps: List[Dict[str, Any]] = []
        self._model_calls: int = 0
        self.last_run_iterations: int = 0
        self.enable_diagnostics = enable_diagnostics
        self._generation_start_time: Optional[float] = None
        
        # Import diagnostic utilities if enabled
        if self.enable_diagnostics:
            try:
                from src.utils.llama_diagnostics import (
                    log_prompt_stats,
                    log_response_stats,
                    log_agent_iteration_summary,
                    log_context_budget_analysis,
                    estimate_token_count,
                )
                self._log_prompt = log_prompt_stats
                self._log_response = log_response_stats
                self._log_iteration = log_agent_iteration_summary
                self._log_budget = log_context_budget_analysis
                self._estimate_tokens = estimate_token_count
            except ImportError:
                self.enable_diagnostics = False

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------
    def before_agent(self, state: AgentState, runtime: Any) -> Optional[Dict[str, Any]]:
        """Reset captured state before each agent execution."""

        self._current_steps = []
        self._model_calls = 0
        self.last_run_steps = []
        self.last_run_iterations = 0
        return None

    def before_model(self, state: AgentState, runtime: Any) -> Optional[Dict[str, Any]]:
        """Log prompt details before model call (for diagnostics)."""
        
        if self.enable_diagnostics and hasattr(self, "_log_prompt"):
            # Extract prompt from state
            messages = state.get("messages", [])
            if messages:
                # Construct full prompt text from messages
                prompt_parts = []
                for msg in messages:
                    content = _message_to_text(msg)
                    role = getattr(msg, "role", type(msg).__name__)
                    prompt_parts.append(f"[{role}]: {content}")
                
                full_prompt = "\n\n".join(prompt_parts)
                self._log_prompt(full_prompt, self._model_calls + 1, self._model_calls + 1)
        
        # Start timing
        self._generation_start_time = time.time()
        return None

    def after_model(self, state: AgentState, runtime: Any) -> Optional[Dict[str, Any]]:
        """Record every language model call as an iteration step."""

        self._model_calls += 1
        last_message = state["messages"][-1]
        response_text = _message_to_text(last_message)
        
        # Calculate generation time
        generation_time = 0.0
        if self._generation_start_time:
            generation_time = time.time() - self._generation_start_time
        
        self._current_steps.append(
            {
                "type": "model",
                "iteration": self._model_calls,
                "content": response_text,
                "generation_time": generation_time,
            }
        )
        
        # Diagnostic logging
        if self.enable_diagnostics and hasattr(self, "_log_response"):
            self._log_response(
                response_text,
                self._model_calls,
                self._model_calls,
                generation_time,
                is_final=False,
            )
        
        return None

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Any,
    ) -> ToolMessage:
        """Capture tool invocations while delegating execution to LangChain."""

        tool_name = getattr(request.tool, "name", request.tool_call.get("name", "unknown_tool"))
        tool_args = request.tool_call.get("args", {})
        response: ToolMessage = handler(request)
        self._current_steps.append(
            {
                "type": "tool",
                "iteration": self._model_calls,
                "tool_name": tool_name,
                "arguments": tool_args,
                "output": _message_to_text(response),
            }
        )
        return response

    def after_agent(self, state: AgentState, runtime: Any) -> Optional[Dict[str, Any]]:
        """Persist steps for access after ``create_agent`` finishes."""

        self.last_run_steps = list(self._current_steps)
        self.last_run_iterations = self._model_calls
        
        # Diagnostic logging: iteration summary
        if self.enable_diagnostics and hasattr(self, "_log_iteration"):
            self._log_iteration(
                iteration=self._model_calls,
                total_iterations=self._model_calls,
                agent_finished=True,
                reason="Agent completed execution",
            )
        
        return None

    @property
    def current_steps(self) -> List[Dict[str, Any]]:
        """Return a shallow copy of the steps captured so far."""

        return list(self._current_steps)

    @property
    def current_iteration_count(self) -> int:
        """Expose the number of model calls during the active run."""

        return self._model_calls


class ResearchAgent:
    """High-level interface for running the research workflow via LangChain."""

    def __init__(
        self,
        model_type: str = "local",
        verbose: bool = True,
        max_iterations: int = 10,
        instructions_path: Optional[str] = None,
        profiling_guide_path: Optional[str] = None,
        prompt_version_id: Optional[int] = None,  # NEW: Use specific prompt version
        prompt_name: Optional[str] = None,  # NEW: Use active version of named prompt
        prompt_version: Optional[str] = None,  # NEW: Use specific version string
        local_model: Optional[str] = None,
        model_path: Optional[str] = None,
        model_kwargs: Optional[Dict[str, Any]] = None,
        enable_diagnostics: bool = False,
    ) -> None:
        self.model_type = model_type
        self.verbose = verbose
        self.max_iterations = max_iterations
        self.instructions_path = instructions_path or _default_instruction_path()
        self.profiling_guide_path = profiling_guide_path or _default_profiling_guide_path()
        self.local_model = local_model
        self.model_path = model_path
        self._resolved_model_path: Optional[str] = None
        self._model_display_name: Optional[str] = None
        self.model_kwargs = model_kwargs or {}
        self.enable_diagnostics = enable_diagnostics

        # Pass diagnostics flag to model initialization
        if self.enable_diagnostics and self.model_type == "local":
            self.model_kwargs["enable_diagnostics"] = True

        # NEW: Load prompts from database if prompt_version_id or prompt_name provided
        # Educational: This demonstrates how to version prompts for A/B testing and
        # tracking prompt engineering experiments. The agent can load prompts from
        # the database instead of files, enabling systematic prompt versioning.
        if prompt_version_id:
            from src.prompts.prompt_manager import PromptManager
            prompt_version = PromptManager.get_version_by_id(prompt_version_id)
            if prompt_version:
                self._instructions = prompt_version.instructions_content
                self._profiling_guide = prompt_version.classification_reference_content or ""
                self._prompt_version_id = prompt_version_id
                self._prompt_name = prompt_version.prompt_name
                self._prompt_version = prompt_version.version
            else:
                raise ValueError(f"Prompt version ID {prompt_version_id} not found")
        elif prompt_name:
            from src.prompts.prompt_manager import PromptManager
            if prompt_version:
                prompt_version_obj = PromptManager.get_version(prompt_name, prompt_version)
            else:
                prompt_version_obj = PromptManager.get_active_version(prompt_name)
            
            if prompt_version_obj:
                self._instructions = prompt_version_obj.instructions_content
                self._profiling_guide = prompt_version_obj.classification_reference_content or ""
                self._prompt_version_id = prompt_version_obj.id
                self._prompt_name = prompt_version_obj.prompt_name
                self._prompt_version = prompt_version_obj.version
            else:
                raise ValueError(f"Prompt '{prompt_name}' (version: {prompt_version or 'active'}) not found")
        else:
            # Legacy: Load from files
            self._instructions = self._load_instructions()
            self._profiling_guide = self._load_profiling_guide()
            self._prompt_version_id = None
            self._prompt_name = None
            self._prompt_version = None

        self._instruction_summary = _summarise_markdown(self._instructions)
        self._classification_reference = _build_classification_reference(self._profiling_guide)
        self._system_prompt = self._build_system_prompt()
        self._user_prompt = self._build_user_prompt()
        self._step_tracker = StepTrackerMiddleware(enable_diagnostics=self.enable_diagnostics)
        self._resolve_model_metadata()
        self._agent = self._build_agent()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def research_company(self, company_name: str) -> ResearchAgentResult:
        """Execute the ReAct agent for a single company."""

        start_time = time.perf_counter()
        user_message = self._user_prompt.format(company_name=company_name)
        messages = [{"role": "user", "content": user_message}]
        inputs = {"messages": messages}
        # Capture the exact prompt state for educational transparency in the UI.
        model_input_payload = {
            "system_prompt": self._system_prompt,
            "messages": [message.copy() for message in messages],
            "instructions_path": self.instructions_path,
            "profiling_guide_path": self.profiling_guide_path,
            "instruction_summary": self._instruction_summary,
            "classification_reference": self._classification_reference,
            "model_display_name": self._model_display_name,
            "local_model_key": self.local_model,
            "model_path": self._resolved_model_path,
            "model_kwargs": self.model_kwargs,
        }

        try:
            # Set recursion_limit higher than max_iterations to allow middleware
            # to handle termination gracefully. LangGraph's default is 25, which
            # can be too low for complex research tasks. We set it to at least
            # 3x max_iterations or 50, whichever is higher.
            # ToolStrategy models (e.g., Gemini) may need higher limits due to
            # additional tool calls required for structured output.
            base_limit = max(self.max_iterations * 3, 50)
            # ToolStrategy adds extra iterations for structured output tool calls
            if self.model_type == "gemini":
                recursion_limit = base_limit * 2  # Gemini uses ToolStrategy
            else:
                recursion_limit = base_limit
            config = {"recursion_limit": recursion_limit}
            agent_output = self._agent.invoke(inputs, config=config)
        except Exception as exc:  # noqa: BLE001
            execution_time = time.perf_counter() - start_time
            steps = self._step_tracker.last_run_steps or self._step_tracker.current_steps
            iterations = (
                self._step_tracker.last_run_iterations
                or self._step_tracker.current_iteration_count
            )
            # Log the full exception for debugging, especially for remote models
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            logger.error(
                f"Agent execution failed for {self.model_type}: {exc}\n"
                f"{traceback.format_exc()}"
            )
            return ResearchAgentResult(
                company_name=company_name,
                success=False,
                raw_output=f"Agent execution error: {exc}",
                execution_time_seconds=execution_time,
                iterations=iterations,
                model_input=model_input_payload,
                intermediate_steps=steps,
                model_display_name=self._model_display_name,
                model_key=self.local_model,
            )

        execution_time = time.perf_counter() - start_time
        steps = self._step_tracker.last_run_steps or self._step_tracker.current_steps
        iterations = (
            self._step_tracker.last_run_iterations
            or self._step_tracker.current_iteration_count
        )
        final_message = _extract_final_ai_message(agent_output.get("messages", []))
        raw_output = _message_to_text(final_message) if final_message else ""

        # Extract structured response - ProviderStrategy returns it in 'structured_response' key
        structured_response = agent_output.get("structured_response")
        
        # Debug logging for structured output issues
        if structured_response is None and self.model_type != "local":
            # With ProviderStrategy, structured_response should always be present
            # Log what we got instead for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Structured response is None for {self.model_type} model. "
                f"Agent output keys: {list(agent_output.keys())}. "
                f"Raw output length: {len(raw_output)}"
            )

        company_info = self._parse_company_info(structured_response, raw_output, company_name)
        success = company_info is not None

        # Final diagnostic logging
        if self.enable_diagnostics and self.model_type == "local":
            try:
                from src.utils.llama_diagnostics import (
                    log_context_budget_analysis,
                    estimate_token_count,
                )
                
                # Get context window from model_kwargs
                n_ctx = self.model_kwargs.get("n_ctx", 8192)
                max_tokens = self.model_kwargs.get("max_tokens", 4096)
                
                # Estimate tokens from all messages
                all_messages = agent_output.get("messages", [])
                total_input_tokens = 0
                total_output_tokens = 0
                
                for msg in all_messages:
                    msg_text = _message_to_text(msg)
                    msg_tokens = estimate_token_count(msg_text)
                    # Roughly classify as input or output based on message type
                    if isinstance(msg, AIMessage):
                        total_output_tokens += msg_tokens
                    else:
                        total_input_tokens += msg_tokens
                
                log_context_budget_analysis(
                    n_ctx=n_ctx,
                    estimated_input_tokens=total_input_tokens,
                    estimated_output_tokens=total_output_tokens,
                    max_tokens=max_tokens,
                )
            except ImportError:
                pass

        return ResearchAgentResult(
            company_name=company_name,
            success=success,
            raw_output=raw_output,
            execution_time_seconds=execution_time,
            iterations=iterations,
            model_input=model_input_payload,
            company_info=company_info,
            intermediate_steps=steps,
            model_display_name=self._model_display_name,
            model_key=self.local_model,
            model_kwargs=self.model_kwargs,
        )

    # ------------------------------------------------------------------
    # Agent construction helpers
    # ------------------------------------------------------------------
    def _build_agent(self) -> Any:
        """Create the LangChain agent graph with safety middleware."""

        chat_model = self._initialise_model()

        # Base middleware for all models
        middleware = [
            self._step_tracker,
        ]
        
        # NOTE: MinimumIterationMiddleware was attempted but doesn't work effectively
        # The middleware can inject continuation messages, but the agent still stops
        # after 1 iteration. The injected messages also clutter the UI display.
        # 
        # Root cause: Without structured output enforcement (which ChatLlamaCpp lacks),
        # there's no mechanism to force comprehensive research. The agent decides it's
        # "done" based on its own judgment, which middleware cannot override.
        #
        # Leaving this disabled to avoid UI clutter without functional benefit.
        # if self.model_type == "local":
        #     middleware.append(MinimumIterationMiddleware(min_iterations=3))
        
        # Add safety limits
        middleware.extend([
            ModelCallLimitMiddleware(run_limit=self.max_iterations, exit_behavior="end"),
            ToolCallLimitMiddleware(run_limit=self.max_iterations, exit_behavior="end"),
        ])

        # Structured output strategy selection:
        # Uses centralized selector to determine the best strategy based on model capabilities.
        # See src.models.structured_output for details on strategy selection logic.
        #
        # Strategy types:
        # - ProviderStrategy: Native structured output (GPT-4o, Claude 3, Gemini)
        # - ToolStrategy: Artificial tool calling (GPT-4o-mini, models without native support)
        # - None: No structured output (ChatLlamaCpp - doesn't support tool_choice parameter)
        #
        # The selector handles model-specific capabilities automatically.
        # Try to extract model name from model_kwargs or database configuration
        model_name = None
        if isinstance(self.model_kwargs, dict):
            model_name = self.model_kwargs.get("model_name")
        
        # If not in kwargs, try to get from database configuration
        if not model_name and self.model_type != "local":
            try:
                from src.database.operations import get_default_model_configuration
                db_model = get_default_model_configuration()
                if db_model and db_model.provider == self.model_type and db_model.api_identifier:
                    model_name = db_model.api_identifier
            except Exception:
                pass  # Fallback to model introspection
        
        response_format = select_structured_output_strategy(
            model=chat_model,
            model_type=self.model_type,
            schema=CompanyInfo,
            model_name=model_name,
        )

        return create_agent(
            model=chat_model,
            tools=TOOLS,
            system_prompt=self._system_prompt,
            middleware=middleware,
            response_format=response_format,
        )

    def _initialise_model(self) -> BaseChatModel:
        """Load a chat-capable model using the shared factory."""

        # ``get_chat_model`` handles provider selection and environment variables.
        # Keeping all configuration in one place makes it easier for learners to
        # swap between local and hosted providers.
        return get_chat_model(
            model_type=self.model_type,
            model_path=self._resolved_model_path,
            temperature=0.2,
            local_model_name=self.local_model,
            verbose=self.verbose,
            **self.model_kwargs,
        )

    def _resolve_model_metadata(self) -> None:
        """Resolve display name and path for the selected model."""

        if self.model_type != "local":
            model_alias = self.model_kwargs.get("model_name") if isinstance(self.model_kwargs, dict) else None
            self._model_display_name = model_alias or self.model_type.title()
            self._resolved_model_path = None
            return

        # Prefer explicit path, otherwise fall back to registry key selection.
        candidate_path = self.model_path or os.getenv("MODEL_PATH")
        if candidate_path:
            resolved = Path(candidate_path).expanduser()
            self._resolved_model_path = str(resolved)
            inferred_key = self.local_model or guess_local_model_key(resolved)
            if inferred_key:
                try:
                    config = get_local_model_config(inferred_key)
                    self.local_model = config.key
                    self._model_display_name = config.display_name
                    return
                except KeyError:
                    self.local_model = inferred_key
            self._model_display_name = resolved.name
            return

        candidate_key = (
            (self.local_model or os.getenv("LOCAL_MODEL_NAME") or DEFAULT_LOCAL_MODEL_KEY)
            .strip()
            .lower()
        )

        try:
            config = get_local_model_config(candidate_key)
            resolved = config.resolve_path()
            self.local_model = config.key
            self._resolved_model_path = str(resolved)
            self._model_display_name = config.display_name
        except KeyError:
            self.local_model = candidate_key
            self._resolved_model_path = None
            self._model_display_name = f"local ({candidate_key})"

    def _build_system_prompt(self) -> str:
        """Combine research rules with formatting requirements."""

        schema_fields = ", ".join(CompanyInfo.model_fields.keys())
        return (
            "You are a focused company research analyst following the ReAct pattern. "
            "Think step-by-step, decide whether a web search is required, and only "
            "produce answers grounded in retrieved evidence.\n\n"
            "IMPORTANT RESEARCH PROCESS:\n"
            "1. Start with a general company overview search\n"
            "2. Make additional searches for missing information\n"
            "3. Search for specific data points: size, revenue, funding\n"
            "4. Verify you have comprehensive information before finishing\n"
            "5. Make AT LEAST 3-4 web searches to ensure thorough research\n\n"
            "DO NOT provide a final answer until you have:\n"
            "- Company basics (name, website, location, founded)\n"
            "- Business details (description)\n"
            "- Size/scale data (employees, revenue if available)\n\n"
            "Research instructions (GTM playbook summary):\n"
            f"{self._instruction_summary}\n\n"
            "Classification reference (choose labels from prompts/company-profiling-guide.md):\n"
            f"{self._classification_reference}\n\n"
            "Formatting requirements:\n"
            "- Return a final answer as JSON matching the CompanyInfo schema.\n"
            "- If data is unavailable, use null or an empty list rather than guessing.\n"
            "- Include concise text in the description summarising the findings.\n"
            "- Cite URLs inline when referencing specific claims.\n\n"
            "CompanyInfo schema keys (complete set, order not important):\n"
            f"{schema_fields}\n"
        )

    def _build_user_prompt(self) -> PromptTemplate:
        """Create the human message template sent to the agent."""

        template = (
            "Research the organisation named {company_name}.\n"
            "Follow the provided instructions, deliberate about missing data, and "
            "call the web_search_tool whenever you need fresh context."
        )
        return PromptTemplate.from_template(template)

    def _load_instructions(self) -> str:
        """Load research instructions from the consolidated prompt file.
        
        Extracts the section between "# RESEARCH INSTRUCTIONS" and "# CLASSIFICATION REFERENCE".
        Falls back to entire file content if section markers not found.
        """

        instruction_path = Path(self.instructions_path)
        if not instruction_path.exists():
            raise FileNotFoundError(
                "Research instructions not found. Update instructions_path to point to a markdown file."
            )
        
        content = instruction_path.read_text(encoding="utf-8").strip()
        
        # Try to extract the RESEARCH INSTRUCTIONS section
        if "# RESEARCH INSTRUCTIONS" in content:
            parts = content.split("# RESEARCH INSTRUCTIONS", 1)
            if len(parts) > 1:
                section = parts[1].split("# CLASSIFICATION REFERENCE", 1)[0].strip()
                if section:
                    return section
        
        # Fallback to entire file if sections not found
        return content

    def _load_profiling_guide(self) -> str:
        """Load classification reference from the consolidated prompt file.
        
        Extracts the section between "# CLASSIFICATION REFERENCE" and next major section.
        Falls back to entire file content if section markers not found.
        """

        guide_path = Path(self.profiling_guide_path)
        if not guide_path.exists():
            raise FileNotFoundError(
                "Company profiling guide not found. Update profiling_guide_path to a markdown file."
            )
        
        content = guide_path.read_text(encoding="utf-8").strip()
        
        # Try to extract the CLASSIFICATION REFERENCE section
        if "# CLASSIFICATION REFERENCE" in content:
            parts = content.split("# CLASSIFICATION REFERENCE", 1)
            if len(parts) > 1:
                # Stop at next major section (starts with # followed by space)
                section = parts[1]
                # Find next major section header (## or # at start of line)
                lines = section.split('\n')
                section_lines = []
                for line in lines:
                    # Stop if we hit a new major section (## Details or # DETAILED)
                    if line.strip().startswith('## ') and 'Details' in line:
                        break
                    if line.strip().startswith('# DETAILED'):
                        break
                    section_lines.append(line)
                section_text = '\n'.join(section_lines).strip()
                if section_text:
                    return section_text
        
        # Fallback to entire file if sections not found
        return content

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------
    def _parse_company_info(
        self,
        structured_response: Any,
        raw_output: str,
        company_name: str,
    ) -> Optional[CompanyInfo]:
        """Convert agent output into :class:`CompanyInfo` when possible."""

        if isinstance(structured_response, CompanyInfo):
            return structured_response

        if isinstance(structured_response, dict):
            structured_response.setdefault("company_name", company_name)
            try:
                return CompanyInfo.model_validate(structured_response)
            except ValidationError as e:
                # Log validation errors for debugging, especially for remote models using ProviderStrategy
                if self.model_type != "local":
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"CompanyInfo validation failed for {self.model_type}: {e}. "
                        f"Received dict keys: {list(structured_response.keys())}"
                    )

        try:
            candidate = json.loads(raw_output)
            if isinstance(candidate, dict):
                candidate.setdefault("company_name", company_name)
                return CompanyInfo.model_validate(candidate)
        except (json.JSONDecodeError, ValidationError):
            pass

        fallback = _fallback_company_info(raw_output, company_name)
        if fallback:
            return fallback

        return None


def _fallback_company_info(raw_output: str, company_name: str) -> Optional[CompanyInfo]:
    """Extract best-effort company info from unstructured model output."""

    if not raw_output.strip():
        return None

    def extract_text(label: str) -> str:
        pattern = re.compile(rf"{label}\s*[:\-]\s*(.+)", re.IGNORECASE)
        match = pattern.search(raw_output)
        if match:
            value = match.group(1).strip()
            value = value.split("\n")[0].strip()
            return value.rstrip("., ")
        return ""

    def extract_list(label: str) -> list[str]:
        text = extract_text(label)
        if not text:
            return []
        items = re.split(r",|;|\n|\-\s", text)
        cleaned = [item.strip() for item in items if item and item.strip()]
        # Deduplicate while preserving order
        seen = set()
        ordered: list[str] = []
        for item in cleaned:
            if item.lower() in seen:
                continue
            seen.add(item.lower())
            ordered.append(item)
        return ordered

    def extract_year(label: str) -> Optional[int]:
        pattern = re.compile(rf"{label}\s*[:\-]\s*(\d{4})", re.IGNORECASE)
        match = pattern.search(raw_output)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None

    company_size = extract_text("Company Size") or "Unknown"
    headquarters = extract_text("Headquarters") or "Unknown"
    founded = extract_year("Founded")
    description = extract_text("Company Description") or raw_output[:500].strip()
    website = extract_text("Website")
    revenue = extract_text("Revenue") or None
    funding_stage = extract_text("Funding Stage") or None

    def extract_classification(
        label: str,
        *,
        aliases: Tuple[str, ...] = (),
    ) -> Optional[str]:
        """Extract a GTM classification value, trying primary label and aliases."""

        candidate_labels: Tuple[str, ...] = (label, *aliases)
        for candidate in candidate_labels:
            value = extract_text(candidate) or None
            if value:
                return value
        return None

    growth_stage = extract_classification("Growth Stage")
    industry_vertical = extract_classification("Industry Vertical")
    sub_industry_vertical = extract_classification("Sub-Industry Vertical")
    business_and_technology_adoption = extract_classification(
        "Business & Technology Adoption",
        aliases=("Business and Technology Adoption",),
    )

    try:
        return CompanyInfo.model_validate(
            {
                "company_name": company_name,
                "company_size": company_size,
                "headquarters": headquarters,
                "founded": founded,
                "description": description,
                "website": website or None,
                "revenue": revenue,
                "funding_stage": funding_stage,
                "growth_stage": growth_stage,
                "industry_vertical": industry_vertical,
                "sub_industry_vertical": sub_industry_vertical,
                "business_and_technology_adoption": business_and_technology_adoption,
            }
        )
    except ValidationError:
        return None


# ----------------------------------------------------------------------
# Utility helpers
# ----------------------------------------------------------------------

def _default_instruction_path() -> str:
    """Return the default path to the consolidated research agent prompt file."""

    project_root = Path(__file__).resolve().parent.parent.parent
    return str(project_root / "prompts" / "research-agent-prompt.md")


def _default_profiling_guide_path() -> str:
    """Return the default path to the consolidated research agent prompt file.
    
    Note: Now uses the same consolidated file as instructions_path.
    The code extracts different sections from the single file.
    """

    project_root = Path(__file__).resolve().parent.parent.parent
    return str(project_root / "prompts" / "research-agent-prompt.md")


def _summarise_markdown(content: str, max_lines: int = 28) -> str:
    """Extract a concise bullet list from a markdown document.

    We keep the summary short to avoid exceeding the context window while
    still surfacing the instructional intent of the markdown files.
    """

    lines: list[str] = []
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped[0].isdigit() and stripped[1:2] == ".":
            lines.append(stripped)
        elif stripped.startswith(('-', '*')):
            lines.append(stripped.lstrip('-* ').strip())
        if len(lines) >= max_lines:
            break

    if not lines:
        # Fallback to the first few non-empty lines if no bullets were found.
        lines = [line.strip() for line in content.splitlines() if line.strip()][:max_lines]

    return "\n".join(lines)


def _build_classification_reference(profiling_guide: Optional[str] = None) -> str:
    """Return concise GTM classification options extracted from the profiling guide.
    
    Tries to parse from the provided profiling_guide content or the consolidated prompt file's 
    CLASSIFICATION REFERENCE section. Falls back to hardcoded defaults if parsing fails.
    
    Args:
        profiling_guide: Optional pre-loaded profiling guide content (from database)
    """

    # Use provided profiling guide if available (from database)
    if profiling_guide:
        content = profiling_guide
    else:
        # Try to load and parse from the consolidated file
        try:
            project_root = Path(__file__).resolve().parent.parent.parent
            prompt_file = project_root / "prompts" / "research-agent-prompt.md"
            
            if prompt_file.exists():
                content = prompt_file.read_text(encoding="utf-8")
            else:
                content = ""
        except Exception:
            content = ""
    
    # Extract CLASSIFICATION REFERENCE section
    try:
        if content and "# CLASSIFICATION REFERENCE" in content:
            parts = content.split("# CLASSIFICATION REFERENCE", 1)
            if len(parts) > 1:
                section = parts[1].split("# DETAILED", 1)[0].strip()
                
                # Parse ## headers and their content
                lines = section.split('\n')
                parsed_sections = {}
                current_header = None
                current_content = []
                
                for line in lines:
                    line_stripped = line.strip()
                    # Skip HTML comments and empty lines
                    if line_stripped.startswith('<!--') or not line_stripped or line_stripped == '':
                        continue
                    
                    # Check for ## header
                    if line_stripped.startswith('## '):
                        # Save previous section if any
                        if current_header and current_content:
                            # Join content lines, removing extra whitespace
                            content_str = ' '.join(current_content).strip()
                            if content_str:
                                parsed_sections[current_header] = content_str
                        
                        # Start new section
                        current_header = line_stripped[3:].strip()
                        current_content = []
                    elif current_header:
                        # Add content to current section (skip markdown list markers)
                        if line_stripped:
                            # Remove leading dashes/bullets and clean up
                            cleaned = line_stripped.lstrip('-* ').strip()
                            if cleaned and not cleaned.startswith('<!--'):
                                current_content.append(cleaned)
                
                # Save last section
                if current_header and current_content:
                    content_str = ' '.join(current_content).strip()
                    if content_str:
                        parsed_sections[current_header] = content_str
                
                # If we parsed sections, use them
                if parsed_sections:
                    reference_lines = [
                        f"- {name}: {options}"
                        for name, options in parsed_sections.items()
                    ]
                    return "\n".join(reference_lines)
    except Exception:
        # Fall through to hardcoded defaults
        pass

    # Fallback to hardcoded defaults (backward compatibility)
    sections: dict[str, str] = {
        "Growth Stage": "Pre-Seed/Idea | Startup | Scale-Up | Mature/Enterprise",
        "Company Size": "Micro/Small (<50) | SMB (50-500) | Mid-Market (500-1000) | Enterprise (>1000)",
        "Industry Vertical": (
            "SaaS (SMB/Scale) | SaaS (Enterprise Scale) | Media & Entertainment | Gaming | "
            "E-commerce & Retail | AdTech/MarTech | FinTech | Healthcare & Life Sciences | "
            "EdTech | Government & Public Sector | Manufacturing/Industrial & IoT | "
            "Telecommunications & Networking | Energy & Utilities | Web3/Blockchain | "
            "Professional Services | Transportation & Logistics"
        ),
        "Financial Health": (
            "Bootstrapped/Indie | VC-Funded (Early) | VC-Funded (Growth) | PE-Backed | "
            "Public (Profitable) | Public (Unprofitable)"
        ),
        "Budget Maturity": "Ad Hoc Spend | Team Budget | Central IT Budget | CCoE/Governance",
        "Cloud Spend Capacity": "< $5K/mo | $5K-$50K/mo | $50K-$250K/mo | $250K+/mo",
        "Procurement Process": "Minimal/Self-Service | Lightweight Review | Formal Review | Enterprise Procurement",
        "Business & Technology Adoption": (
            "Digital Laggards | Digitally-Adopting | Digitally-Transforming | Tech-Enabled Service Businesses | "
            "Digital-Native (SMB/Scale) | Digital-Native (Enterprise Scale) | Deep Tech & R&D-Driven"
        ),
        "Buyer Journey": "Practitioner-Led | Organization-Led | Partner-Led | Hybrid",
        "Primary Workload Philosophy": (
            "Performance-Intensive | Distributed & Edge-Native | Reliability & Simplicity | "
            "Storage & Data-Centric | Orchestration-Native | Cost-Optimization & Efficiency"
        ),
        "Key Personas": "Deciders | Approvers/Influencers | Users/Practitioners | Partners",
    }

    reference_lines = [
        f"- {name}: {options}"
        for name, options in sections.items()
    ]

    return "\n".join(reference_lines)


def _extract_final_ai_message(messages: List[BaseMessage]) -> Optional[AIMessage]:
    """Grab the last AI message from the agent trace."""

    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return message
    return None


def _message_to_text(message: BaseMessage | ToolMessage | None) -> str:
    """Safely convert LangChain message objects into plain text."""

    if message is None:
        return ""

    content = message.content
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_chunks = []
        for part in content:
            if isinstance(part, dict):
                text_chunks.append(part.get("text", ""))
        return "\n".join(chunk for chunk in text_chunks if chunk)

    return str(content)

