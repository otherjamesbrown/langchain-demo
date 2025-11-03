"""
Testing framework for research agent validation.

This module provides a comprehensive testing framework that:
- Runs identical tests across multiple models
- Compares model outputs against baseline expectations
- Uses fuzzy matching logic for flexible validation
- Supports both automated CLI execution and interactive UI execution
"""

from src.testing.baseline import (
    MatchType,
    FieldExpectation,
    TestBaseline,
)
from src.testing.matchers import FieldMatcher

# Note: test_runner imports are lazy-loaded to avoid requiring LangChain
# when only using baseline/matcher functionality
__all__ = [
    "MatchType",
    "FieldExpectation",
    "TestBaseline",
    "FieldMatcher",
]

# Lazy imports for components that require LangChain
def _lazy_import_test_runner():
    """Lazy import for test runner components that require LangChain."""
    from src.testing.test_runner import (
        FieldMatchResult,
        ModelTestResult,
        TestExecutionResult,
        TestRunner,
    )
    return {
        "FieldMatchResult": FieldMatchResult,
        "ModelTestResult": ModelTestResult,
        "TestExecutionResult": TestExecutionResult,
        "TestRunner": TestRunner,
    }

# Make lazy imports available via getattr for dynamic access
def __getattr__(name):
    if name in ["FieldMatchResult", "ModelTestResult", "TestExecutionResult", "TestRunner"]:
        components = _lazy_import_test_runner()
        return components[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

