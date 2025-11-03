#!/usr/bin/env python3
"""
Unified test execution engine for research agent validation.

This module provides the core test runner that executes research agent tests
across multiple models and compares results against baselines. It handles
model initialization, test execution, validation, and scoring.

Educational Focus:
- Shows how to build a unified testing framework
- Demonstrates cross-model comparison patterns
- Implements confidence-based scoring for flexible validation
"""

import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from src.agent.research_agent import ResearchAgent, ResearchAgentResult
from src.testing.baseline import TestBaseline
from src.testing.matchers import FieldMatcher
from src.tools.models import CompanyInfo


@dataclass
class FieldMatchResult:
    """Result of matching a single field.
    
    Educational: This structure captures all the details of a field validation,
    allowing for detailed analysis and reporting of what passed/failed and why.
    """
    
    field_name: str
    is_match: bool
    confidence: float  # 0.0-1.0
    expected_value: Any
    actual_value: Any
    error_message: Optional[str] = None
    match_type: str = ""


@dataclass
class ModelTestResult:
    """Test results for a single model.
    
    Educational: This aggregates all validation results for one model execution.
    It includes both detailed field-by-field results and aggregate scores for
    quick comparison across models.
    """
    
    model_name: str
    model_provider: str
    success: bool
    execution_time: float
    iterations: int
    field_results: Dict[str, FieldMatchResult] = field(default_factory=dict)
    required_fields_score: float = 0.0  # 0.0-1.0
    optional_fields_score: float = 0.0  # 0.0-1.0
    overall_score: float = 0.0  # 0.0-1.0
    company_info: Optional[CompanyInfo] = None
    raw_output: str = ""
    error_message: Optional[str] = None


@dataclass
class TestExecutionResult:
    """Complete test execution across all models.
    
    Educational: This is the top-level result structure that contains results
    for all models tested. It includes aggregate metrics for easy comparison
    and identifies the best-performing model.
    """
    
    test_name: str
    baseline: TestBaseline
    model_results: List[ModelTestResult] = field(default_factory=list)
    execution_time: float = 0.0
    best_model: Optional[str] = None  # Model with highest overall_score
    average_score: float = 0.0


class TestRunner:
    """Runs tests across multiple models and compares results.
    
    Educational: The TestRunner is the main entry point for executing tests.
    It handles:
    1. Model initialization based on configuration
    2. Test execution via ResearchAgent
    3. Validation against baseline expectations
    4. Score calculation and aggregation
    
    Example:
        models = [
            {"name": "Gemini Flash", "provider": "gemini", "api_identifier": "gemini-flash-latest"},
            {"name": "GPT-4", "provider": "openai", "api_identifier": "gpt-4"},
        ]
        
        runner = TestRunner(model_configs=models)
        result = runner.run_test(baseline=baseline)
        
        print(f"Best model: {result.best_model}")
        for mr in result.model_results:
            print(f"{mr.model_name}: {mr.overall_score:.2%}")
    """
    
    def __init__(self, model_configs: List[Dict[str, Any]]):
        """
        Initialize test runner with model configurations.
        
        Educational: Model configs should include all information needed to
        initialize a ResearchAgent. The runner handles different provider types
        (local vs remote) and passes appropriate parameters.
        
        Args:
            model_configs: List of model config dicts with keys:
                - name: Model name (display name)
                - provider: Model provider (local, openai, anthropic, gemini)
                - model_path: Path for local models (optional)
                - model_key: Model key for local models (optional)
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
        
        Educational: This method orchestrates the entire test execution:
        1. Iterates through each model configuration
        2. Runs the research agent for the baseline company
        3. Validates results against baseline expectations
        4. Calculates scores and aggregates results
        
        Args:
            baseline: Test baseline with expectations
            max_iterations: Maximum agent iterations
            verbose: Enable verbose logging
            
        Returns:
            TestExecutionResult with results for all models
        """
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
            best_model_result = max(model_results, key=lambda r: r.overall_score)
            best_model_name = best_model_result.model_name
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
        """Run test for a single model.
        
        Educational: This method handles model-specific initialization and
        error handling. Different providers require different parameters,
        and the runner adapts accordingly.
        """
        model_name = model_config["name"]
        model_provider = model_config["provider"]
        
        try:
            # Initialize agent with model-specific configuration
            agent_kwargs = {
                "model_type": model_provider,
                "verbose": verbose,
                "max_iterations": max_iterations,
            }
            
            # Configure based on provider type
            if model_provider == "local":
                if model_config.get("model_path"):
                    agent_kwargs["model_path"] = model_config["model_path"]
                if model_config.get("model_key"):
                    agent_kwargs["local_model"] = model_config["model_key"]
            else:
                # For remote models, pass API identifier if provided
                if model_config.get("api_identifier"):
                    agent_kwargs["model_kwargs"] = {
                        "model_name": model_config["api_identifier"]
                    }
            
            agent = ResearchAgent(**agent_kwargs)
            
            # Execute research
            result: ResearchAgentResult = agent.research_company(baseline.company_name)
            execution_time = result.execution_time_seconds
            
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
            
            # Required fields score: average confidence of required fields
            if baseline.required_fields:
                required_score = (
                    sum(fr.confidence for fr in required_matches) / len(baseline.required_fields)
                )
            else:
                required_score = 1.0
            
            # Optional fields score: average confidence if any optional fields present
            if baseline.optional_fields and optional_matches:
                optional_score = (
                    sum(fr.confidence for fr in optional_matches) / len(baseline.optional_fields)
                )
            else:
                optional_score = 0.0
            
            # Overall score: 70% required, 30% optional (weighted)
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
        """Validate result against baseline expectations.
        
        Educational: This method iterates through all expected fields (both
        required and optional) and uses the FieldMatcher to validate each one.
        It returns a dictionary of field results for detailed analysis.
        """
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

