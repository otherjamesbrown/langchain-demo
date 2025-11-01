"""Agent package exposing high-level research agent helpers.

This package collects educational agent examples that combine LangChain's
modern agent runtime with the project's custom tooling. Each module is
designed to be approachable for learners exploring how ReAct-style
reasoning maps onto LangChain's create_agent API.
"""

from src.agent.research_agent import ResearchAgent, ResearchAgentResult

__all__ = ["ResearchAgent", "ResearchAgentResult"]

