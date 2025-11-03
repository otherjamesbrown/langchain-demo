# Comprehensive Testing Framework Plan

## Overview

This document outlines a comprehensive plan for building a robust testing framework that:
- Runs identical tests across multiple models (local, OpenAI, Anthropic, Gemini)
- Compares model outputs against baseline expectations
- Uses fuzzy matching logic for flexible validation
- Supports both automated CLI execution and interactive UI execution
- Provides clear, actionable comparison results

---

## Goals

1. **Consistency**: Same test inputs across all models
2. **Comparability**: Side-by-side comparison of outputs
3. **Flexibility**: Fuzzy matching for approximate values (e.g., "200-500" ≈ "250-500")
4. **Automation**: Can run via CLI/scripts without UI
5. **Visibility**: Rich UI display of results with visual comparisons
6. **Maintainability**: Easy to add new test cases and baselines

---

## Current State Analysis

### Existing Components

✅ **Test Infrastructure**:
- `scripts/test_bitmovin_research.py` - Standalone test script
- `tests/test_bitmovin_research.py` - Pytest-based tests
- `src/ui/pages/4_🧪_Test_BitMovin.py` - Streamlit UI page

✅ **Validation Logic**:
- `validate_required_fields()` - Hard-coded validation in test scripts
- Basic exact matching for some fields (e.g., `founded == 2013`)
- Simple keyword matching for others (e.g., `"video" in industry.lower()`)

❌ **Missing Components**:
- Baseline/expected value definitions
- Fuzzy matching logic for ranges/approximations
- Comparison engine for cross-model results
- Unified test execution framework
- Automated test runner
- Rich UI comparison views

---

## Architecture Design

### 1. Test Case Definition

#### 1.1 Baseline Schema

```python
# src/testing/baseline.py

from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass
from enum import Enum

class MatchType(Enum):
    """How to match expected vs actual values."""
    EXACT = "exact"           # Must match exactly
    KEYWORD = "keyword"       # Must contain keywords
    FUZZY = "fuzzy"           # Use fuzzy matching (ranges, numbers, etc.)
    REGEX = "regex"           # Match against regex pattern
    CUSTOM = "custom"         # Custom validation function

@dataclass
class FieldExpectation:
    """Expected value for a single field."""
    field_name: str
    expected_value: Optional[Union[str, int, List[str]]] = None
    match_type: MatchType = MatchType.EXACT
    required: bool = True
    fuzzy_tolerance: Optional[float] = None  # For numeric fuzzy matching
    keywords: Optional[List[str]] = None  # For keyword matching
    regex_pattern: Optional[str] = None  # For regex matching
    validator_func: Optional[callable] = None  # For custom validation
    description: Optional[str] = None

@dataclass
class TestBaseline:
    """Complete baseline for a test case."""
    test_name: str
    company_name: str
    description: str
    required_fields: List[FieldExpectation]
    optional_fields: List[FieldExpectation]
    metadata: Dict[str, Any] = None
```

#### 1.2 Example Baseline Definitions

```python
# src/testing/baselines/bitmovin.py

from src.testing.baseline import TestBaseline, FieldExpectation, MatchType

BITMOVIN_BASELINE = TestBaseline(
    test_name="bitmovin_research",
    company_name="BitMovin",
    description="BitMovin company research baseline - video streaming infrastructure",
    
    required_fields=[
        FieldExpectation(
            field_name="company_name",
            expected_value="Bitmovin",
            match_type=MatchType.KEYWORD,
            keywords=["bitmovin"],
            required=True,
            description="Company name should contain 'bitmovin' (case-insensitive)"
        ),
        FieldExpectation(
            field_name="industry",
            expected_value="Video Technology / SaaS",
            match_type=MatchType.KEYWORD,
            keywords=["video", "streaming"],
            required=True,
            description="Industry should relate to video/streaming"
        ),
        FieldExpectation(
            field_name="company_size",
            expected_value="51-200 employees",
            match_type=MatchType.FUZZY,
            fuzzy_tolerance=0.3,  # Allow ±30% variation
            required=True,
            description="Company size should be in 51-200 range (fuzzy match)"
        ),
        FieldExpectation(
            field_name="headquarters",
            expected_value="San Francisco, California",
            match_type=MatchType.KEYWORD,
            keywords=["san francisco", "california", "sf"],
            required=True,
            description="Headquarters should be in San Francisco area"
        ),
        FieldExpectation(
            field_name="founded",
            expected_value=2013,
            match_type=MatchType.EXACT,
            required=True,
            description="Founded year must be exactly 2013"
        ),
    ],
    
    optional_fields=[
        FieldExpectation(
            field_name="growth_stage",
            expected_value=None,
            match_type=MatchType.KEYWORD,
            keywords=["scale-up", "scaleup", "startup", "mature"],
            required=False,
            description="Growth stage classification"
        ),
        # ... more optional fields
    ],
    
    metadata={
        "company_type": "SaaS",
        "domain": "video_technology",
        "difficulty": "medium"
    }
)
```

### 2. Fuzzy Matching Engine

#### 2.1 Matching Functions

```python
# src/testing/matchers.py

from typing import Any, Optional, Tuple
from src.testing.baseline import MatchType, FieldExpectation
import re

class FieldMatcher:
    """Matches actual field values against expectations."""
    
    @staticmethod
    def match(
        expectation: FieldExpectation,
        actual_value: Any,
    ) -> Tuple[bool, float, Optional[str]]:
        """
        Match actual value against expectation.
        
        Returns:
            (is_match, confidence_score, error_message)
            - is_match: True if value matches expectation
            - confidence_score: 0.0-1.0 indicating match quality
            - error_message: Description of why match failed (if applicable)
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
        """Exact match - must be identical."""
        expected = expectation.expected_value
        
        if actual == expected:
            return True, 1.0, None
        else:
            return False, 0.0, f"Expected '{expected}', got '{actual}'"
    
    @staticmethod
    def _match_keyword(expectation: FieldExpectation, actual: Any) -> Tuple[bool, float, Optional[str]]:
        """Keyword match - must contain at least one keyword."""
        if not expectation.keywords:
            return False, 0.0, "No keywords defined for keyword matching"
        
        actual_str = str(actual).lower()
        matched_keywords = [kw for kw in expectation.keywords if kw.lower() in actual_str]
        
        if matched_keywords:
            confidence = len(matched_keywords) / len(expectation.keywords)
            return True, confidence, None
        else:
            return False, 0.0, f"Expected keywords {expectation.keywords}, none found in '{actual}'"
    
    @staticmethod
    def _match_fuzzy(expectation: FieldExpectation, actual: Any) -> Tuple[bool, float, Optional[str]]:
        """Fuzzy match - handles ranges, numbers, and approximate values."""
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
        
        # Check if any actual numbers fall within expected range (with tolerance)
        expected_min = min(expected_numbers)
        expected_max = max(expected_numbers)
        expected_range = expected_max - expected_min
        tolerance_amount = expected_range * tolerance
        
        actual_min = min(numbers)
        actual_max = max(numbers)
        
        # Check overlap
        ranges_overlap = not (actual_max < expected_min - tolerance_amount or 
                             actual_min > expected_max + tolerance_amount)
        
        if ranges_overlap:
            # Calculate confidence based on overlap percentage
            overlap_min = max(actual_min, expected_min - tolerance_amount)
            overlap_max = min(actual_max, expected_max + tolerance_amount)
            overlap_range = max(0, overlap_max - overlap_min)
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
        """Extract all integers from text."""
        return [int(match) for match in re.findall(r'\d+', text)]
    
    @staticmethod
    def _string_similarity(str1: str, str2: str) -> float:
        """Calculate simple string similarity (0.0 to 1.0)."""
        # Simple Jaccard similarity on character bigrams
        if not str1 or not str2:
            return 0.0
        
        bigrams1 = set(zip(str1, str1[1:]))
        bigrams2 = set(zip(str2, str2[1:]))
        
        intersection = len(bigrams1 & bigrams2)
        union = len(bigrams1 | bigrams2)
        
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def _match_regex(expectation: FieldExpectation, actual: Any) -> Tuple[bool, float, Optional[str]]:
        """Regex match."""
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
        """Custom validator function match."""
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
```

### 3. Test Execution Engine

#### 3.1 Unified Test Runner

```python
# src/testing/test_runner.py

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from src.agent.research_agent import ResearchAgent, ResearchAgentResult
from src.testing.baseline import TestBaseline
from src.testing.matchers import FieldMatcher
from src.tools.models import CompanyInfo

@dataclass
class FieldMatchResult:
    """Result of matching a single field."""
    field_name: str
    is_match: bool
    confidence: float
    expected_value: Any
    actual_value: Any
    error_message: Optional[str]
    match_type: str

@dataclass
class ModelTestResult:
    """Test results for a single model."""
    model_name: str
    model_provider: str
    success: bool
    execution_time: float
    iterations: int
    field_results: Dict[str, FieldMatchResult]
    required_fields_score: float  # 0.0-1.0
    optional_fields_score: float  # 0.0-1.0
    overall_score: float  # 0.0-1.0
    company_info: Optional[CompanyInfo]
    raw_output: str
    error_message: Optional[str]

@dataclass
class TestExecutionResult:
    """Complete test execution across all models."""
    test_name: str
    baseline: TestBaseline
    model_results: List[ModelTestResult]
    execution_time: float
    best_model: Optional[str]  # Model with highest overall_score
    average_score: float

class TestRunner:
    """Runs tests across multiple models and compares results."""
    
    def __init__(self, model_configs: List[Dict[str, Any]]):
        """
        Initialize test runner with model configurations.
        
        Args:
            model_configs: List of model config dicts with keys:
                - name: Model name
                - provider: Model provider (local, openai, anthropic, gemini)
                - model_path: Path for local models (optional)
                - api_identifier: API model identifier for remote models (optional)
        """
        self.model_configs = model_configs
        self.matcher = FieldMatcher()
    
    def run_test(
        self,
        baseline: TestBaseline,
        max_iterations: int = 10,
        verbose: bool = False,
    ) -> TestExecutionResult:
        """
        Run a test case across all configured models.
        
        Args:
            baseline: Test baseline with expectations
            max_iterations: Maximum agent iterations
            verbose: Enable verbose logging
        
        Returns:
            TestExecutionResult with results for all models
        """
        import time
        start_time = time.time()
        
        model_results = []
        
        for model_config in self.model_configs:
            model_result = self._run_single_model_test(
                model_config=model_config,
                baseline=baseline,
                max_iterations=max_iterations,
                verbose=verbose,
            )
            model_results.append(model_result)
        
        execution_time = time.time() - start_time
        
        # Calculate aggregate metrics
        if model_results:
            average_score = sum(r.overall_score for r in model_results) / len(model_results)
            best_model = max(model_results, key=lambda r: r.overall_score)
            best_model_name = best_model.model_name
        else:
            average_score = 0.0
            best_model_name = None
        
        return TestExecutionResult(
            test_name=baseline.test_name,
            baseline=baseline,
            model_results=model_results,
            execution_time=execution_time,
            best_model=best_model_name,
            average_score=average_score,
        )
    
    def _run_single_model_test(
        self,
        model_config: Dict[str, Any],
        baseline: TestBaseline,
        max_iterations: int,
        verbose: bool,
    ) -> ModelTestResult:
        """Run test for a single model."""
        model_name = model_config["name"]
        model_provider = model_config["provider"]
        
        try:
            # Initialize agent
            agent_kwargs = {
                "model_type": model_provider,
                "verbose": verbose,
                "max_iterations": max_iterations,
            }
            
            if model_provider == "local":
                if model_config.get("model_path"):
                    agent_kwargs["model_path"] = model_config["model_path"]
                if model_config.get("model_key"):
                    agent_kwargs["local_model"] = model_config["model_key"]
            else:
                if model_config.get("api_identifier"):
                    agent_kwargs["model_kwargs"] = {
                        "model_name": model_config["api_identifier"]
                    }
            
            agent = ResearchAgent(**agent_kwargs)
            
            # Execute research
            import time
            start_time = time.time()
            result: ResearchAgentResult = agent.research_company(baseline.company_name)
            execution_time = time.time() - start_time
            
            # Validate results
            field_results = self._validate_result(
                result=result,
                baseline=baseline,
            )
            
            # Calculate scores
            required_matches = [
                fr for field_name, fr in field_results.items()
                if any(exp.field_name == field_name and exp.required 
                      for exp in baseline.required_fields)
            ]
            optional_matches = [
                fr for field_name, fr in field_results.items()
                if not any(exp.field_name == field_name and exp.required 
                          for exp in baseline.required_fields)
            ]
            
            required_score = (
                sum(fr.confidence for fr in required_matches) / len(baseline.required_fields)
                if baseline.required_fields else 1.0
            )
            optional_score = (
                sum(fr.confidence for fr in optional_matches) / len(baseline.optional_fields)
                if baseline.optional_fields and optional_matches else 0.0
            )
            
            # Overall score: 70% required, 30% optional
            overall_score = (required_score * 0.7) + (optional_score * 0.3)
            
            success = result.success and result.company_info is not None
            
            return ModelTestResult(
                model_name=model_name,
                model_provider=model_provider,
                success=success,
                execution_time=execution_time,
                iterations=result.iterations,
                field_results=field_results,
                required_fields_score=required_score,
                optional_fields_score=optional_score,
                overall_score=overall_score,
                company_info=result.company_info,
                raw_output=result.raw_output or "",
                error_message=None,
            )
            
        except Exception as e:
            return ModelTestResult(
                model_name=model_name,
                model_provider=model_provider,
                success=False,
                execution_time=0.0,
                iterations=0,
                field_results={},
                required_fields_score=0.0,
                optional_fields_score=0.0,
                overall_score=0.0,
                company_info=None,
                raw_output="",
                error_message=str(e),
            )
    
    def _validate_result(
        self,
        result: ResearchAgentResult,
        baseline: TestBaseline,
    ) -> Dict[str, FieldMatchResult]:
        """Validate result against baseline expectations."""
        field_results = {}
        
        company_info = result.company_info
        if not company_info:
            # All fields fail if no company_info
            for exp in baseline.required_fields + baseline.optional_fields:
                field_results[exp.field_name] = FieldMatchResult(
                    field_name=exp.field_name,
                    is_match=False,
                    confidence=0.0,
                    expected_value=exp.expected_value,
                    actual_value=None,
                    error_message="No company_info returned",
                    match_type=exp.match_type.value,
                )
            return field_results
        
        # Validate each expected field
        all_expectations = baseline.required_fields + baseline.optional_fields
        
        for expectation in all_expectations:
            actual_value = getattr(company_info, expectation.field_name, None)
            
            is_match, confidence, error_msg = self.matcher.match(expectation, actual_value)
            
            field_results[expectation.field_name] = FieldMatchResult(
                field_name=expectation.field_name,
                is_match=is_match,
                confidence=confidence,
                expected_value=expectation.expected_value,
                actual_value=actual_value,
                error_message=error_msg,
                match_type=expectation.match_type.value,
            )
        
        return field_results
```

### 4. CLI Test Runner

```python
# scripts/run_test_framework.py

#!/usr/bin/env python3
"""
Unified test framework CLI runner.

Usage:
    python scripts/run_test_framework.py --test bitmovin
    python scripts/run_test_framework.py --test bitmovin --models gemini openai
    python scripts/run_test_framework.py --test bitmovin --output json
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
import json
from typing import List, Dict, Any

from src.testing.test_runner import TestRunner
from src.testing.baselines import get_baseline
from src.database.operations import get_model_configurations
from src.database.schema import get_session, create_database

def get_available_models(
    provider_filter: List[str] = None
) -> List[Dict[str, Any]]:
    """Get available model configurations."""
    create_database()
    session = get_session()
    try:
        configs = get_model_configurations(session=session)
        models = []
        
        for config in configs:
            if provider_filter and config.provider not in provider_filter:
                continue
            
            model_dict = {
                "name": config.name,
                "provider": config.provider,
                "config_id": config.id,
            }
            
            if config.provider == "local":
                model_dict["model_path"] = config.model_path
                model_dict["model_key"] = config.model_key
            else:
                model_dict["api_identifier"] = config.api_identifier
            
            models.append(model_dict)
        
        return models
    finally:
        session.close()

def format_results(result, output_format: str = "text"):
    """Format test results for display."""
    if output_format == "json":
        return json.dumps({
            "test_name": result.test_name,
            "average_score": result.average_score,
            "best_model": result.best_model,
            "execution_time": result.execution_time,
            "model_results": [
                {
                    "model_name": mr.model_name,
                    "provider": mr.model_provider,
                    "success": mr.success,
                    "overall_score": mr.overall_score,
                    "required_fields_score": mr.required_fields_score,
                    "optional_fields_score": mr.optional_fields_score,
                    "execution_time": mr.execution_time,
                    "iterations": mr.iterations,
                }
                for mr in result.model_results
            ]
        }, indent=2)
    else:
        # Text output
        lines = [
            f"Test: {result.test_name}",
            f"Average Score: {result.average_score:.2%}",
            f"Best Model: {result.best_model}",
            f"Execution Time: {result.execution_time:.2f}s",
            "",
            "Model Results:",
        ]
        
        for mr in result.model_results:
            lines.extend([
                f"  {mr.model_name} ({mr.model_provider}):",
                f"    Success: {'✅' if mr.success else '❌'}",
                f"    Overall Score: {mr.overall_score:.2%}",
                f"    Required Fields: {mr.required_fields_score:.2%}",
                f"    Optional Fields: {mr.optional_fields_score:.2%}",
                f"    Execution Time: {mr.execution_time:.2f}s",
                f"    Iterations: {mr.iterations}",
            ])
        
        return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Run test framework")
    parser.add_argument(
        "--test",
        required=True,
        help="Test name (e.g., 'bitmovin')"
    )
    parser.add_argument(
        "--models",
        nargs="+",
        help="Filter to specific model providers (e.g., gemini openai)"
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=10,
        help="Maximum agent iterations"
    )
    
    args = parser.parse_args()
    
    # Get baseline
    try:
        baseline = get_baseline(args.test)
    except Exception as e:
        print(f"Error loading baseline: {e}")
        return 1
    
    # Get available models
    models = get_available_models(provider_filter=args.models)
    
    if not models:
        print("No models available for testing")
        return 1
    
    print(f"Running test '{args.test}' across {len(models)} model(s)...")
    
    # Run test
    runner = TestRunner(model_configs=models)
    result = runner.run_test(
        baseline=baseline,
        max_iterations=args.max_iterations,
    )
    
    # Output results
    print(format_results(result, args.output))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### 5. UI Integration

#### 5.1 Enhanced Test_BitMovin Page

The existing Test_BitMovin page will be enhanced to:
1. Use the unified TestRunner
2. Display comparison tables with confidence scores
3. Show fuzzy match details
4. Visual indicators for match quality
5. Export results capability

#### 5.2 New Comparison View

Add a new section showing:
- Side-by-side field comparison with confidence scores
- Match type indicators (exact, keyword, fuzzy, etc.)
- Visual scoring bars
- Detailed match explanations

---

## Implementation Plan

### Phase 1: Core Framework (Week 1)

**Tasks:**
1. ✅ Create baseline schema and dataclasses (`src/testing/baseline.py`)
2. ✅ Implement fuzzy matching engine (`src/testing/matchers.py`)
3. ✅ Create test runner (`src/testing/test_runner.py`)
4. ✅ Create baseline registry (`src/testing/baselines/__init__.py`)

**Deliverables:**
- Working fuzzy matching for ranges (e.g., "200-500" ≈ "250-500")
- Test runner that executes tests across multiple models
- Basic baseline definitions

### Phase 2: Baseline Definitions (Week 1-2)

**Tasks:**
1. Convert existing BitMovin validation to baseline format
2. Define fuzzy matching rules for all fields
3. Add baseline for additional test cases (optional)

**Deliverables:**
- Complete BitMovin baseline with fuzzy matching
- Documentation of matching rules

### Phase 3: CLI Integration (Week 2)

**Tasks:**
1. Create unified CLI script (`scripts/run_test_framework.py`)
2. Add JSON output format
3. Add filtering options
4. Test automated execution

**Deliverables:**
- Working CLI that can run tests automatically
- Scripts can be run from CI/CD

### Phase 4: UI Enhancement (Week 2-3)

**Tasks:**
1. Refactor Test_BitMovin page to use TestRunner
2. Add comparison table with confidence scores
3. Add fuzzy match details view
4. Add visual scoring indicators
5. Add export functionality

**Deliverables:**
- Enhanced UI with rich comparison views
- Visual indicators for match quality
- Export results to JSON/CSV

### Phase 5: Testing & Documentation (Week 3)

**Tasks:**
1. Test all matching scenarios
2. Document fuzzy matching logic
3. Create usage examples
4. Update existing documentation

**Deliverables:**
- Comprehensive tests
- User documentation
- Developer documentation

---

## Fuzzy Matching Logic Details

### Employee Range Matching

**Example**: "200-500 employees" vs "250-500 employees"

**Algorithm:**
1. Extract numbers: `[200, 500]` vs `[250, 500]`
2. Calculate ranges: `200-500` (range=300) vs `250-500` (range=250)
3. Apply tolerance (default 30%): `300 * 0.3 = 90`
4. Check overlap:
   - Expected: `200-90` to `500+90` = `110-590`
   - Actual: `250-500`
   - Overlap: `250-500` (overlap range = 250)
5. Confidence = `overlap_range / max(range1, range2)` = `250/300 = 0.83`

**Result**: ✅ Match with 83% confidence

### Keyword Matching

**Example**: Industry field

**Rule**: Must contain at least one keyword from `["video", "streaming"]`

**Examples:**
- "Video Technology" → ✅ Match (contains "video")
- "Streaming Platform" → ✅ Match (contains "streaming")
- "Software Company" → ❌ No match
- "Video Streaming Infrastructure" → ✅ Match (contains both, higher confidence)

### Exact Matching

**Example**: Founded year

**Rule**: Must match exactly

**Examples:**
- Expected: `2013`, Actual: `2013` → ✅ Match (100% confidence)
- Expected: `2013`, Actual: `2014` → ❌ No match
- Expected: `2013`, Actual: `"2013"` → ✅ Match (type coercion)

### Regex Matching

**Example**: Website URL validation

**Pattern**: `^https?://(www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$`

**Examples:**
- `https://bitmovin.com` → ✅ Match
- `http://www.bitmovin.com` → ✅ Match
- `bitmovin.com` → ❌ No match (missing protocol)

---

## File Structure

```
src/testing/
├── __init__.py
├── baseline.py              # Baseline schema and dataclasses
├── matchers.py              # Fuzzy matching engine
├── test_runner.py           # Unified test execution
└── baselines/
    ├── __init__.py          # Baseline registry
    ├── bitmovin.py          # BitMovin baseline definition
    └── ...

scripts/
├── run_test_framework.py    # CLI test runner
└── test_bitmovin_research.py  # Legacy script (can be deprecated)

src/ui/pages/
└── 4_🧪_Test_BitMovin.py    # Enhanced UI page

tests/
└── testing/
    ├── test_matchers.py     # Unit tests for matching logic
    ├── test_runner.py       # Integration tests
    └── test_baselines.py    # Baseline validation tests
```

---

## Usage Examples

### CLI Usage

```bash
# Run BitMovin test across all models
python scripts/run_test_framework.py --test bitmovin

# Run only Gemini and OpenAI
python scripts/run_test_framework.py --test bitmovin --models gemini openai

# Output as JSON for programmatic use
python scripts/run_test_framework.py --test bitmovin --output json

# Custom max iterations
python scripts/run_test_framework.py --test bitmovin --max-iterations 15
```

### Programmatic Usage

```python
from src.testing.test_runner import TestRunner
from src.testing.baselines import get_baseline

# Get baseline
baseline = get_baseline("bitmovin")

# Configure models
models = [
    {"name": "Gemini Flash", "provider": "gemini", "api_identifier": "gemini-flash-latest"},
    {"name": "GPT-4", "provider": "openai", "api_identifier": "gpt-4"},
    {"name": "Claude 3", "provider": "anthropic", "api_identifier": "claude-3-opus"},
]

# Run test
runner = TestRunner(model_configs=models)
result = runner.run_test(baseline=baseline)

# Access results
print(f"Best model: {result.best_model}")
for mr in result.model_results:
    print(f"{mr.model_name}: {mr.overall_score:.2%}")
```

### UI Usage

1. Navigate to Test_BitMovin page
2. Select models to test (checkboxes)
3. Click "Run Tests"
4. View:
   - Comparison table with scores
   - Field-by-field match details
   - Confidence indicators
   - Export options

---

## Success Metrics

1. **Accuracy**: Fuzzy matching correctly identifies "200-500" ≈ "250-500" with >80% confidence
2. **Consistency**: Same test produces consistent results across runs
3. **Performance**: Test completes across 3 models in <5 minutes
4. **Usability**: UI clearly shows what passed/failed and why
5. **Maintainability**: Adding new test cases takes <30 minutes

---

## Open Questions

1. **Baseline Storage**: Should baselines be stored in:
   - Python files (current plan) ✅
   - JSON/YAML files (easier to edit)
   - Database (centralized, but harder to version)

2. **Confidence Thresholds**: What confidence score counts as "pass"?
   - Required fields: ≥0.8?
   - Optional fields: ≥0.6?

3. **Multiple Test Cases**: Should framework support:
   - Single company, multiple baselines?
   - Multiple companies in one test run?
   - Regression testing (compare against previous runs)?

4. **CI/CD Integration**: 
   - Run tests automatically on commits?
   - Compare against previous results?
   - Alert on score degradation?

---

## Next Steps

1. **Review this plan** - Ensure it meets requirements
2. **Clarify open questions** - Decide on storage, thresholds, etc.
3. **Begin Phase 1** - Start implementing core framework
4. **Iterate** - Build incrementally, test as we go

---

**Status**: 📋 **PLAN - READY FOR IMPLEMENTATION**  
**Last Updated**: 2025-01-XX  
**Owner**: TBD

