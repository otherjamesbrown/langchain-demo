#!/usr/bin/env python3
"""
LLM Output Validation Page

Run LLM output validation tests with prompt versioning, view results,
and compare prompt versions through the Streamlit UI.

URL: http://host:8501/🧪_LLM_Output_Validation
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
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.utils.streamlit_helpers import init_streamlit_db
from src.database.schema import get_session
from src.prompts.prompt_manager import PromptManager
from src.testing.llm_output_validation_runner import LLMOutputValidationRunner
from src.testing.prompt_analytics import PromptAnalytics
from src.utils.model_availability import get_available_models


def get_prompt_versions(session) -> List[Dict[str, Any]]:
    """Get list of available prompt versions."""
    try:
        # Get all prompt names
        from src.database.schema import PromptVersion
        prompt_versions = session.query(PromptVersion).order_by(
            PromptVersion.prompt_name,
            PromptVersion.created_at.desc()
        ).all()
        
        versions = []
        for pv in prompt_versions:
            versions.append({
                'id': pv.id,
                'prompt_name': pv.prompt_name,
                'version': pv.version,
                'description': pv.description,
                'is_active': pv.is_active,
                'created_at': pv.created_at,
                'display': f"{pv.prompt_name} v{pv.version}" + (" (active)" if pv.is_active else "")
            })
        
        return versions
    except Exception as e:
        st.error(f"Error loading prompt versions: {e}")
        return []


def format_accuracy_score(score: Optional[float]) -> str:
    """Format accuracy score with color indicator."""
    if score is None:
        return "N/A"
    
    percentage = score
    if percentage >= 80:
        return f"✅ {percentage:.1f}%"
    elif percentage >= 50:
        return f"⚠️ {percentage:.1f}%"
    else:
        return f"❌ {percentage:.1f}%"


def display_test_results(result: dict) -> None:
    """Display test run results."""
    st.subheader("📊 Test Results")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Test Run ID", result.get('test_run_id', 'N/A'))
    with col2:
        st.metric("Company", result.get('company_name', 'N/A'))
    with col3:
        st.metric("Models Tested", result.get('other_outputs_count', 0))
    with col4:
        st.metric("Grading Results", result.get('grading_results_count', 0))
    
    # Accuracy scores
    if result.get('aggregate_stats'):
        stats = result['aggregate_stats']
        st.subheader("📈 Accuracy Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_overall = stats.get('average_overall_accuracy')
            st.metric("Overall Accuracy", format_accuracy_score(avg_overall))
        
        with col2:
            avg_required = stats.get('average_required_fields_accuracy')
            st.metric("Required Fields", format_accuracy_score(avg_required))
        
        with col3:
            avg_optional = stats.get('average_optional_fields_accuracy')
            st.metric("Optional Fields", format_accuracy_score(avg_optional))
        
        with col4:
            avg_weighted = stats.get('average_weighted_accuracy')
            st.metric("Weighted Accuracy", format_accuracy_score(avg_weighted))
        
        # Cost information
        if stats.get('total_grading_cost'):
            st.subheader("💰 Cost Information")
            st.info(f"Total Grading Cost: ${stats['total_grading_cost']:.6f}")
    
    st.success("✅ Test completed successfully!")


def display_comparison(comparison: List[Dict[str, Any]]) -> None:
    """Display prompt version comparison."""
    if not comparison:
        st.info("No comparison data available. Run some tests first!")
        return
    
    st.subheader("📊 Prompt Version Comparison")
    
    # Create comparison DataFrame
    comparison_data = []
    for version_data in comparison:
        comparison_data.append({
            'Version': version_data['prompt_version'],
            'Test Runs': version_data['test_runs_count'],
            'Overall Accuracy': version_data.get('average_overall_accuracy'),
            'Required Fields': version_data.get('average_required_fields_accuracy'),
            'Optional Fields': version_data.get('average_optional_fields_accuracy'),
            'Weighted': version_data.get('average_weighted_accuracy'),
            'Companies': ', '.join(version_data['companies_tested']),
        })
    
    df = pd.DataFrame(comparison_data)
    
    # Format accuracy columns
    for col in ['Overall Accuracy', 'Required Fields', 'Optional Fields', 'Weighted']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"{x:.1f}%" if x is not None else "N/A")
    
    st.dataframe(df, use_container_width=True)
    
    # Show best version
    best = max(
        [v for v in comparison if v.get('average_overall_accuracy') is not None],
        key=lambda x: x.get('average_overall_accuracy', 0),
        default=None
    )
    if best:
        st.success(f"🏆 Best Version: {best['prompt_version']} "
                   f"({best.get('average_overall_accuracy', 0):.1f}% accuracy)")


def display_cost_analysis(cost_analysis: Dict[str, Any]) -> None:
    """Display cost analysis."""
    st.subheader("💰 Cost Analysis")
    
    total = cost_analysis['total']
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Cost", f"${total['total_cost']:.6f}")
    with col2:
        st.metric("Agent Cost", f"${total['agent_cost']:.6f}")
    with col3:
        st.metric("Grading Cost", f"${total['grading_cost']:.6f}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Tokens", f"{total['total_tokens']:,}")
    with col2:
        st.metric("Outputs", f"{total['outputs_count']}")
    
    # By prompt version
    if cost_analysis['by_prompt_version']:
        st.subheader("📌 By Prompt Version")
        version_data = []
        for version, stats in cost_analysis['by_prompt_version'].items():
            version_data.append({
                'Version': version,
                'Agent Cost': f"${stats['agent_cost']:.6f}",
                'Grading Cost': f"${stats['grading_cost']:.6f}",
                'Total Cost': f"${stats['agent_cost'] + stats['grading_cost']:.6f}",
                'Agent Tokens': f"{stats['agent_tokens']:,}",
                'Grading Tokens': f"{stats['grading_tokens']:,}",
            })
        st.dataframe(pd.DataFrame(version_data), use_container_width=True)
    
    # By company
    if cost_analysis['by_company']:
        st.subheader("🏢 By Company")
        company_data = []
        for company, stats in cost_analysis['by_company'].items():
            company_data.append({
                'Company': company,
                'Agent Cost': f"${stats['agent_cost']:.6f}",
                'Grading Cost': f"${stats['grading_cost']:.6f}",
                'Total Cost': f"${stats['agent_cost'] + stats['grading_cost']:.6f}",
            })
        st.dataframe(pd.DataFrame(company_data), use_container_width=True)


# Page config
st.set_page_config(
    page_title="LLM Output Validation",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 LLM Output Validation")

# Initialize database
session = init_streamlit_db()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Run Test", "Compare Versions", "Cost Analysis", "Review Test"])

# Tab 1: Run Test
with tab1:
    st.header("Run Validation Test")
    
    # Get prompt versions
    prompt_versions = get_prompt_versions(session)
    
    if not prompt_versions:
        st.warning("⚠️ No prompt versions found. Please initialize prompts first using `scripts/initialize_prompts.py`")
    else:
        # Prompt selection
        prompt_options = {v['display']: v for v in prompt_versions}
        selected_prompt_display = st.selectbox(
            "Select Prompt Version",
            options=list(prompt_options.keys()),
            help="Select the prompt version to use for testing"
        )
        selected_prompt = prompt_options[selected_prompt_display]
        
        # Company input
        company_name = st.text_input(
            "Company Name",
            value="BitMovin",
            help="Enter the company name to test"
        )
        
        # Test suite name (optional)
        test_suite_name = st.text_input(
            "Test Suite Name (optional)",
            value="",
            help="Optional: Group this test run with others in a test suite"
        )
        
        # Test run description
        test_run_description = st.text_input(
            "Test Run Description (optional)",
            value="",
            help="Optional: Description for this test run"
        )
        
        # Max iterations
        max_iterations = st.number_input(
            "Max Iterations",
            min_value=1,
            max_value=20,
            value=10,
            help="Maximum agent iterations"
        )
        
        # Force refresh
        force_refresh = st.checkbox(
            "Force Refresh Ground Truth",
            value=False,
            help="Force regeneration of ground truth even if cached"
        )
        
        # Run button
        if st.button("🚀 Run Test", type="primary"):
            if not company_name:
                st.error("Please enter a company name")
            else:
                with st.spinner("Running test... This may take a few minutes."):
                    try:
                        # Get available models
                        available_models = get_available_models(session=session, include_reasons=False)
                        
                        # Initialize runner
                        runner = LLMOutputValidationRunner(
                            prompt_version_id=selected_prompt['id'],
                            test_run_description=test_run_description or None,
                        )
                        
                        # Get Gemini Pro model name
                        gemini_pro_model_name = runner.gemini_pro_model_name
                        
                        # Filter out Gemini Pro from other models
                        from src.database.schema import ModelConfiguration
                        other_models = []
                        for model_dict in available_models:
                            if (model_dict['provider'] == 'gemini' and 
                                model_dict.get('api_identifier') == gemini_pro_model_name):
                                continue
                            
                            config = session.query(ModelConfiguration).filter(
                                ModelConfiguration.id == model_dict["config_id"]
                            ).first()
                            if config:
                                other_models.append(config)
                        
                        # Run test
                        result = runner.run_test(
                            company_name=company_name,
                            other_models=other_models if other_models else None,
                            force_refresh=force_refresh,
                            max_iterations=max_iterations,
                            test_suite_name=test_suite_name or None,
                        )
                        
                        if result.get("success"):
                            display_test_results(result)
                        else:
                            st.error(f"❌ Test failed: {result.get('error', 'Unknown error')}")
                    
                    except Exception as e:
                        st.error(f"❌ Error running test: {e}")
                        import traceback
                        st.code(traceback.format_exc())

# Tab 2: Compare Versions
with tab2:
    st.header("Compare Prompt Versions")
    
    # Get prompt name
    prompt_names = list(set([v['prompt_name'] for v in prompt_versions]))
    
    if not prompt_names:
        st.warning("⚠️ No prompts found. Please initialize prompts first.")
    else:
        selected_prompt_name = st.selectbox(
            "Select Prompt",
            options=prompt_names,
            help="Select the prompt to compare versions for"
        )
        
        company_filter = st.text_input(
            "Filter by Company (optional)",
            value="",
            help="Optional: Filter comparison by specific company"
        )
        
        if st.button("📊 Compare Versions"):
            with st.spinner("Loading comparison..."):
                try:
                    comparison = PromptAnalytics.compare_prompt_versions(
                        prompt_name=selected_prompt_name,
                        company_name=company_filter or None
                    )
                    display_comparison(comparison)
                except Exception as e:
                    st.error(f"❌ Error loading comparison: {e}")
                    import traceback
                    st.code(traceback.format_exc())

# Tab 3: Cost Analysis
with tab3:
    st.header("Cost Analysis")
    
    if not prompt_names:
        st.warning("⚠️ No prompts found. Please initialize prompts first.")
    else:
        selected_prompt_name = st.selectbox(
            "Select Prompt (for cost analysis)",
            options=prompt_names,
            key="cost_prompt",
            help="Select the prompt to analyze costs for"
        )
        
        company_filter = st.text_input(
            "Filter by Company (optional)",
            value="",
            key="cost_company",
            help="Optional: Filter cost analysis by specific company"
        )
        
        if st.button("💰 Show Cost Analysis"):
            with st.spinner("Loading cost analysis..."):
                try:
                    cost_analysis = PromptAnalytics.get_cost_analysis(
                        prompt_name=selected_prompt_name,
                        company_name=company_filter or None
                    )
                    display_cost_analysis(cost_analysis)
                except Exception as e:
                    st.error(f"❌ Error loading cost analysis: {e}")
                    import traceback
                    st.code(traceback.format_exc())

# Tab 4: Review Test
with tab4:
    st.header("Review Test")
    
    # Get all test runs for dropdown
    from src.database.schema import TestRun, LLMOutputValidation, LLMOutputValidationResult
    
    test_runs = session.query(TestRun).order_by(
        TestRun.created_at.desc()
    ).all()
    
    if not test_runs:
        st.warning("⚠️ No test runs found. Run some tests first!")
    else:
        # Create dropdown options with descriptive labels
        test_run_options = {}
        for tr in test_runs:
            # Create descriptive label
            date_str = tr.created_at.strftime("%Y-%m-%d %H:%M") if tr.created_at else "Unknown"
            label = f"Run #{tr.id} - {tr.company_name} ({tr.prompt_name}@{tr.prompt_version}) - {date_str}"
            test_run_options[label] = tr.id
        
        selected_label = st.selectbox(
            "Select Test Run",
            options=list(test_run_options.keys()),
            help="Select a test run to review its results"
        )
        
        selected_test_run_id = test_run_options[selected_label]
        
        if selected_test_run_id:
            with st.spinner("Loading test run data..."):
                try:
                    # Get the test run
                    test_run = session.query(TestRun).filter(
                        TestRun.id == selected_test_run_id
                    ).first()
                    
                    if not test_run:
                        st.error(f"Test run {selected_test_run_id} not found")
                    else:
                        # Display test run info
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Company", test_run.company_name)
                        with col2:
                            st.metric("Prompt", f"{test_run.prompt_name}@{test_run.prompt_version}")
                        with col3:
                            st.metric("Test Run ID", test_run.id)
                        
                        # Get all outputs for this test run
                        all_outputs = session.query(LLMOutputValidation).filter(
                            LLMOutputValidation.test_run_id == selected_test_run_id
                        ).all()
                        
                        if not all_outputs:
                            st.info("No outputs found for this test run.")
                        else:
                            # Get Gemini Pro model name (for identifying ground truth)
                            runner = LLMOutputValidationRunner()
                            gemini_pro_model_name = runner.gemini_pro_model_name
                            
                            # Find ground truth (Gemini Pro output)
                            ground_truth_output = None
                            other_outputs = []
                            
                            for output in all_outputs:
                                if output.model_name == gemini_pro_model_name and output.model_provider == "gemini":
                                    ground_truth_output = output
                                else:
                                    other_outputs.append(output)
                            
                            if not ground_truth_output:
                                st.warning("⚠️ Ground truth (Gemini Pro) output not found for this test run.")
                            else:
                                # Get grading results for other outputs
                                grading_results = {}
                                for output in other_outputs:
                                    result = session.query(LLMOutputValidationResult).filter(
                                        LLMOutputValidationResult.output_id == output.id,
                                        LLMOutputValidationResult.test_run_id == selected_test_run_id
                                    ).first()
                                    
                                    if result:
                                        grading_results[output.id] = {
                                            'output': output,
                                            'result': result,
                                            'model_name': output.model_name,
                                            'model_provider': output.model_provider
                                        }
                                
                                # Define all CompanyInfo fields (questions)
                                # These match the LLMOutputValidation schema columns
                                field_mapping = {
                                    'company_name_field': 'Company Name',
                                    'industry': 'Industry',
                                    'company_size': 'Company Size',
                                    'headquarters': 'Headquarters',
                                    'founded': 'Founded',
                                    'description': 'Description',
                                    'website': 'Website',
                                    'products': 'Products',
                                    'competitors': 'Competitors',
                                    'revenue': 'Revenue',
                                    'funding_stage': 'Funding Stage',
                                    'growth_stage': 'Growth Stage',
                                    'industry_vertical': 'Industry Vertical',
                                    'sub_industry_vertical': 'Sub-Industry Vertical',
                                    'financial_health': 'Financial Health',
                                    'business_and_technology_adoption': 'Business & Technology Adoption',
                                    'primary_workload_philosophy': 'Primary Workload Philosophy',
                                    'buyer_journey': 'Buyer Journey',
                                    'budget_maturity': 'Budget Maturity',
                                    'cloud_spend_capacity': 'Cloud Spend Capacity',
                                    'procurement_process': 'Procurement Process',
                                    'key_personas': 'Key Personas',
                                }
                                
                                # Build table data
                                table_data = []
                                
                                for field_key, field_label in field_mapping.items():
                                    # Get ground truth value
                                    ground_truth_value = getattr(ground_truth_output, field_key, None)
                                    
                                    # Format ground truth value
                                    if ground_truth_value is None:
                                        gt_display = "N/A"
                                    elif isinstance(ground_truth_value, list):
                                        gt_display = ", ".join(str(v) for v in ground_truth_value) if ground_truth_value else "N/A"
                                    else:
                                        gt_display = str(ground_truth_value)
                                    
                                    # Start row with question and ground truth
                                    row = {
                                        'Question': field_label,
                                        'Ground Truth': gt_display
                                    }
                                    
                                    # Add columns for each model output
                                    for output_id, grading_data in grading_results.items():
                                        output = grading_data['output']
                                        result = grading_data['result']
                                        model_name = grading_data['model_name']
                                        
                                        # Get model's answer
                                        model_answer = getattr(output, field_key, None)
                                        
                                        # Format model answer
                                        if model_answer is None:
                                            answer_display = "N/A"
                                        elif isinstance(model_answer, list):
                                            answer_display = ", ".join(str(v) for v in model_answer) if model_answer else "N/A"
                                        else:
                                            answer_display = str(model_answer)
                                        
                                        # Get accuracy for this field from field_accuracy_scores
                                        field_scores = result.field_accuracy_scores or {}
                                        field_score_data = field_scores.get(field_key, {})
                                        accuracy = field_score_data.get('score', None)
                                        
                                        # Format accuracy
                                        if accuracy is not None:
                                            accuracy_display = f"{accuracy:.1f}%"
                                        else:
                                            accuracy_display = "N/A"
                                        
                                        # Create column names for this model
                                        answer_col = f"{model_name} - Answer"
                                        accuracy_col = f"{model_name} - Accuracy"
                                        
                                        row[answer_col] = answer_display
                                        row[accuracy_col] = accuracy_display
                                    
                                    table_data.append(row)
                                
                                # Display table
                                if table_data:
                                    df = pd.DataFrame(table_data)
                                    st.dataframe(df, use_container_width=True, hide_index=True)
                                else:
                                    st.info("No data to display.")
                                
                                # Show summary stats
                                if grading_results:
                                    st.subheader("📊 Summary")
                                    summary_cols = st.columns(min(len(grading_results), 4))
                                    
                                    for idx, (output_id, grading_data) in enumerate(grading_results.items()):
                                        if idx < len(summary_cols):
                                            with summary_cols[idx]:
                                                result = grading_data['result']
                                                model_name = grading_data['model_name']
                                                
                                                st.metric(
                                                    f"{model_name} Overall",
                                                    f"{result.overall_accuracy:.1f}%" if result.overall_accuracy else "N/A"
                                                )
                                
                except Exception as e:
                    st.error(f"❌ Error loading test run: {e}")
                    import traceback
                    st.code(traceback.format_exc())

