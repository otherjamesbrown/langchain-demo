#!/usr/bin/env python3
"""
Baseline schema for test expectations.

This module defines the data structures used to specify expected values
and validation rules for research agent test cases. The baseline system
allows flexible matching strategies including exact, keyword, fuzzy, regex,
and custom validation.

Educational Focus:
- Shows how to define structured test expectations
- Demonstrates different matching strategies for flexible validation
- Enables reusable test definitions across multiple models
"""

from typing import Optional, Dict, Any, List, Union, Callable
from dataclasses import dataclass, field
from enum import Enum


class MatchType(Enum):
    """How to match expected vs actual values.
    
    Educational: Different matching strategies allow for flexible validation:
    - EXACT: For precise values (e.g., founded year = 2013)
    - KEYWORD: For semantic matches (e.g., industry contains "video")
    - FUZZY: For approximate values (e.g., "200-500" ≈ "250-500")
    - REGEX: For pattern matching (e.g., URL validation)
    - CUSTOM: For complex validation logic
    """
    
    EXACT = "exact"           # Must match exactly
    KEYWORD = "keyword"       # Must contain keywords
    FUZZY = "fuzzy"           # Use fuzzy matching (ranges, numbers, etc.)
    REGEX = "regex"           # Match against regex pattern
    CUSTOM = "custom"         # Custom validation function


@dataclass
class FieldExpectation:
    """Expected value for a single field.
    
    Educational: This structure allows us to define flexible validation rules
    for each field. The match_type determines how the actual value is compared
    against the expected value.
    
    Example:
        FieldExpectation(
            field_name="company_size",
            expected_value="51-200 employees",
            match_type=MatchType.FUZZY,
            fuzzy_tolerance=0.3,
            required=True,
            description="Company size should be in 51-200 range (fuzzy match)"
        )
    """
    
    field_name: str
    expected_value: Optional[Union[str, int, List[str]]] = None
    match_type: MatchType = MatchType.EXACT
    required: bool = True
    fuzzy_tolerance: Optional[float] = None  # For numeric fuzzy matching (0.0-1.0)
    keywords: Optional[List[str]] = None  # For keyword matching
    regex_pattern: Optional[str] = None  # For regex matching
    validator_func: Optional[Callable[[Any, Optional[Any]], Union[bool, tuple[bool, Optional[str]]]]] = None  # For custom validation
    description: Optional[str] = None


@dataclass
class TestBaseline:
    """Complete baseline for a test case.
    
    Educational: A test baseline encapsulates all validation rules for a
    single test case (e.g., "BitMovin research"). It separates required
    fields (must pass) from optional fields (nice to have), allowing for
    flexible scoring and comparison.
    
    Example:
        TestBaseline(
            test_name="bitmovin_research",
            company_name="BitMovin",
            description="BitMovin company research baseline",
            required_fields=[...],
            optional_fields=[...],
            metadata={"difficulty": "medium"}
        )
    """
    
    test_name: str
    company_name: str
    description: str
    required_fields: List[FieldExpectation]
    optional_fields: List[FieldExpectation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

