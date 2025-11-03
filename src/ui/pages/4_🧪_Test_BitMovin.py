#!/usr/bin/env python3
"""
BitMovin Test Execution Page

Run automated tests for BitMovin research across all available models.
Results are saved to the database for validation.

URL: http://host:8501/Test_BitMovin
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Change to project directory so imports work correctly
import os
os.chdir(project_root)

import streamlit as st
import pandas as pd
import time
from datetime import datetime

from src.database.schema import get_session, create_database
from src.database.operations import (
    ensure_default_configuration,
    get_model_configurations,
    get_api_key,
    save_test_execution,
    get_test_executions,
)
from src.agent.research_agent import ResearchAgent, ResearchAgentResult
from src.tools.models import CompanyInfo

# Import validation functions (duplicated here to avoid import issues)
def check_package_installed(package_name: str) -> bool:
    """Check if a Python package is installed."""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def validate_required_fields(company_info: CompanyInfo):
    """Validate that all required fields are present and correct."""
    errors = []
    warnings = []
    correct_fields = []
    incorrect_fields = []
    blank_fields = []
    
    # Expected values
    expected_values = {
        "company_name": "Bitmovin",
        "industry": ["video", "streaming"],
        "company_size": ["51", "200"],
        "headquarters": ["san francisco", "california"],
        "founded": 2013,
    }
    
    # Check company_name
    if not company_info.company_name or not company_info.company_name.strip():
        blank_fields.append(("company_name", "missing or empty"))
        errors.append("company_name is missing")
    elif "bitmovin" not in company_info.company_name.lower():
        incorrect_fields.append(("company_name", f"expected 'Bitmovin', got '{company_info.company_name}'"))
        warnings.append(f"company_name mismatch: expected 'Bitmovin', got '{company_info.company_name}'")
    else:
        correct_fields.append("company_name")
    
    # Check industry
    if not company_info.industry or not company_info.industry.strip():
        blank_fields.append(("industry", "missing or empty"))
        errors.append("industry is missing or empty")
    else:
        industry_lower = company_info.industry.lower()
        if any(keyword in industry_lower for keyword in expected_values["industry"]):
            correct_fields.append("industry")
        else:
            incorrect_fields.append(("industry", f"expected video/streaming related, got '{company_info.industry}'"))
            warnings.append(f"industry may be incorrect: expected video/streaming related, got '{company_info.industry}'")
    
    # Check company_size
    if not company_info.company_size or not company_info.company_size.strip():
        blank_fields.append(("company_size", "missing or empty"))
        errors.append("company_size is missing or empty")
    else:
        size_str = company_info.company_size
        if any(keyword in size_str for keyword in expected_values["company_size"]):
            correct_fields.append("company_size")
        else:
            incorrect_fields.append(("company_size", f"expected 51-200 range, got '{company_info.company_size}'"))
    
    # Check headquarters
    if not company_info.headquarters or not company_info.headquarters.strip():
        blank_fields.append(("headquarters", "missing or empty"))
        errors.append("headquarters is missing or empty")
    else:
        hq_lower = company_info.headquarters.lower()
        if any(keyword in hq_lower for keyword in expected_values["headquarters"]):
            correct_fields.append("headquarters")
        else:
            incorrect_fields.append(("headquarters", f"expected San Francisco, California, got '{company_info.headquarters}'"))
    
    # Check founded
    if company_info.founded is None:
        blank_fields.append(("founded", "missing"))
        errors.append("founded year is missing")
    elif company_info.founded != expected_values["founded"]:
        incorrect_fields.append(("founded", f"expected 2013, got {company_info.founded}"))
        warnings.append(f"founded year mismatch: expected 2013, got {company_info.founded}")
    else:
        correct_fields.append("founded")
    
    return {
        "errors": errors,
        "warnings": warnings,
        "correct": correct_fields,
        "incorrect": incorrect_fields,
        "blank": blank_fields,
    }

OPTIONAL_FIELDS = [
    "growth_stage", "industry_vertical", "sub_industry_vertical",
    "financial_health", "business_and_technology_adoption",
    "primary_workload_philosophy", "buyer_journey",
    "budget_maturity", "cloud_spend_capacity", "procurement_process",
]

def validate_optional_fields(company_info: CompanyInfo):
    """Validate optional fields if they are present."""
    present_fields = []
    for field_name in OPTIONAL_FIELDS:
        field_value = getattr(company_info, field_name, None)
        if field_value is not None:
            if isinstance(field_value, str) and field_value.strip():
                present_fields.append(field_name)
            elif isinstance(field_value, (int, float, bool)):
                present_fields.append(field_name)
            elif isinstance(field_value, list) and len(field_value) > 0:
                present_fields.append(field_name)
    
    return {
        "present_fields": present_fields,
        "coverage": len(present_fields) / len(OPTIONAL_FIELDS) if OPTIONAL_FIELDS else 0,
    }

def check_provider_packages_installed(provider: str) -> bool:
    """Check if required packages are installed for a provider."""
    package_map = {
        "local": "llama_cpp",
        "openai": "langchain_openai",
        "anthropic": "langchain_anthropic",
        "gemini": "langchain_google_genai",
    }
    
    required_package = package_map.get(provider)
    if not required_package:
        return False
    
    # Check if package can be imported
    try:
        if provider == "openai":
            __import__("langchain_openai")
        elif provider == "anthropic":
            __import__("langchain_anthropic")
        elif provider == "gemini":
            __import__("langchain_google_genai")
        elif provider == "local":
            __import__("llama_cpp")
        return True
    except ImportError:
        return False

def get_available_models_from_database():
    """Get available models from database."""
    from src.database.operations import get_api_key
    
    model_configs = get_model_configurations(session=session)
    available_models = []
    
    for config in model_configs:
        # First check if required packages are installed
        if not check_provider_packages_installed(config.provider):
            continue
        
        is_usable = False
        
        if config.provider == "local":
            if config.model_path and os.path.exists(os.path.expanduser(config.model_path)):
                is_usable = True
        else:
            api_key = get_api_key(config.provider, session=session)
            if api_key and api_key.strip():
                is_usable = True
        
        if is_usable:
            available_models.append({
                "provider": config.provider,
                "name": config.name,
                "model_key": config.model_key,
                "model_path": config.model_path,
                "api_identifier": config.api_identifier,
                "config_id": config.id,
            })
    
    return available_models

# Page config
st.set_page_config(
    page_title="Test BitMovin - Dashboard",
    page_icon="🧪",
    layout="wide"
)

# Initialize database
@st.cache_resource
def init_db():
    """Initialize database connection."""
    create_database()
    return get_session()

# Main page
st.title("🧪 BitMovin Research Test")
st.markdown("Run automated tests for BitMovin research across all available models")

# Initialize database
try:
    session = init_db()
except Exception as e:
    st.error(f"Failed to connect to database: {e}")
    st.stop()

ensure_default_configuration(session=session)

# Sidebar
st.sidebar.header("⚙️ Test Configuration")

# Get available models
st.sidebar.info("This test validates that models can extract required company information for BitMovin.")
st.sidebar.markdown("### Required Fields")
st.sidebar.markdown("- company_name: Bitmovin")
st.sidebar.markdown("- industry: Video Streaming Infrastructure / SaaS")
st.sidebar.markdown("- company_size: 51-200 employees")
st.sidebar.markdown("- headquarters: San Francisco, California, United States")
st.sidebar.markdown("- founded: 2013")

st.sidebar.markdown("### Optional Fields")
st.sidebar.markdown("10 additional GTM classification fields")

# Get available models
with st.spinner("Loading available models..."):
    available_models = get_available_models_from_database()

if not available_models:
    st.error("No models available for testing. Please configure models and API keys.")
    st.stop()

# Model selection
st.subheader("Select Models to Test")
model_selections = {}
for model in available_models:
    model_key = f"model_{model['config_id']}"
    model_selections[model['name']] = st.checkbox(
        f"{model['name']} ({model['provider']})",
        key=model_key,
        value=True
    )

selected_models = [m for m in available_models if model_selections.get(m['name'], False)]

if not selected_models:
    st.warning("Please select at least one model to test.")
    st.stop()

# Run test button
if st.button("🚀 Run Tests", type="primary"):
    st.markdown("---")
    st.subheader("Test Execution")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    results_container = st.container()
    
    results = []
    
    for idx, model_config in enumerate(selected_models):
        model_name = model_config['name']
        model_type = model_config['provider']
        
        progress = (idx) / len(selected_models)
        progress_bar.progress(progress)
        status_text.text(f"Testing {model_name} ({idx+1}/{len(selected_models)})...")
        
        with results_container:
            with st.expander(f"Testing: {model_name}", expanded=False):
                try:
                    # Prepare agent configuration
                    agent_kwargs = {
                        "model_type": model_type,
                        "verbose": False,
                        "max_iterations": 10,
                    }
                    
                    if model_type == "local":
                        agent_kwargs["model_path"] = model_config.get("model_path")
                        if model_config.get("model_key"):
                            agent_kwargs["local_model"] = model_config["model_key"]
                    else:
                        if model_config.get("api_identifier"):
                            agent_kwargs["model_kwargs"] = {
                                "model_name": model_config["api_identifier"]
                            }
                    
                    # Initialize and run
                    agent = ResearchAgent(**agent_kwargs)
                    result: ResearchAgentResult = agent.research_company("BitMovin")
                    
                    # Validate results
                    if result.company_info:
                        validation = validate_required_fields(result.company_info)
                        optional_validation = validate_optional_fields(result.company_info)
                        
                        # Save to database
                        company_info_dict = None
                        if result.company_info:
                            company_info_dict = result.company_info.model_dump()
                        
                        test_record = save_test_execution(
                            test_name="bitmovin_research",
                            test_company="BitMovin",
                            model_configuration_id=model_config.get("config_id"),
                            model_name=model_name,
                            model_provider=model_type,
                            success=result.success and len(validation["errors"]) == 0,
                            required_fields_valid=len(validation["errors"]) == 0,
                            execution_time_seconds=result.execution_time_seconds,
                            iterations=result.iterations,
                            required_fields_errors=validation["errors"],
                            required_fields_warnings=validation["warnings"],
                            optional_fields_count=len(optional_validation["present_fields"]),
                            optional_fields_coverage=optional_validation["coverage"],
                            optional_fields_present=optional_validation["present_fields"],
                            extracted_company_info=company_info_dict,
                            raw_output=result.raw_output[:1000] if result.raw_output else None,
                            session=session,
                        )
                        
                        # Display results
                        if len(validation["errors"]) == 0:
                            st.success(f"✅ Passed - All required fields valid")
                        else:
                            st.error(f"❌ Failed - {len(validation['errors'])} validation errors")
                            for error in validation["errors"]:
                                st.error(f"  - {error}")
                        
                        if validation["warnings"]:
                            for warning in validation["warnings"]:
                                st.warning(f"⚠️ {warning}")
                        
                        # Field categorization display
                        st.markdown("#### Field Validation")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if validation["correct"]:
                                st.success(f"✅ **Correct ({len(validation['correct'])})**")
                                for field in validation["correct"]:
                                    value = getattr(result.company_info, field, None)
                                    if isinstance(value, str):
                                        st.text(f"  • {field}: {value[:50]}")
                                    else:
                                        st.text(f"  • {field}: {value}")
                            else:
                                st.info("✅ **Correct: 0**")
                        
                        with col2:
                            if validation["incorrect"]:
                                st.warning(f"⚠️ **Incorrect ({len(validation['incorrect'])})**")
                                for field, reason in validation["incorrect"]:
                                    value = getattr(result.company_info, field, None)
                                    st.text(f"  • {field}: {value}")
                                    st.caption(f"    ({reason})")
                            else:
                                st.info("⚠️ **Incorrect: 0**")
                        
                        with col3:
                            if validation["blank"]:
                                st.error(f"❌ **Blank/Missing ({len(validation['blank'])})**")
                                for field, reason in validation["blank"]:
                                    st.text(f"  • {field}: {reason}")
                            else:
                                st.info("❌ **Blank/Missing: 0**")
                        
                        st.metric("Optional Fields", f"{len(optional_validation['present_fields'])}/10")
                        st.metric("Execution Time", f"{result.execution_time_seconds:.2f}s")
                        
                        results.append({
                            "model": model_name,
                            "provider": model_type,
                            "success": len(validation["errors"]) == 0,
                            "optional_fields": len(optional_validation["present_fields"]),
                            "time": result.execution_time_seconds,
                        })
                    else:
                        st.error("❌ Failed - No company info returned")
                        save_test_execution(
                            test_name="bitmovin_research",
                            test_company="BitMovin",
                            model_configuration_id=model_config.get("config_id"),
                            model_name=model_name,
                            model_provider=model_type,
                            success=False,
                            required_fields_valid=False,
                            error_message="No company info returned",
                            raw_output=result.raw_output[:1000] if result.raw_output else None,
                            session=session,
                        )
                        results.append({
                            "model": model_name,
                            "provider": model_type,
                            "success": False,
                            "optional_fields": 0,
                            "time": result.execution_time_seconds,
                        })
                        
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
                    
                    save_test_execution(
                        test_name="bitmovin_research",
                        test_company="BitMovin",
                        model_configuration_id=model_config.get("config_id"),
                        model_name=model_name,
                        model_provider=model_type,
                        success=False,
                        required_fields_valid=False,
                        error_message=str(e),
                        session=session,
                    )
                    
                    results.append({
                        "model": model_name,
                        "provider": model_type,
                        "success": False,
                        "optional_fields": 0,
                        "time": 0,
                    })
    
    progress_bar.progress(1.0)
    status_text.text("✅ All tests completed!")
    
    # Results summary
    st.markdown("---")
    st.subheader("📊 Test Summary")
    
    if results:
        # Get detailed field information for each test
        summary_data = []
        for result_entry in results:
            # Get the test execution from database for field details
            test_exec = get_test_executions(
                test_name="bitmovin_research",
                test_company="BitMovin",
                model_provider=result_entry["provider"],
                limit=1,
                session=session,
            )
            
            if test_exec and test_exec[0].extracted_company_info:
                ci = test_exec[0].extracted_company_info
                # Categorize fields
                correct = []
                incorrect = []
                blank = []
                
                # Check each required field
                required_fields = ["company_name", "industry", "company_size", "headquarters", "founded"]
                for field in required_fields:
                    value = ci.get(field)
                    
                    if value is None or (isinstance(value, str) and not value.strip()):
                        blank.append(field)
                    elif field == "company_name" and "bitmovin" in str(value).lower():
                        correct.append(field)
                    elif field == "company_name":
                        incorrect.append(field)
                    elif field == "industry" and ("video" in str(value).lower() or "streaming" in str(value).lower()):
                        correct.append(field)
                    elif field == "industry":
                        incorrect.append(field)
                    elif field == "company_size" and ("51" in str(value) or "200" in str(value)):
                        correct.append(field)
                    elif field == "company_size":
                        incorrect.append(field)
                    elif field == "headquarters" and ("san francisco" in str(value).lower() or "california" in str(value).lower()):
                        correct.append(field)
                    elif field == "headquarters":
                        incorrect.append(field)
                    elif field == "founded" and value == 2013:
                        correct.append(field)
                    elif field == "founded":
                        incorrect.append(field)
                
                summary_data.append({
                    "Model": result_entry["model"],
                    "Provider": result_entry["provider"],
                    "Success": "✅" if result_entry["success"] else "❌",
                    "Correct Fields": f"{len(correct)}/5",
                    "Incorrect Fields": len(incorrect),
                    "Blank Fields": len(blank),
                    "Optional Fields": f"{result_entry['optional_fields']}/10",
                    "Time": f"{result_entry['time']:.2f}s",
                })
            else:
                summary_data.append({
                    "Model": result_entry["model"],
                    "Provider": result_entry["provider"],
                    "Success": "❌",
                    "Correct Fields": "0/5",
                    "Incorrect Fields": 0,
                    "Blank Fields": 5,
                    "Optional Fields": "0/10",
                    "Time": f"{result_entry['time']:.2f}s",
                })
        
        if summary_data:
            df = pd.DataFrame(summary_data)
            st.dataframe(df, use_container_width=True)
            
            # Show detailed field breakdown for each model
            for result_entry in results:
                test_exec = get_test_executions(
                    test_name="bitmovin_research",
                    test_company="BitMovin",
                    model_provider=result_entry["provider"],
                    limit=1,
                    session=session,
                )
                
                if test_exec and test_exec[0].extracted_company_info:
                    with st.expander(f"Field Details: {result_entry['model']}"):
                        ci = test_exec[0].extracted_company_info
                        
                        # Required Fields Section
                        st.markdown("### Required Fields (5)")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.markdown("**✅ Correct Fields**")
                            correct_required = []
                            if ci.get("company_name") and "bitmovin" in str(ci.get("company_name", "")).lower():
                                correct_required.append(("company_name", ci.get("company_name")))
                            if ci.get("industry") and ("video" in str(ci.get("industry", "")).lower() or "streaming" in str(ci.get("industry", "")).lower()):
                                correct_required.append(("industry", ci.get("industry")))
                            if ci.get("company_size") and ("51" in str(ci.get("company_size", "")) or "200" in str(ci.get("company_size", ""))):
                                correct_required.append(("company_size", ci.get("company_size")))
                            if ci.get("headquarters") and ("san francisco" in str(ci.get("headquarters", "")).lower() or "california" in str(ci.get("headquarters", "")).lower()):
                                correct_required.append(("headquarters", ci.get("headquarters")))
                            if ci.get("founded") == 2013:
                                correct_required.append(("founded", ci.get("founded")))
                            
                            if correct_required:
                                st.text(f"({len(correct_required)}/5)")
                                for field, value in correct_required:
                                    st.text(f"• {field}: {value}")
                            else:
                                st.text("(0/5)")
                                st.text("None")
                        
                        with col2:
                            st.markdown("**⚠️ Incorrect Fields**")
                            incorrect_required = []
                            if ci.get("company_name") and "bitmovin" not in str(ci.get("company_name", "")).lower():
                                incorrect_required.append(("company_name", ci.get("company_name"), "Expected 'Bitmovin'"))
                            if ci.get("industry") and "video" not in str(ci.get("industry", "")).lower() and "streaming" not in str(ci.get("industry", "")).lower():
                                incorrect_required.append(("industry", ci.get("industry"), "Expected video/streaming"))
                            if ci.get("company_size") and "51" not in str(ci.get("company_size", "")) and "200" not in str(ci.get("company_size", "")):
                                incorrect_required.append(("company_size", ci.get("company_size"), "Expected 51-200 range"))
                            if ci.get("headquarters") and "san francisco" not in str(ci.get("headquarters", "")).lower() and "california" not in str(ci.get("headquarters", "")).lower():
                                incorrect_required.append(("headquarters", ci.get("headquarters"), "Expected San Francisco, CA"))
                            if ci.get("founded") and ci.get("founded") != 2013:
                                incorrect_required.append(("founded", ci.get("founded"), "Expected 2013"))
                            
                            if incorrect_required:
                                st.text(f"({len(incorrect_required)})")
                                for field, value, expected in incorrect_required:
                                    st.text(f"• {field}: {value}")
                                    st.caption(f"  ({expected})")
                            else:
                                st.text("(0)")
                                st.text("None")
                        
                        with col3:
                            st.markdown("**❌ Blank/Missing Fields**")
                            blank_required = []
                            if not ci.get("company_name") or not str(ci.get("company_name", "")).strip():
                                blank_required.append("company_name")
                            if not ci.get("industry") or not str(ci.get("industry", "")).strip():
                                blank_required.append("industry")
                            if not ci.get("company_size") or not str(ci.get("company_size", "")).strip():
                                blank_required.append("company_size")
                            if not ci.get("headquarters") or not str(ci.get("headquarters", "")).strip():
                                blank_required.append("headquarters")
                            if ci.get("founded") is None:
                                blank_required.append("founded")
                            
                            if blank_required:
                                st.text(f"({len(blank_required)})")
                                for field in blank_required:
                                    st.text(f"• {field}")
                            else:
                                st.text("(0)")
                                st.text("None")
                        
                        # Optional Fields Section
                        st.markdown("---")
                        st.markdown("### Optional Fields (10)")
                        col4, col5, col6 = st.columns(3)
                        
                        # Get list of optional fields that were actually present in the test
                        optional_fields_present = test_exec[0].optional_fields_present or []
                        
                        with col4:
                            st.markdown("**✅ Present Fields**")
                            if optional_fields_present:
                                st.text(f"({len(optional_fields_present)}/10)")
                                for field_name in optional_fields_present:
                                    value = ci.get(field_name)
                                    if value is not None:
                                        if isinstance(value, str):
                                            display_value = value[:50] + "..." if len(value) > 50 else value
                                        elif isinstance(value, list):
                                            display_value = ", ".join(str(v) for v in value[:3])
                                            if len(value) > 3:
                                                display_value += f" ... (+{len(value)-3} more)"
                                        else:
                                            display_value = str(value)
                                        st.text(f"• {field_name}: {display_value}")
                            else:
                                st.text("(0/10)")
                                st.text("None")
                        
                        with col5:
                            st.markdown("**⚠️ Incorrect Fields**")
                            # For optional fields, we consider them incorrect if they exist but have invalid values
                            # Since optional fields don't have strict validation, this would be empty
                            # unless we want to validate against specific expected values
                            st.text("(0)")
                            st.text("N/A - Optional fields")
                            st.caption("Optional fields are not validated")
                        
                        with col6:
                            st.markdown("**❌ Blank/Missing Fields**")
                            # Get all optional field names
                            all_optional_fields = [
                                "growth_stage", "industry_vertical", "sub_industry_vertical",
                                "financial_health", "business_and_technology_adoption",
                                "primary_workload_philosophy", "buyer_journey",
                                "budget_maturity", "cloud_spend_capacity", "procurement_process",
                            ]
                            missing_optional = [field for field in all_optional_fields if field not in optional_fields_present]
                            
                            if missing_optional:
                                st.text(f"({len(missing_optional)})")
                                for field in missing_optional:
                                    st.text(f"• {field}")
                            else:
                                st.text("(0)")
                                st.text("None")
        
        success_count = sum(1 for r in results if r["success"])
        st.metric("Success Rate", f"{success_count}/{len(results)}")

# Show recent test results
st.markdown("---")
st.subheader("📋 Recent Test Results")

recent_tests = get_test_executions(
    test_name="bitmovin_research",
    test_company="BitMovin",
    limit=20,
    session=session,
)

if recent_tests:
    test_data = []
    for test in recent_tests:
        # Calculate required fields count from extracted company info
        required_fields_count = 0
        if test.extracted_company_info:
            ci = test.extracted_company_info
            
            # Check each required field
            if ci.get("company_name") and "bitmovin" in str(ci.get("company_name", "")).lower():
                required_fields_count += 1
            if ci.get("industry") and ("video" in str(ci.get("industry", "")).lower() or "streaming" in str(ci.get("industry", "")).lower()):
                required_fields_count += 1
            if ci.get("company_size") and ("51" in str(ci.get("company_size", "")) or "200" in str(ci.get("company_size", ""))):
                required_fields_count += 1
            if ci.get("headquarters") and ("san francisco" in str(ci.get("headquarters", "")).lower() or "california" in str(ci.get("headquarters", "")).lower()):
                required_fields_count += 1
            if ci.get("founded") == 2013:
                required_fields_count += 1
        
        test_data.append({
            "Model": test.model_name,
            "Provider": test.model_provider,
            "Success": "✅" if test.success and test.required_fields_valid else "❌",
            "Required Fields": f"{required_fields_count}/5",
            "Optional Fields": f"{test.optional_fields_count or 0}/10",
            "Time": f"{test.execution_time_seconds:.2f}s" if test.execution_time_seconds else "N/A",
            "Date": test.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        })
    
    st.dataframe(pd.DataFrame(test_data), use_container_width=True)
else:
    st.info("No test results yet. Run tests above to see results.")

