"""
Baseline registry for test cases.

This module provides a registry of all test baselines and a function to
retrieve them by name. Baselines define expected values and validation
rules for research agent tests.

Educational Focus:
- Shows how to organize test definitions in a centralized registry
- Enables easy discovery and retrieval of test cases
"""

from typing import Dict
from src.testing.baseline import TestBaseline

# Import all baselines
from src.testing.baselines.bitmovin import BITMOVIN_BASELINE

# Registry mapping test names to baselines
_BASELINE_REGISTRY: Dict[str, TestBaseline] = {
    "bitmovin": BITMOVIN_BASELINE,
    "bitmovin_research": BITMOVIN_BASELINE,  # Alias
}


def get_baseline(test_name: str) -> TestBaseline:
    """
    Get a test baseline by name.
    
    Educational: This function provides a centralized way to retrieve
    test baselines. It raises a clear error if the baseline doesn't exist,
    making it easy to discover available tests.
    
    Args:
        test_name: Name of the test (e.g., "bitmovin")
        
    Returns:
        TestBaseline for the specified test
        
    Raises:
        ValueError: If test name not found in registry
        
    Example:
        baseline = get_baseline("bitmovin")
        runner = TestRunner(model_configs=models)
        result = runner.run_test(baseline=baseline)
    """
    test_name_lower = test_name.lower()
    
    if test_name_lower not in _BASELINE_REGISTRY:
        available = ", ".join(_BASELINE_REGISTRY.keys())
        raise ValueError(
            f"Test baseline '{test_name}' not found. "
            f"Available tests: {available}"
        )
    
    return _BASELINE_REGISTRY[test_name_lower]


def list_baselines() -> list[str]:
    """
    List all available test baseline names.
    
    Returns:
        List of test baseline names
    """
    return list(_BASELINE_REGISTRY.keys())

