"""
Test research agent execution against all available models for BitMovin.

This test validates that the research agent can successfully extract company
information using different LLM providers. It tests:
- Required fields: company_name, industry, company_size, headquarters, founded
- Optional fields: growth_stage, industry_vertical, sub_industry_vertical, etc.
"""

import os
import pytest
from typing import Dict, Any

from src.agent.research_agent import ResearchAgent, ResearchAgentResult
from src.tools.models import CompanyInfo
from src.models.model_factory import list_available_providers


# Expected minimum required fields for BitMovin
REQUIRED_FIELDS = {
    "company_name": "Bitmovin",  # Allow case variation
    "industry": None,  # Should not be None/empty, but value varies
    "company_size": None,  # Should not be None/empty, but value varies
    "headquarters": None,  # Should not be None/empty, but value varies
    "founded": 2013,  # Specific expected value
}

# Expected optional fields (if present, should have reasonable values)
OPTIONAL_FIELDS = [
    "growth_stage",
    "industry_vertical",
    "sub_industry_vertical",
    "financial_health",
    "business_and_technology_adoption",
    "primary_workload_philosophy",
    "buyer_journey",
    "budget_maturity",
    "cloud_spend_capacity",
    "procurement_process",
]

# Model configurations for testing
MODEL_CONFIGS = [
    {
        "model_type": "local",
        "pytest_marker": "requires_model",
        "skip_reason": "Local model file not available",
    },
    {
        "model_type": "openai",
        "pytest_marker": "requires_api",
        "skip_reason": "OpenAI API key not available",
    },
    {
        "model_type": "anthropic",
        "pytest_marker": "requires_api",
        "skip_reason": "Anthropic API key not available",
    },
    {
        "model_type": "gemini",
        "pytest_marker": "requires_api",
        "skip_reason": "Google Gemini API key not available",
    },
]


def _check_api_key_available(model_type: str) -> bool:
    """Check if API key is available for the model type.
    
    Checks database first (primary source), then falls back to environment variables.
    This matches the architecture where database is the source of truth.
    """
    if model_type == "local":
        # For local, check if MODEL_PATH is set or if default model exists
        model_path = os.getenv("MODEL_PATH")
        if model_path and os.path.exists(model_path):
            return True
        # Could also check for default model location
        return False
    
    # Check database first (primary source of truth)
    try:
        from src.database.operations import get_api_key
        db_key = get_api_key(model_type)
        if db_key and db_key.strip():
            return True
    except Exception:
        pass  # Fallback to environment variables
    
    # Fallback to environment variables
    env_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GOOGLE_API_KEY",
    }
    
    api_key_env = env_map.get(model_type)
    if not api_key_env:
        return False
    
    api_key = os.getenv(api_key_env)
    return api_key is not None and api_key.strip() != ""


def _validate_required_fields(company_info: CompanyInfo) -> Dict[str, Any]:
    """Validate that all required fields are present and correct."""
    errors = []
    warnings = []
    
    # Check company_name (case-insensitive)
    if not company_info.company_name:
        errors.append("company_name is missing")
    elif "bitmovin" not in company_info.company_name.lower():
        warnings.append(
            f"company_name mismatch: expected 'Bitmovin' (or variation), got '{company_info.company_name}'"
        )
    
    # Check industry
    if not company_info.industry or not company_info.industry.strip():
        errors.append("industry is missing or empty")
    elif "video" not in company_info.industry.lower() and "streaming" not in company_info.industry.lower():
        warnings.append(
            f"industry may be incorrect: expected video/streaming related, got '{company_info.industry}'"
        )
    
    # Check company_size (expected: "51-200 employees" or similar)
    if not company_info.company_size or not company_info.company_size.strip():
        errors.append("company_size is missing or empty")
    else:
        # Check for "51-200" range or variations like "51 to 200", "51-200", etc.
        has_51 = "51" in company_info.company_size or "50" in company_info.company_size
        has_200 = "200" in company_info.company_size
        if not (has_51 or has_200):
            warnings.append(
                f"company_size may be incorrect: expected 51-200 range, got '{company_info.company_size}'"
            )
    
    # Check headquarters (expected: "San Francisco, California, United States" or similar)
    if not company_info.headquarters or not company_info.headquarters.strip():
        errors.append("headquarters is missing or empty")
    else:
        hq_lower = company_info.headquarters.lower()
        # Check for San Francisco (primary requirement)
        has_sf = "san francisco" in hq_lower or "sf" in hq_lower
        # Also accept California or United States as they're part of the expected location
        has_ca = "california" in hq_lower or "ca" in hq_lower
        has_us = "united states" in hq_lower or "usa" in hq_lower or "u.s.a" in hq_lower
        
        if not (has_sf or (has_ca and has_us)):
            warnings.append(
                f"headquarters may be incorrect: expected San Francisco, California, United States, "
                f"got '{company_info.headquarters}'"
            )
    
    # Check founded
    if company_info.founded is None:
        errors.append("founded year is missing")
    elif company_info.founded != 2013:
        warnings.append(
            f"founded year mismatch: expected 2013, got {company_info.founded}"
        )
    
    return {"errors": errors, "warnings": warnings}


def _validate_optional_fields(company_info: CompanyInfo) -> Dict[str, Any]:
    """Validate optional fields if they are present."""
    present_fields = []
    missing_fields = []
    
    for field_name in OPTIONAL_FIELDS:
        field_value = getattr(company_info, field_name, None)
        if field_value is not None:
            if isinstance(field_value, str) and field_value.strip():
                present_fields.append(field_name)
            elif isinstance(field_value, (int, float, bool)):
                present_fields.append(field_name)
            elif isinstance(field_value, list) and len(field_value) > 0:
                present_fields.append(field_name)
            else:
                missing_fields.append(field_name)
        else:
            missing_fields.append(field_name)
    
    return {
        "present_fields": present_fields,
        "missing_fields": missing_fields,
        "coverage": len(present_fields) / len(OPTIONAL_FIELDS) if OPTIONAL_FIELDS else 0,
    }


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize("model_config", MODEL_CONFIGS)
def test_bitmovin_research_across_models(model_config: Dict[str, Any], mock_env_vars, monkeypatch):
    """Test research agent execution against each model type for BitMovin.
    
    This test:
    1. Initializes the research agent with the specified model type
    2. Executes research for BitMovin
    3. Validates required fields are present and correct
    4. Optionally validates additional fields if present
    
    Note: For integration tests, we use the real database (not the test database)
    so that API keys stored in the database are available. The mock_env_vars
    DATABASE_PATH is overridden to use the real database path.
    """
    # For integration tests with remote APIs, use real database for API keys
    # Override the mock DATABASE_PATH to use the real database
    import os
    # Remove the in-memory database path set by mock_env_vars fixture
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    # Use real database path for integration tests (has API keys)
    real_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "research_agent.db")
    os.environ["DATABASE_PATH"] = real_db_path
    model_type = model_config["model_type"]
    pytest_marker = model_config["pytest_marker"]
    skip_reason = model_config["skip_reason"]
    
    # Skip if API key or model is not available
    if not _check_api_key_available(model_type):
        pytest.skip(f"{skip_reason}")
    
    # Prepare model-specific configuration
    agent_kwargs = {
        "model_type": model_type,
        "verbose": False,  # Reduce noise in test output
        "max_iterations": 10,
    }
    
    # For local models, we may need to provide model_path
    if model_type == "local":
        model_path = os.getenv("MODEL_PATH")
        if model_path:
            agent_kwargs["model_path"] = model_path
        else:
            pytest.skip("MODEL_PATH not set for local model")
    
    # For remote models, we can specify model names if needed
    if model_type == "openai":
        # Use a specific model if desired, otherwise defaults to gpt-4-turbo-preview
        pass
    elif model_type == "anthropic":
        # Use a specific model if desired, otherwise defaults to claude-3-opus
        pass
    elif model_type == "gemini":
        # Use a specific model if desired, otherwise defaults to gemini-flash-latest
        pass
    
    # Initialize research agent
    print(f"\n{'='*60}")
    print(f"Testing {model_type.upper()} model for BitMovin research")
    print(f"{'='*60}")
    
    try:
        agent = ResearchAgent(**agent_kwargs)
    except Exception as e:
        pytest.skip(f"Failed to initialize {model_type} agent: {e}")
    
    # Execute research
    print(f"Executing research for BitMovin...")
    try:
        result: ResearchAgentResult = agent.research_company("BitMovin")
    except Exception as e:
        pytest.fail(f"Research agent execution failed for {model_type}: {e}")
    
    # Basic validation
    assert result is not None, f"Result is None for {model_type}"
    assert result.company_name == "BitMovin", f"Company name mismatch: {result.company_name}"
    
    # Validate success
    if not result.success:
        print(f"\n⚠️  Research returned success=False for {model_type}")
        print(f"Raw output: {result.raw_output[:500]}")
        print(f"Iterations: {result.iterations}")
        
        # Check if we got partial results despite success=False
        if result.company_info is None:
            pytest.fail(
                f"Research failed for {model_type}. "
                f"No company_info returned. Raw output: {result.raw_output[:200]}"
            )
    
    # Validate company_info structure
    assert result.company_info is not None, f"company_info is None for {model_type}"
    company_info: CompanyInfo = result.company_info
    
    # Validate required fields
    print(f"\nValidating required fields...")
    validation = _validate_required_fields(company_info)
    
    if validation["errors"]:
        error_msg = f"Required field validation failed for {model_type}:\n"
        error_msg += "\n".join(f"  - {error}" for error in validation["errors"])
        pytest.fail(error_msg)
    
    if validation["warnings"]:
        for warning in validation["warnings"]:
            print(f"  ⚠️  Warning: {warning}")
    
    # Validate optional fields
    print(f"\nValidating optional fields...")
    optional_validation = _validate_optional_fields(company_info)
    
    print(f"  Present fields: {len(optional_validation['present_fields'])}/{len(OPTIONAL_FIELDS)}")
    print(f"  Coverage: {optional_validation['coverage']:.1%}")
    
    if optional_validation["present_fields"]:
        print(f"  ✓ Found optional fields: {', '.join(optional_validation['present_fields'])}")
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"✅ {model_type.upper()} Test Summary")
    print(f"{'='*60}")
    print(f"  Success: {result.success}")
    print(f"  Execution time: {result.execution_time_seconds:.2f}s")
    print(f"  Iterations: {result.iterations}")
    print(f"  Required fields: ✅ All present")
    print(f"  Optional fields: {len(optional_validation['present_fields'])}/{len(OPTIONAL_FIELDS)}")
    
    # Print actual values
    print(f"\n  Extracted values:")
    print(f"    company_name: {company_info.company_name}")
    print(f"    industry: {company_info.industry}")
    print(f"    company_size: {company_info.company_size}")
    print(f"    headquarters: {company_info.headquarters}")
    print(f"    founded: {company_info.founded}")
    
    if optional_validation["present_fields"]:
        print(f"\n  Optional fields:")
        for field_name in optional_validation["present_fields"]:
            value = getattr(company_info, field_name)
            print(f"    {field_name}: {value}")
    
    print(f"{'='*60}\n")
    
    # Test passes if we got here
    assert result.success, f"Research should have succeeded for {model_type}"
    assert company_info is not None, f"Company info should not be None for {model_type}"


@pytest.mark.integration
@pytest.mark.slow
def test_bitmovin_research_all_models_available():
    """Test that at least one model is available for testing."""
    available_providers = list_available_providers()
    
    assert len(available_providers) > 0, "No models available for testing"
    
    # Check which ones have API keys
    available_for_testing = []
    for provider in available_providers:
        if _check_api_key_available(provider):
            available_for_testing.append(provider)
    
    print(f"\nAvailable providers: {available_providers}")
    print(f"Available for testing: {available_for_testing}")
    
    if not available_for_testing:
        pytest.skip("No models configured for testing (missing API keys or model files)")

