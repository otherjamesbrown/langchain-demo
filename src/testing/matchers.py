#!/usr/bin/env python3
"""
Fuzzy matching engine for field validation.

This module implements the matching logic that compares actual field values
against expected values using various matching strategies. The fuzzy matching
logic handles ranges, numbers, and approximate values intelligently.

Educational Focus:
- Shows how to implement flexible matching algorithms
- Demonstrates fuzzy matching for numeric ranges
- Handles edge cases and type coercion gracefully
"""

from typing import Any, Optional, Tuple, List
import re

from src.testing.baseline import MatchType, FieldExpectation


class FieldMatcher:
    """Matches actual field values against expectations.
    
    Educational: This class implements multiple matching strategies. The key
    insight is that LLM outputs are not always exact - they may vary in format,
    precision, or wording while still being correct. The matcher handles these
    variations intelligently.
    
    Example:
        expectation = FieldExpectation(
            field_name="company_size",
            expected_value="51-200 employees",
            match_type=MatchType.FUZZY,
            fuzzy_tolerance=0.3
        )
        
        matcher = FieldMatcher()
        is_match, confidence, error = matcher.match(expectation, "100-250 employees")
        # Returns: (True, 0.83, None)  # 83% confidence due to range overlap
    """
    
    @staticmethod
    def match(
        expectation: FieldExpectation,
        actual_value: Any,
    ) -> Tuple[bool, float, Optional[str]]:
        """
        Match actual value against expectation.
        
        Educational: Returns a tuple with three values:
        1. is_match: Boolean indicating if the value matches
        2. confidence_score: Float (0.0-1.0) indicating match quality
        3. error_message: Optional description of why match failed
        
        This allows for nuanced scoring where partial matches can contribute
        to overall test scores.
        
        Args:
            expectation: Field expectation with matching rules
            actual_value: The actual value to validate
            
        Returns:
            Tuple of (is_match, confidence_score, error_message)
        """
        
        # Handle None/missing values
        if actual_value is None or (isinstance(actual_value, str) and not actual_value.strip()):
            if expectation.required:
                return False, 0.0, f"Required field '{expectation.field_name}' is missing"
            else:
                return True, 0.0, None  # Optional fields can be None
        
        match_type = expectation.match_type
        
        if match_type == MatchType.EXACT:
            return FieldMatcher._match_exact(expectation, actual_value)
        elif match_type == MatchType.KEYWORD:
            return FieldMatcher._match_keyword(expectation, actual_value)
        elif match_type == MatchType.FUZZY:
            return FieldMatcher._match_fuzzy(expectation, actual_value)
        elif match_type == MatchType.REGEX:
            return FieldMatcher._match_regex(expectation, actual_value)
        elif match_type == MatchType.CUSTOM:
            return FieldMatcher._match_custom(expectation, actual_value)
        else:
            return False, 0.0, f"Unknown match type: {match_type}"
    
    @staticmethod
    def _match_exact(expectation: FieldExpectation, actual: Any) -> Tuple[bool, float, Optional[str]]:
        """Exact match - must be identical.
        
        Educational: For exact matches, we compare values directly. We also
        handle type coercion (e.g., string "2013" matches int 2013) to be
        forgiving of LLM output format variations.
        """
        expected = expectation.expected_value
        
        # Type coercion for common cases
        if expected is not None:
            if isinstance(expected, int) and isinstance(actual, str):
                try:
                    actual = int(actual.strip())
                except (ValueError, AttributeError):
                    pass
            elif isinstance(expected, str) and isinstance(actual, int):
                actual = str(actual)
                expected = str(expected)
        
        if actual == expected:
            return True, 1.0, None
        else:
            return False, 0.0, f"Expected '{expected}', got '{actual}'"
    
    @staticmethod
    def _match_keyword(expectation: FieldExpectation, actual: Any) -> Tuple[bool, float, Optional[str]]:
        """Keyword match - must contain at least one keyword.
        
        Educational: Keyword matching is case-insensitive and checks if any
        of the specified keywords appear in the actual value. Confidence is
        calculated based on how many keywords matched.
        """
        if not expectation.keywords:
            return False, 0.0, "No keywords defined for keyword matching"
        
        actual_str = str(actual).lower()
        matched_keywords = [kw for kw in expectation.keywords if kw.lower() in actual_str]
        
        if matched_keywords:
            # Confidence based on fraction of keywords matched
            confidence = len(matched_keywords) / len(expectation.keywords)
            return True, confidence, None
        else:
            return False, 0.0, f"Expected keywords {expectation.keywords}, none found in '{actual}'"
    
    @staticmethod
    def _match_fuzzy(expectation: FieldExpectation, actual: Any) -> Tuple[bool, float, Optional[str]]:
        """Fuzzy match - handles ranges, numbers, and approximate values.
        
        Educational: Fuzzy matching is the most sophisticated matching type.
        It extracts numbers from strings and compares ranges intelligently.
        This handles cases like "200-500" vs "250-500" by calculating overlap.
        
        Algorithm:
        1. Extract numbers from both expected and actual values
        2. If numbers found, compare ranges with tolerance
        3. If no numbers, fall back to string similarity
        """
        actual_str = str(actual).lower()
        
        # Extract numbers from strings (handles "200-500", "250 to 500", etc.)
        numbers = FieldMatcher._extract_numbers(actual_str)
        
        if not numbers:
            # Fall back to string similarity
            expected_str = str(expectation.expected_value or "").lower()
            similarity = FieldMatcher._string_similarity(expected_str, actual_str)
            tolerance = expectation.fuzzy_tolerance or 0.2
            is_match = similarity >= (1.0 - tolerance)
            return is_match, similarity, None if is_match else f"String similarity too low: {similarity:.2f}"
        
        # Extract expected numbers
        expected_str = str(expectation.expected_value or "").lower()
        expected_numbers = FieldMatcher._extract_numbers(expected_str)
        
        if not expected_numbers:
            return False, 0.0, "Could not extract numbers from expected value"
        
        # Match number ranges (e.g., "51-200" vs "100-250")
        tolerance = expectation.fuzzy_tolerance or 0.3
        
        # Calculate range boundaries
        expected_min = min(expected_numbers)
        expected_max = max(expected_numbers)
        expected_range = expected_max - expected_min
        tolerance_amount = expected_range * tolerance
        
        actual_min = min(numbers)
        actual_max = max(numbers)
        
        # Check if ranges overlap (with tolerance)
        ranges_overlap = not (actual_max < expected_min - tolerance_amount or 
                             actual_min > expected_max + tolerance_amount)
        
        if ranges_overlap:
            # Calculate confidence based on overlap percentage
            overlap_min = max(actual_min, expected_min - tolerance_amount)
            overlap_max = min(actual_max, expected_max + tolerance_amount)
            overlap_range = max(0, overlap_max - overlap_min)
            
            # Use the larger range as the denominator for confidence calculation
            total_range = max(actual_max - actual_min, expected_max - expected_min)
            confidence = overlap_range / total_range if total_range > 0 else 1.0
            
            return True, confidence, None
        else:
            return False, 0.0, (
                f"Number range mismatch: expected {expected_min}-{expected_max}, "
                f"got {actual_min}-{actual_max}"
            )
    
    @staticmethod
    def _extract_numbers(text: str) -> List[int]:
        """Extract all integers from text.
        
        Educational: This regex-based extraction handles various formats:
        - "51-200 employees" → [51, 200]
        - "250 to 500" → [250, 500]
        - "1000" → [1000]
        """
        return [int(match) for match in re.findall(r'\d+', text)]
    
    @staticmethod
    def _string_similarity(str1: str, str2: str) -> float:
        """Calculate simple string similarity (0.0 to 1.0).
        
        Educational: Uses Jaccard similarity on character bigrams. This is
        a simple but effective way to measure string similarity without
        external libraries. More sophisticated algorithms (e.g., Levenshtein)
        could be used for better accuracy.
        """
        if not str1 or not str2:
            return 0.0
        
        # Simple Jaccard similarity on character bigrams
        bigrams1 = set(zip(str1, str1[1:]))
        bigrams2 = set(zip(str2, str2[1:]))
        
        intersection = len(bigrams1 & bigrams2)
        union = len(bigrams1 | bigrams2)
        
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def _match_regex(expectation: FieldExpectation, actual: Any) -> Tuple[bool, float, Optional[str]]:
        """Regex match - validates against regex pattern.
        
        Educational: Regex matching is useful for structured formats like
        URLs, dates, or phone numbers. The pattern must be defined in the
        expectation.
        """
        if not expectation.regex_pattern:
            return False, 0.0, "No regex pattern defined"
        
        actual_str = str(actual)
        match = re.search(expectation.regex_pattern, actual_str, re.IGNORECASE)
        
        if match:
            return True, 1.0, None
        else:
            return False, 0.0, f"Regex '{expectation.regex_pattern}' did not match '{actual_str}'"
    
    @staticmethod
    def _match_custom(expectation: FieldExpectation, actual: Any) -> Tuple[bool, float, Optional[str]]:
        """Custom validator function match.
        
        Educational: Custom validators allow for complex validation logic
        that doesn't fit into standard matching types. The validator function
        receives the actual value and expected value, and returns either:
        - A boolean (pass/fail)
        - A tuple of (bool, error_message)
        """
        if not expectation.validator_func:
            return False, 0.0, "No validator function defined"
        
        try:
            result = expectation.validator_func(actual, expectation.expected_value)
            if isinstance(result, bool):
                return result, 1.0 if result else 0.0, None
            elif isinstance(result, tuple) and len(result) == 2:
                is_match, error_msg = result
                return is_match, 1.0 if is_match else 0.0, error_msg
            else:
                return False, 0.0, "Validator function returned invalid result"
        except Exception as e:
            return False, 0.0, f"Validator function error: {e}"

