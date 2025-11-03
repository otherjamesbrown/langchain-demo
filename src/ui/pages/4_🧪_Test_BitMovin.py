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
    
    if not company_info.company_name:
        errors.append("company_name is missing")
    elif "bitmovin" not in company_info.company_name.lower():
        warnings.append(f"company_name mismatch: expected 'Bitmovin', got '{company_info.company_name}'")
    
    if not company_info.industry or not company_info.industry.strip():
        errors.append("industry is missing or empty")
    elif "video" not in company_info.industry.lower() and "streaming" not in company_info.industry.lower():
        warnings.append(f"industry may be incorrect: expected video/streaming related, got '{company_info.industry}'")
    
    if not company_info.company_size or not company_info.company_size.strip():
        errors.append("company_size is missing or empty")
    
    if not company_info.headquarters or not company_info.headquarters.strip():
        errors.append("headquarters is missing or empty")
    
    if company_info.founded is None:
        errors.append("founded year is missing")
    elif company_info.founded != 2013:
        warnings.append(f"founded year mismatch: expected 2013, got {company_info.founded}")
    
    return {"errors": errors, "warnings": warnings}

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
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True)
        
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
        test_data.append({
            "Model": test.model_name,
            "Provider": test.model_provider,
            "Success": "✅" if test.success and test.required_fields_valid else "❌",
            "Optional Fields": f"{test.optional_fields_count or 0}/10",
            "Time": f"{test.execution_time_seconds:.2f}s" if test.execution_time_seconds else "N/A",
            "Date": test.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        })
    
    st.dataframe(pd.DataFrame(test_data), use_container_width=True)
else:
    st.info("No test results yet. Run tests above to see results.")

