"""
Research module for two-phase architecture.

This module provides Phase 1 (search collection) and Phase 2 (LLM processing)
workflows for the improved research architecture.
"""

from src.research.query_generator import (
    generate_queries,
    generate_queries_for_companies,
    get_pending_queries,
    DEFAULT_QUERY_TEMPLATES,
    QueryTemplate
)

from src.research.search_executor import (
    execute_search,
    execute_all_pending_queries,
    get_search_results_for_company
)

from src.research.prompt_builder import (
    build_prompt,
    build_prompt_from_files,
    get_prompt_version,
    format_search_results
)

from src.research.llm_processor import (
    process_with_llm,
    process_company_with_multiple_models
)

__all__ = [
    "generate_queries",
    "generate_queries_for_companies",
    "get_pending_queries",
    "DEFAULT_QUERY_TEMPLATES",
    "QueryTemplate",
    "execute_search",
    "execute_all_pending_queries",
    "get_search_results_for_company",
    "build_prompt",
    "build_prompt_from_files",
    "get_prompt_version",
    "format_search_results",
    "process_with_llm",
    "process_company_with_multiple_models"
]

