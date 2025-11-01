"""
Tools module for LangChain research agent.

This module exports all available tools that agents can use.
"""

from src.tools.web_search import web_search_tool, TOOLS as WEB_SEARCH_TOOLS
from src.tools.data_loaders import (
    load_csv_file,
    load_markdown_file,
    list_companies_from_csv,
    DATA_LOADER_TOOLS
)

# Combine all tools
TOOLS = WEB_SEARCH_TOOLS + DATA_LOADER_TOOLS

__all__ = [
    "web_search_tool",
    "load_csv_file",
    "load_markdown_file",
    "list_companies_from_csv",
    "TOOLS",
    "WEB_SEARCH_TOOLS",
    "DATA_LOADER_TOOLS"
]

