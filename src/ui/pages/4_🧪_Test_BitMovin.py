#!/usr/bin/env python3
"""
BitMovin Test Execution Page - Enhanced with Testing Framework

Run automated tests for BitMovin research across all available models using
the unified testing framework. Displays rich comparison views with confidence
scores, visual indicators, and detailed field-by-field analysis.

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
import json
from datetime import datetime
from typing import List, Dict, Any

from src.database.schema import get_session, create_database
from src.database.operations import (
    ensure_default_configuration,
    get_model_configurations,
    get_api_key,
    save_test_execution,
    get_test_executions,
)

# Import testing framework components
from src.testing.test_runner import TestRunner, ModelTestResult, TestExecutionResult
from src.testing.baselines import get_baseline
from src.testing.matchers import FieldMatcher

# Model availability checking (shared from CLI script logic)
def check_package_installed(package_name: str) -> bool:
    """Check if a Python package is installed."""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

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
    
    try:
        if provider == "openai":
            return check_package_installed("langchain_openai") or check_package_installed("openai")
        elif provider == "anthropic":
            return check_package_installed("langchain_anthropic") or check_package_installed("anthropic")
        elif provider == "gemini":
            return check_package_installed("langchain_google_genai") or check_package_installed("google.generativeai")
        elif provider == "local":
            return check_package_installed("llama_cpp") or check_package_installed("llama_cpp_python")
    except ImportError:
        return False
    return False

def get_available_models_from_database(session) -> List[Dict[str, Any]]:
    """
    Get available model configurations from database.
    
    Educational: This function validates that models are actually usable
    (packages installed, model files exist, API keys available) before
    allowing them to be selected for testing.
    """
    model_configs = get_model_configurations(session=session)
    available_models = []
    
    for config in model_configs:
        # Check if required packages are installed
        if not check_provider_packages_installed(config.provider):
            continue
        
        # Check if model is usable
        is_usable = False
        
        if config.provider == "local":
            if config.model_path and os.path.exists(os.path.expanduser(config.model_path)):
                is_usable = True
        else:
            api_key = get_api_key(config.provider, session=session)
            if api_key and api_key.strip():
                is_usable = True
        
        if is_usable:
            model_dict = {
                "name": config.name,
                "provider": config.provider,
                "config_id": config.id,
            }
            
            if config.provider == "local":
                if config.model_path:
                    model_dict["model_path"] = config.model_path
                if config.model_key:
                    model_dict["model_key"] = config.model_key
            else:
                if config.api_identifier:
                    model_dict["api_identifier"] = config.api_identifier
            
            available_models.append(model_dict)
    
    return available_models

def format_confidence_score(confidence: float) -> str:
    """Format confidence score with color-coded indicator."""
    percentage = confidence * 100
    if percentage >= 80:
        return f"✅ {percentage:.0f}%"
    elif percentage >= 50:
        return f"⚠️ {percentage:.0f}%"
    else:
        return f"❌ {percentage:.0f}%"

def display_field_match_details(field_result, baseline_field):
    """Display detailed field match information."""
    status_icon = "✅" if field_result.is_match else "❌"
    confidence_pct = field_result.confidence * 100
    
    # Create visual indicator based on confidence
    if confidence_pct >= 80:
        color = "green"
        bg_color = "#d4edda"
    elif confidence_pct >= 50:
        color = "orange"
        bg_color = "#fff3cd"
    else:
        color = "red"
        bg_color = "#f8d7da"
    
    st.markdown(
        f"""
        <div style="background-color: {bg_color}; padding: 10px; border-radius: 5px; margin: 5px 0;">
            <strong>{status_icon} {baseline_field.field_name}</strong><br>
            <small>
            Expected: <code>{baseline_field.expected_value}</code><br>
            Actual: <code>{field_result.actual_value}</code><br>
            Match Type: <code>{field_result.match_type}</code><br>
            Confidence: <strong>{confidence_pct:.1f}%</strong>
            </small>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    if field_result.error_message:
        st.caption(f"⚠️ {field_result.error_message}")

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
st.markdown("""
Run automated tests for BitMovin research across all available models using the 
**unified testing framework**. This page uses fuzzy matching, confidence scores, 
and detailed field-by-field validation.
""")

# Initialize database
try:
    session = init_db()
except Exception as e:
    st.error(f"Failed to connect to database: {e}")
    st.stop()

ensure_default_configuration(session=session)

# Sidebar
st.sidebar.header("⚙️ Test Configuration")

# Load baseline info
try:
    baseline = get_baseline("bitmovin")
    st.sidebar.info(f"**Test:** {baseline.test_name}\n\n{baseline.description}")
    
    st.sidebar.markdown("### Required Fields")
    for field_exp in baseline.required_fields:
        match_type_icon = {
            "exact": "🎯",
            "keyword": "🔑",
            "fuzzy": "📊",
            "regex": "🔍",
            "custom": "⚙️"
        }
        icon = match_type_icon.get(field_exp.match_type.value, "•")
        st.sidebar.markdown(f"{icon} **{field_exp.field_name}** ({field_exp.match_type.value})")
        if field_exp.description:
            st.sidebar.caption(f"   {field_exp.description}")
    
    st.sidebar.markdown(f"\n### Optional Fields ({len(baseline.optional_fields)})")
    st.sidebar.caption("GTM classification fields (growth_stage, industry_vertical, etc.)")
    
except Exception as e:
    st.sidebar.error(f"Error loading baseline: {e}")
    st.stop()

# Get available models
with st.spinner("Loading available models..."):
    available_models = get_available_models_from_database(session)

if not available_models:
    st.error("No models available for testing. Please configure models and API keys.")
    st.stop()

# Configuration section
st.subheader("⚙️ Configuration")
col_config1, col_config2 = st.columns(2)

with col_config1:
    max_iterations = st.number_input(
        "Max Iterations",
        min_value=1,
        max_value=20,
        value=10,
        help="Maximum agent iterations per model"
    )

with col_config2:
    verbose_mode = st.checkbox(
        "Verbose Mode",
        value=False,
        help="Show detailed agent reasoning (slower, more output)"
    )

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
    
    # Initialize TestRunner
    with st.spinner("Initializing test framework..."):
        try:
            runner = TestRunner(model_configs=selected_models)
        except Exception as e:
            st.error(f"Failed to initialize TestRunner: {e}")
            st.stop()
    
    # Run tests with progress indicator
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    status_text.text(f"Running test across {len(selected_models)} model(s)...")
    
    try:
        test_result: TestExecutionResult = runner.run_test(
            baseline=baseline,
            max_iterations=max_iterations,
            verbose=verbose_mode,
        )
        
        progress_bar.progress(1.0)
        status_text.text("✅ All tests completed!")
        
        # Display results
        st.markdown("---")
        st.subheader("📊 Test Results Summary")
        
        # Overall metrics
        col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)
        
        with col_metric1:
            st.metric("Average Score", f"{test_result.average_score:.1%}")
        
        with col_metric2:
            st.metric("Best Model", test_result.best_model or "N/A")
        
        with col_metric3:
            st.metric("Total Time", f"{test_result.execution_time:.1f}s")
        
        with col_metric4:
            successful_count = sum(1 for mr in test_result.model_results if mr.success)
            st.metric("Success Rate", f"{successful_count}/{len(test_result.model_results)}")
        
        # Model comparison table
        st.markdown("### Model Comparison")
        
        comparison_data = []
        for mr in test_result.model_results:
            comparison_data.append({
                "Model": mr.model_name,
                "Provider": mr.model_provider,
                "Overall Score": f"{mr.overall_score:.1%}",
                "Required Fields": f"{mr.required_fields_score:.1%}",
                "Optional Fields": f"{mr.optional_fields_score:.1%}",
                "Success": "✅" if mr.success else "❌",
                "Time": f"{mr.execution_time:.1f}s",
                "Iterations": mr.iterations,
            })
        
        df_comparison = pd.DataFrame(comparison_data)
        st.dataframe(df_comparison, use_container_width=True, hide_index=True)
        
        # Detailed results for each model
        st.markdown("---")
        st.subheader("📋 Detailed Results")
        
        for mr in test_result.model_results:
            with st.expander(
                f"{'✅' if mr.success else '❌'} {mr.model_name} ({mr.model_provider}) - "
                f"Score: {mr.overall_score:.1%}",
                expanded=False
            ):
                # Overall scores with visual indicators
                st.markdown("#### Scores")
                col_score1, col_score2, col_score3 = st.columns(3)
                
                with col_score1:
                    st.metric("Overall", f"{mr.overall_score:.1%}")
                    st.progress(mr.overall_score)
                
                with col_score2:
                    st.metric("Required Fields", f"{mr.required_fields_score:.1%}")
                    st.progress(mr.required_fields_score)
                
                with col_score3:
                    st.metric("Optional Fields", f"{mr.optional_fields_score:.1%}")
                    st.progress(mr.optional_fields_score)
                
                # Execution info
                st.markdown("#### Execution Details")
                col_exec1, col_exec2 = st.columns(2)
                
                with col_exec1:
                    st.text(f"Execution Time: {mr.execution_time:.2f}s")
                    st.text(f"Iterations: {mr.iterations}")
                    st.text(f"Success: {'✅ Yes' if mr.success else '❌ No'}")
                
                with col_exec2:
                    if mr.error_message:
                        st.error(f"Error: {mr.error_message}")
                    else:
                        st.success("No errors")
                
                # Field-by-field results
                st.markdown("#### Field Validation Results")
                
                # Required fields
                st.markdown("**Required Fields**")
                required_fields = [exp for exp in baseline.required_fields]
                
                for field_exp in required_fields:
                    field_result = mr.field_results.get(field_exp.field_name)
                    if field_result:
                        display_field_match_details(field_result, field_exp)
                
                # Optional fields
                if baseline.optional_fields:
                    st.markdown("**Optional Fields**")
                    optional_fields = [exp for exp in baseline.optional_fields]
                    
                    optional_results = []
                    for field_exp in optional_fields:
                        field_result = mr.field_results.get(field_exp.field_name)
                        if field_result and field_result.actual_value is not None:
                            actual_display = str(field_result.actual_value)
                            if len(actual_display) > 50:
                                actual_display = actual_display[:47] + "..."
                            optional_results.append({
                                "Field": field_exp.field_name,
                                "Value": actual_display,
                                "Confidence": f"{field_result.confidence:.1%}",
                                "Match": "✅" if field_result.is_match else "❌"
                            })
                    
                    if optional_results:
                        df_optional = pd.DataFrame(optional_results)
                        st.dataframe(df_optional, use_container_width=True, hide_index=True)
                    else:
                        st.info("No optional fields extracted")
        
        # Side-by-side field comparison
        st.markdown("---")
        st.subheader("🔍 Side-by-Side Field Comparison")
        
        # Create comparison table for required fields
        st.markdown("### Required Fields Comparison")
        
        required_comparison_data = []
        for field_exp in baseline.required_fields:
            row = {
                "Field": field_exp.field_name,
                "Match Type": field_exp.match_type.value,
                "Expected": str(field_exp.expected_value) if field_exp.expected_value else "N/A"
            }
            
            for mr in test_result.model_results:
                field_result = mr.field_results.get(field_exp.field_name)
                if field_result:
                    actual_value = str(field_result.actual_value) if field_result.actual_value is not None else "N/A"
                    confidence = field_result.confidence
                    status = "✅" if field_result.is_match else "❌"
                    row[mr.model_name] = f"{status} {actual_value[:40]} ({confidence:.0%})"
                else:
                    row[mr.model_name] = "N/A"
            
            required_comparison_data.append(row)
        
        if required_comparison_data:
            df_required_comp = pd.DataFrame(required_comparison_data)
            st.dataframe(df_required_comp, use_container_width=True, hide_index=True)
        
        # Export functionality
        st.markdown("---")
        st.subheader("💾 Export Results")
        
        col_export1, col_export2 = st.columns(2)
        
        with col_export1:
            # JSON export
            json_data = {
                "test_name": test_result.test_name,
                "company": baseline.company_name,
                "execution_time": test_result.execution_time,
                "average_score": test_result.average_score,
                "best_model": test_result.best_model,
                "model_results": [
                    {
                        "model_name": mr.model_name,
                        "provider": mr.model_provider,
                        "overall_score": mr.overall_score,
                        "required_fields_score": mr.required_fields_score,
                        "optional_fields_score": mr.optional_fields_score,
                        "success": mr.success,
                        "execution_time": mr.execution_time,
                        "iterations": mr.iterations,
                        "field_results": {
                            field_name: {
                                "is_match": fr.is_match,
                                "confidence": fr.confidence,
                                "expected": str(fr.expected_value),
                                "actual": str(fr.actual_value) if fr.actual_value is not None else None,
                                "match_type": fr.match_type,
                            }
                            for field_name, fr in mr.field_results.items()
                        }
                    }
                    for mr in test_result.model_results
                ]
            }
            
            st.download_button(
                label="📥 Download JSON",
                data=json.dumps(json_data, indent=2),
                file_name=f"test_results_{test_result.test_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col_export2:
            # CSV export (summary only)
            csv_data = []
            for mr in test_result.model_results:
                csv_data.append({
                    "Model": mr.model_name,
                    "Provider": mr.model_provider,
                    "Overall Score": mr.overall_score,
                    "Required Fields Score": mr.required_fields_score,
                    "Optional Fields Score": mr.optional_fields_score,
                    "Success": mr.success,
                    "Execution Time (s)": mr.execution_time,
                    "Iterations": mr.iterations,
                })
            
            df_csv = pd.DataFrame(csv_data)
            csv_string = df_csv.to_csv(index=False)
            
            st.download_button(
                label="📥 Download CSV",
                data=csv_string,
                file_name=f"test_results_{test_result.test_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        # Save results to database (for historical tracking)
        for mr in test_result.model_results:
            try:
                # Find the model config ID
                model_config = next(
                    (m for m in selected_models if m["name"] == mr.model_name),
                    None
                )
                
                if model_config and mr.company_info:
                    company_info_dict = mr.company_info.model_dump()
                    
                    # Count successful required fields
                    required_passed = sum(
                        1 for field_exp in baseline.required_fields
                        if (field_result := mr.field_results.get(field_exp.field_name))
                        and field_result.is_match
                    )
                    
                    save_test_execution(
                        test_name="bitmovin_research",  # Match database schema
                        test_company=baseline.company_name,
                        model_configuration_id=model_config.get("config_id"),
                        model_name=mr.model_name,
                        model_provider=mr.model_provider,
                        success=mr.success,
                        required_fields_valid=required_passed == len(baseline.required_fields),
                        execution_time_seconds=mr.execution_time,
                        iterations=mr.iterations,
                        extracted_company_info=company_info_dict,
                        raw_output=mr.raw_output[:1000] if mr.raw_output else None,
                        error_message=mr.error_message,
                        session=session,
                    )
            except Exception as e:
                st.warning(f"Failed to save results for {mr.model_name}: {e}")
    
    except Exception as e:
        progress_bar.progress(1.0)
        status_text.text("❌ Test execution failed")
        st.error(f"Error running tests: {e}")
        import traceback
        st.code(traceback.format_exc())

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
            "Time": f"{test.execution_time_seconds:.2f}s" if test.execution_time_seconds else "N/A",
            "Iterations": test.iterations or 0,
            "Date": test.created_at.strftime("%Y-%m-%d %H:%M:%S") if test.created_at else "N/A",
        })
    
    st.dataframe(pd.DataFrame(test_data), use_container_width=True, hide_index=True)
else:
    st.info("No test results yet. Run tests above to see results.")
