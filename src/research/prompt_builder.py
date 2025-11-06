"""
Prompt builder for Phase 2: LLM processing.

This module combines research instructions with search results to create
prompts for LLM processing.

LangSmith Integration:
- Prompt building operations are traced with phase:llm-processing tags
- Tracks prompt length, search result counts, and prompt versioning
"""

from typing import List, Optional
from pathlib import Path
import hashlib
from src.database.schema import SearchHistory
from src.tools.data_loaders import load_markdown_content
from src.utils.monitoring import langsmith_phase_trace


def load_instructions(file_path: str) -> str:
    """
    Load research instructions from a markdown file.
    
    Args:
        file_path: Path to instructions file
        
    Returns:
        Instructions content as string
    """
    return load_markdown_content(file_path)


def format_search_results(search_results: List[SearchHistory]) -> str:
    """
    Format search results into a readable text block for the prompt.
    
    Args:
        search_results: List of SearchHistory objects with raw_results
        
    Returns:
        Formatted string containing all search results
    """
    if not search_results:
        return "No search results available."
    
    formatted_sections = []
    
    for i, result in enumerate(search_results, 1):
        section = f"\n{'='*70}\n"
        section += f"SEARCH RESULT {i} (Query: {result.query})\n"
        section += f"{'='*70}\n\n"
        
        if result.raw_results:
            for j, raw_result in enumerate(result.raw_results, 1):
                section += f"Source {j}:\n"
                section += f"  Title: {raw_result.get('title', 'N/A')}\n"
                section += f"  URL: {raw_result.get('url', 'N/A')}\n"
                section += f"  Content: {raw_result.get('content', 'N/A')}\n"
                if raw_result.get('relevance_score'):
                    section += f"  Relevance: {raw_result['relevance_score']}\n"
                section += "\n"
        else:
            # Fallback to summary if raw results not available
            section += result.results_summary or "No detailed results available."
        
        formatted_sections.append(section)
    
    return "\n".join(formatted_sections)


def build_prompt(
    instructions: str,
    company_name: str,
    search_results: List[SearchHistory],
    include_raw_results: bool = True
) -> str:
    """
    Build a complete prompt from instructions and search results.
    
    This function is traced with LangSmith using phase:llm-processing tags.
    
    Args:
        instructions: Research instructions/guidelines
        company_name: Name of the company being researched
        search_results: List of SearchHistory objects with results
        include_raw_results: Whether to include full search results
        
    Returns:
        Complete prompt string ready for LLM processing
    """
    # Trace prompt building with Phase 2 tags
    with langsmith_phase_trace(
        phase="llm-processing",
        company_name=company_name
    ) as trace:
        trace["metadata"]["num_search_results"] = len(search_results)
        trace["metadata"]["include_raw_results"] = include_raw_results
        trace["metadata"]["instructions_length"] = len(instructions)
        
        prompt_parts = []
        
        # Instructions section
        prompt_parts.append("# RESEARCH INSTRUCTIONS")
        prompt_parts.append("=" * 70)
        prompt_parts.append(instructions)
        prompt_parts.append("")
        
        # Company context
        prompt_parts.append("# COMPANY TO RESEARCH")
        prompt_parts.append("=" * 70)
        prompt_parts.append(f"Company Name: {company_name}")
        prompt_parts.append("")
        
        # Search results section
        if include_raw_results and search_results:
            prompt_parts.append("# SEARCH RESULTS")
            prompt_parts.append("=" * 70)
            prompt_parts.append("The following information has been gathered from web searches:")
            prompt_parts.append("")
            prompt_parts.append(format_search_results(search_results))
            prompt_parts.append("")
        
        # Task section
        prompt_parts.append("# TASK")
        prompt_parts.append("=" * 70)
        prompt_parts.append(
            f"Based on the instructions above and the search results provided, "
            f"extract structured information about {company_name}. "
            f"Provide a comprehensive summary with all available information."
        )
        
        prompt = "\n".join(prompt_parts)
        trace["metadata"]["prompt_length"] = len(prompt)
        
        return prompt


def get_prompt_version(instructions: str) -> str:
    """
    Generate a version hash for prompt tracking.
    
    Args:
        instructions: Instructions content
        
    Returns:
        Hash string representing the prompt version
    """
    return hashlib.sha256(instructions.encode()).hexdigest()[:16]


def build_prompt_from_files(
    instructions_path: str,
    company_name: str,
    search_results: List[SearchHistory]
) -> tuple[str, str]:
    """
    Build prompt from instruction file and search results.
    
    This function is traced with LangSmith using phase:llm-processing tags.
    
    Args:
        instructions_path: Path to instructions markdown file
        company_name: Company name
        search_results: Search results
        
    Returns:
        Tuple of (prompt_string, prompt_version_hash)
    """
    # Trace prompt building from files
    with langsmith_phase_trace(
        phase="llm-processing",
        company_name=company_name
    ) as trace:
        trace["metadata"]["instructions_path"] = instructions_path
        
        instructions = load_instructions(instructions_path)
        prompt = build_prompt(instructions, company_name, search_results)
        version = get_prompt_version(instructions)
        
        trace["metadata"]["prompt_version"] = version
        
        return prompt, version

