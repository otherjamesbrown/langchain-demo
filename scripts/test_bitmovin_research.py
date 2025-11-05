#!/usr/bin/env python3
"""
Standalone script to test BitMovin research across all available models.

This script:
1. Checks which models are available (local, OpenAI, Anthropic, Gemini)
2. Runs research agent for BitMovin against each available model
3. Validates required fields (company_name, industry, company_size, headquarters, founded)
4. Reports on optional fields if present
5. Provides summary output

Usage:
    # On server:
    cd ~/langchain-demo
    source venv/bin/activate
    python scripts/test_bitmovin_research.py
    
    # Or via SSH:
    ssh langchain@172.234.181.156 "cd ~/langchain-demo && source venv/bin/activate && python scripts/test_bitmovin_research.py"
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agent.research_agent import ResearchAgent, ResearchAgentResult
from src.tools.models import CompanyInfo
from src.utils.model_availability import get_available_models


# All fields are treated equally - no distinction between required/optional
# These are fields we expect to be present for BitMovin validation
EXPECTED_FIELDS = [
    "company_name",
    "company_size",
    "headquarters",
    "founded",
    "growth_stage",
    "industry_vertical",
    "sub_industry_vertical",
    "business_and_technology_adoption",
    "buyer_journey",
    "cloud_spend_capacity",
]


# Use shared utility function from utils module
def get_available_models_from_database() -> List[Dict[str, Any]]:
    """Query database for available model configurations.
    
    Wrapper around shared utility function for backward compatibility.
    Uses the new database-centric approach where all models and API keys
    are stored in the database as the single source of truth.
    """
    models = get_available_models()
    # Convert to expected format (includes extra_metadata and maintains structure)
    result = []
    for model in models:
        result.append({
            "provider": model["provider"],
            "name": model["name"],
            "model_key": model.get("model_key"),
            "model_path": model.get("model_path"),
            "api_identifier": model.get("api_identifier"),
            "extra_metadata": {},  # Not included in utility function output
            "config_id": model["config_id"],
        })
    return result


def validate_fields(company_info: CompanyInfo) -> Dict[str, Any]:
    """Validate all fields - no distinction between required/optional."""
    errors = []
    warnings = []
    present_fields = []
    missing_fields = []
    
    # Check company_name (case-insensitive)
    if not company_info.company_name:
        errors.append("company_name is missing")
        missing_fields.append("company_name")
    else:
        present_fields.append("company_name")
        if "bitmovin" not in company_info.company_name.lower():
            warnings.append(
                f"company_name mismatch: expected 'Bitmovin' (or variation), got '{company_info.company_name}'"
            )
    
    # Check company_size (expected: "51-200 employees" or similar)
    if not company_info.company_size or not company_info.company_size.strip():
        errors.append("company_size is missing or empty")
        missing_fields.append("company_size")
    else:
        present_fields.append("company_size")
        # Check for "51-200" range or variations
        has_51 = "51" in company_info.company_size or "50" in company_info.company_size
        has_200 = "200" in company_info.company_size
        if not (has_51 or has_200):
            warnings.append(
                f"company_size may be incorrect: expected 51-200 range, got '{company_info.company_size}'"
            )
    
    # Check headquarters (expected: "San Francisco, California, United States" or similar)
    if not company_info.headquarters or not company_info.headquarters.strip():
        errors.append("headquarters is missing or empty")
        missing_fields.append("headquarters")
    else:
        present_fields.append("headquarters")
        hq_lower = company_info.headquarters.lower()
        has_sf = "san francisco" in hq_lower or "sf" in hq_lower
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
        missing_fields.append("founded")
    else:
        present_fields.append("founded")
        if company_info.founded != 2013:
            warnings.append(
                f"founded year mismatch: expected 2013, got {company_info.founded}"
            )
    
    # Check other fields if present
    for field_name in ["growth_stage", "industry_vertical", "sub_industry_vertical", 
                       "business_and_technology_adoption", "buyer_journey", "cloud_spend_capacity"]:
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
        "errors": errors,
        "warnings": warnings,
        "present_fields": present_fields,
        "missing_fields": missing_fields,
        "coverage": len(present_fields) / len(EXPECTED_FIELDS) if EXPECTED_FIELDS else 0,
    }


def test_model(model_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Test research agent execution for a single model configuration."""
    
    model_type = model_config["provider"]
    model_name = model_config["name"]
    
    print(f"\n{'='*70}")
    print(f"Testing {model_name} ({model_type.upper()})")
    print(f"{'='*70}")
    
    # Prepare model-specific configuration
    agent_kwargs: Dict[str, Any] = {
        "model_type": model_type,
        "verbose": False,
        "max_iterations": 10,
    }
    
    # For local models, provide model_path
    if model_type == "local":
        model_path = model_config.get("model_path")
        if not model_path or not os.path.exists(model_path):
            print(f"⚠️  Skipping {model_name}: Model file not found at {model_path}")
            return None
        agent_kwargs["model_path"] = model_path
        # Use model_key if available for local model name
        if model_config.get("model_key"):
            agent_kwargs["local_model"] = model_config["model_key"]
    
    # For remote models, set API key from database and model identifier
    elif model_type in ["openai", "anthropic", "gemini"]:
        # API keys are handled by the model factory from database
        # But we can specify the model name if needed
        if model_config.get("api_identifier"):
            # Pass model name via model_kwargs
            agent_kwargs["model_kwargs"] = {
                "model_name": model_config["api_identifier"]
            }
    
    # Initialize research agent
    print(f"Initializing {model_name} agent...")
    try:
        agent = ResearchAgent(**agent_kwargs)
    except ImportError as e:
        print(f"⚠️  Skipping {model_name}: Required package not installed: {e}")
        return None
    except Exception as e:
        print(f"❌ Failed to initialize {model_name} agent: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Execute research
    print(f"Executing research for BitMovin...")
    try:
        result: ResearchAgentResult = agent.research_company("BitMovin")
    except Exception as e:
        print(f"❌ Research agent execution failed: {e}")
        return None
    
    # Basic validation
    if result is None:
        print(f"❌ Result is None")
        return None
    
    if result.company_name != "BitMovin":
        print(f"⚠️  Company name mismatch: {result.company_name}")
    
    # Validate success
    if not result.success:
        print(f"\n⚠️  Research returned success=False")
        print(f"Raw output: {result.raw_output[:500]}")
        print(f"Iterations: {result.iterations}")
        
        if result.company_info is None:
            print(f"❌ No company_info returned")
            return {
                "model_type": model_type,
                "success": False,
                "error": "No company_info returned",
                "raw_output": result.raw_output[:200],
            }
    
    # Validate company_info structure
    if result.company_info is None:
        print(f"❌ company_info is None")
        return {
            "model_type": model_type,
            "success": False,
            "error": "company_info is None",
        }
    
    company_info: CompanyInfo = result.company_info
    
    # Validate all fields (no distinction between required/optional)
    print(f"\nValidating fields...")
    validation = validate_fields(company_info)
    
    if validation["errors"]:
        print(f"❌ Field validation failed:")
        for error in validation["errors"]:
            print(f"   - {error}")
        return {
            "model_type": model_type,
            "success": False,
            "errors": validation["errors"],
            "warnings": validation["warnings"],
        }
    
    if validation["warnings"]:
        print(f"⚠️  Warnings:")
        for warning in validation["warnings"]:
            print(f"   - {warning}")
    
    print(f"   Present fields: {len(validation['present_fields'])}/{len(EXPECTED_FIELDS)}")
    print(f"   Coverage: {validation['coverage']:.1%}")
    
    if validation["present_fields"]:
        print(f"   ✓ Found fields: {', '.join(validation['present_fields'])}")
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"✅ {model_name} Test Summary")
    print(f"{'='*70}")
    print(f"  Success: {result.success}")
    print(f"  Execution time: {result.execution_time_seconds:.2f}s")
    print(f"  Iterations: {result.iterations}")
    print(f"  Fields present: {len(validation['present_fields'])}/{len(EXPECTED_FIELDS)}")
    
    # Print actual values
    print(f"\n  Extracted values:")
    print(f"    company_name: {company_info.company_name}")
    print(f"    company_size: {company_info.company_size}")
    print(f"    headquarters: {company_info.headquarters}")
    print(f"    founded: {company_info.founded}")
    
    if validation["present_fields"]:
        other_fields = [f for f in validation["present_fields"] 
                       if f not in ["company_name", "company_size", "headquarters", "founded"]]
        if other_fields:
            print(f"\n  Other fields:")
            for field_name in other_fields:
                value = getattr(company_info, field_name)
                print(f"    {field_name}: {value}")
    
    print(f"{'='*70}")
    
    return {
        "model_type": model_type,
        "model_name": model_name,
        "success": result.success,
        "execution_time": result.execution_time_seconds,
        "iterations": result.iterations,
        "required_fields_valid": len(validation["errors"]) == 0,  # For backwards compatibility
        "optional_fields_count": len(validation["present_fields"]),  # All fields counted
        "optional_fields_coverage": validation["coverage"],
        "warnings": validation["warnings"],
        "company_info": {
            "company_name": company_info.company_name,
            "company_size": company_info.company_size,
            "headquarters": company_info.headquarters,
            "founded": company_info.founded,
        },
    }


def main():
    """Main test execution."""
    print("="*70)
    print("BitMovin Research Test - All Models")
    print("="*70)
    print("\nThis test will run the research agent for BitMovin against")
    print("all available models configured in the database.")
    print("\nExpected fields (all treated equally):")
    print("  - company_name: Bitmovin")
    print("  - company_size: 51-200 employees")
    print("  - headquarters: San Francisco, California, United States")
    print("  - founded: 2013")
    print("  - growth_stage, industry_vertical, sub_industry_vertical, etc.")
    print("="*70)
    
    # Get available models from database
    print("\nQuerying database for available model configurations...")
    available_models = get_available_models_from_database()
    
    if not available_models:
        print("\n❌ No models found in database or models are not properly configured")
        print("\nTo configure models:")
        print("  1. Ensure database is initialized (run Streamlit app once)")
        print("  2. For local models: Models should be auto-registered from registry")
        print("  3. For remote models: API keys should be stored in api_credentials table")
        print("     (API keys are typically added through the Streamlit UI)")
        return 1
    
    print(f"\nFound {len(available_models)} available model(s):")
    for model in available_models:
        print(f"  - {model['name']} ({model['provider']})")
    
    # Test each model
    results = []
    for model_config in available_models:
        result = test_model(model_config)
        if result:
            results.append(result)
    
    # Final summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")
    
    if not results:
        print("❌ No tests completed successfully")
        return 1
    
    successful = [r for r in results if r.get("success", False) and r.get("required_fields_valid", False)]
    print(f"\n✅ Successful tests: {len(successful)}/{len(results)}")
    
    for result in results:
        model_name = result.get("model_name", result.get("model_type", "Unknown"))
        model_type = result["model_type"]
        success = "✅" if result.get("success", False) and result.get("required_fields_valid", False) else "❌"
        field_count = result.get("optional_fields_count", 0)
        print(f"  {success} {model_name} ({model_type.upper()}): {field_count}/{len(EXPECTED_FIELDS)} fields")
    
    print(f"\n{'='*70}")
    
    # Return exit code based on results
    if len(successful) == len(results):
        print("✅ All tests passed!")
        return 0
    else:
        print("⚠️  Some tests had issues")
        return 1


if __name__ == "__main__":
    sys.exit(main())

