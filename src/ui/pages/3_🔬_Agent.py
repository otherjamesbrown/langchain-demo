#!/usr/bin/env python3
"""
Agent Execution Page

Execute research agent on multiple companies with real-time stage visualization.

URL: http://host:8501/Agent
"""

import sys
from pathlib import Path
import json

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
    save_company_info,
    ensure_default_configuration,
    get_model_configurations,
    get_last_used_model,
    set_last_used_model,
)
from src.utils.llm_logger import log_llm_call
from src.utils.metrics import LLMMetrics

# Page config
st.set_page_config(
    page_title="Agent - Dashboard",
    page_icon="🔬",
    layout="wide"
)

# Initialize database
@st.cache_resource
def init_db():
    """Initialize database connection."""
    create_database()
    return get_session()

# Main page
st.title("🔬 Agent Execution")
st.markdown("Execute the research agent on companies and monitor progress in real-time")

# Initialize database
try:
    session = init_db()
except Exception as e:
    st.error(f"Failed to connect to database: {e}")
    st.stop()

ensure_default_configuration(session=session)

# Sidebar configuration
st.sidebar.header("⚙️ Agent Configuration")

configured_models = get_model_configurations(session=session)

if not configured_models:
    st.sidebar.error("No models configured. Use the Home page to add model entries before running the agent.")
    st.stop()

last_used = get_last_used_model(session=session)
default_index = 0
if last_used is not None:
    for idx, model in enumerate(configured_models):
        if model.id == last_used.id:
            default_index = idx
            break

selected_model_name = st.sidebar.selectbox(
    "Model",
    options=[model.name for model in configured_models],
    index=default_index,
    help="Select which model configuration the agent should use.",
)

selected_model = next(model for model in configured_models if model.name == selected_model_name)
if last_used is None or last_used.id != selected_model.id:
    set_last_used_model(selected_model.id, session=session)

model_type = selected_model.provider
local_model_path: Path | None = None
local_model_key: str | None = None
model_kwargs: dict[str, str] = {}

if selected_model.provider == "local":
    if selected_model.model_path:
        local_model_path = Path(selected_model.model_path).expanduser()
        if not local_model_path.exists():
            st.sidebar.error(
                f"Model file missing: {local_model_path}. Update the model configuration on the Home page."
            )
            st.stop()
    else:
        st.sidebar.error("Selected local model does not have a path configured. Update it on the Home page.")
        st.stop()
    local_model_key = selected_model.model_key or selected_model.name
else:
    if selected_model.api_identifier:
        model_kwargs["model_name"] = selected_model.api_identifier

metadata = selected_model.extra_metadata or {}
st.sidebar.caption(f"Provider: `{selected_model.provider}`")
if selected_model.model_path:
    st.sidebar.caption(f"Path: `{selected_model.model_path}`")
if selected_model.api_identifier:
    st.sidebar.caption(f"Model Identifier: `{selected_model.api_identifier}`")
if metadata.get("description"):
    st.sidebar.info(metadata["description"])
elif selected_model.provider == "local" and not selected_model.model_path:
    st.sidebar.info("Configure the model path from the Home page to use this entry.")

max_iterations = st.sidebar.slider(
    "Max Iterations",
    min_value=1,
    max_value=20,
    value=10,
    help="Maximum reasoning iterations for the agent"
)

verbose_mode = st.sidebar.checkbox(
    "Verbose Output",
    value=True,
    help="Show detailed agent reasoning steps"
)

# Main interface
st.subheader("📋 Company List")
st.markdown("Enter company names, one per line:")

# Default company list
default_companies = """BitMovin
Hydrolix
Queue-it"""

companies_text = st.text_area(
    "Companies",
    value=default_companies,
    height=200,
    placeholder="Enter company names, one per line...",
    label_visibility="collapsed"
)

# Parse companies from text
companies = [c.strip() for c in companies_text.split('\n') if c.strip()]

if companies:
    st.info(f"📊 {len(companies)} companies loaded")
    with st.expander("View company list"):
        for i, company in enumerate(companies, 1):
            st.write(f"{i}. {company}")

st.divider()

# Execution controls
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    execute_button = st.button("🚀 Execute Agent", type="primary", use_container_width=True)

with col2:
    if st.button("🗑️ Clear Results", use_container_width=True):
        if "agent_results" in st.session_state:
            del st.session_state.agent_results
        if "agent_logs" in st.session_state:
            del st.session_state.agent_logs
        st.rerun()

with col3:
    st.write(f"Model: {selected_model.name}")
    st.caption(f"Provider: {selected_model.provider}")

# Initialize session state
if "agent_results" not in st.session_state:
    st.session_state.agent_results = {}
if "agent_logs" not in st.session_state:
    st.session_state.agent_logs = {}

# Execute agent when button is clicked
if execute_button:
    if not companies:
        st.warning("⚠️ Please enter at least one company name")
    else:
        st.divider()
        st.header("🔄 Execution Progress")

        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Load agent
        with st.spinner("Loading research agent..."):
            try:
                from src.agent.research_agent import ResearchAgent

                model_path_str = str(local_model_path) if local_model_path else None
                agent = ResearchAgent(
                    model_type=model_type,
                    verbose=verbose_mode,
                    max_iterations=max_iterations,
                    local_model=local_model_key if model_type == "local" else None,
                    model_path=model_path_str,
                    model_kwargs=model_kwargs,
                )
                if model_type == "local":
                    st.success(
                        "✅ Agent initialized with local model: "
                        f"{selected_model.name}"
                    )
                else:
                    model_label = selected_model.api_identifier or selected_model.name
                    st.success(
                        "✅ Agent initialized with "
                        f"{selected_model.provider.title()} model: {model_label}"
                    )
            except Exception as e:
                st.error(f"❌ Failed to initialize agent: {e}")
                st.code(str(e))
                st.stop()

        # Process each company
        for idx, company in enumerate(companies):
            status_text.text(f"Processing {idx + 1}/{len(companies)}: {company}")

            # Create expander for this company's execution
            with st.expander(f"🏢 {company}", expanded=True):
                stages_container = st.container()

                with stages_container:
                    st.write("**Execution Stages:**")

                    # Stage 1: Initialization
                    stage1 = st.empty()
                    stage1.info("1️⃣ Initializing research task...")

                    # Stage 2: Agent execution
                    stage2 = st.empty()
                    stage2.info("2️⃣ Running ReAct agent loop...")

                    if verbose_mode:
                        st.caption("Verbose logging enabled – capturing agent reasoning and tool usage.")

                    try:
                        # Execute research
                        start_time = time.time()

                        # Stage 1 complete
                        stage1.success("1️⃣ ✅ Research task initialized")

                        # Stage 2: Execute agent (this includes ReAct loop)
                        result = agent.research_company(company)

                        stage2.success("2️⃣ ✅ Agent execution complete")

                        # Stage 3: Parsing
                        stage3 = st.empty()
                        stage3.info("3️⃣ Parsing results...")

                        end_time = time.time()
                        execution_time = end_time - start_time

                        stage3.success("3️⃣ ✅ Results parsed")

                        # Stage 4: Database storage
                        stage4 = st.empty()
                        stage4.info("4️⃣ Storing to database...")

                        # Store result in session state
                        st.session_state.agent_results[company] = {
                            "result": result,
                            "execution_time": execution_time,
                            "timestamp": datetime.now()
                        }

                        if result.company_info:
                            try:
                                save_company_info(result.company_info, session=session)
                                stage4.success("4️⃣ ✅ Stored to database")
                            except Exception as db_error:
                                stage4.error("4️⃣ ❌ Failed to store in database")
                                st.error(f"Database error: {db_error}")
                        else:
                            stage4.warning("4️⃣ ⚠️ No structured company info to store")

                        # Log the run to LLM call history so we can analyse model usage.
                        model_display = result.model_display_name or selected_model.name
                        metadata = {
                            "company_name": company,
                            "iterations": result.iterations,
                            "success": result.success,
                            "execution_time_seconds": execution_time,
                            "source": "streamlit_agent_page",
                            "provider": selected_model.provider,
                            "model_configuration_id": selected_model.id,
                        }
                        if result.model_key:
                            metadata["model_key"] = result.model_key
                        if selected_model.model_path:
                            metadata["model_path"] = selected_model.model_path
                        if selected_model.api_identifier:
                            metadata["api_identifier"] = selected_model.api_identifier

                        try:
                            metrics = LLMMetrics(
                                prompt_tokens=0,
                                completion_tokens=0,
                                total_tokens=0,
                                generation_time=execution_time,
                                model_name=model_display,
                                model_type=model_type,
                            )
                            log_entry = log_llm_call(
                                metrics=metrics,
                                response=result.raw_output,
                                model_name=model_display,
                                call_type="agent_run",
                                metadata=metadata,
                                session=session,
                            )
                            if log_entry is not None:
                                session.commit()
                        except Exception as logging_error:  # noqa: BLE001
                            st.warning(f"⚠️ Failed to log agent run: {logging_error}")

                        # Display summary
                        st.divider()
                        st.write("**📊 Result Summary:**")

                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric("Status", "✅ Success")

                        with col2:
                            st.metric("Execution Time", f"{execution_time:.2f}s")

                        with col3:
                            if result.company_info:
                                st.metric("Fields Found", len([f for f in vars(result.company_info).values() if f]))
                            else:
                                st.metric("Fields Found", "N/A")

                        # Display company info if available
                        if result.company_info:
                            st.write("**Company Information:**")
                            info = result.company_info

                            if info.company_name:
                                st.write(f"**Name:** {info.company_name}")
                            if info.industry:
                                st.write(f"**Industry:** {info.industry}")
                            if info.website:
                                st.write(f"**Website:** {info.website}")
                            if info.description:
                                st.write(f"**Description:** {info.description}")
                            if info.company_size:
                                st.write(f"**Company Size:** {info.company_size}")
                            if info.headquarters:
                                st.write(f"**Headquarters:** {info.headquarters}")
                            if info.founded:
                                st.write(f"**Founded:** {info.founded}")

                            # Highlight core GTM classifications so learners see key signals upfront.
                            gtm_snapshot_fields = [
                                (
                                    "Growth Stage",
                                    info.growth_stage,
                                    info.growth_stage_reason,
                                ),
                                (
                                    "Company Size",
                                    info.company_size,
                                    info.company_size_reason,
                                ),
                                (
                                    "Industry Vertical",
                                    info.industry_vertical,
                                    info.industry_vertical_reason,
                                ),
                                (
                                    "Sub-Industry Vertical",
                                    info.sub_industry_vertical,
                                    info.sub_industry_vertical_reason,
                                ),
                                (
                                    "Financial Health",
                                    info.financial_health,
                                    info.financial_health_reason,
                                ),
                                (
                                    "Business & Technology Adoption",
                                    info.business_and_technology_adoption,
                                    info.business_and_technology_adoption_reason,
                                ),
                            ]

                            populated_snapshot_fields = [
                                (label, value, reason)
                                for label, value, reason in gtm_snapshot_fields
                                if value or reason
                            ]

                            if populated_snapshot_fields:
                                st.write("**Go-To-Market Snapshot:**")
                                snapshot_columns = st.columns(2)
                                for index, (label, value, reason) in enumerate(populated_snapshot_fields):
                                    target_column = snapshot_columns[index % len(snapshot_columns)]
                                    with target_column:
                                        st.markdown(
                                            f"**{label}:** {value or 'Not identified'}"
                                        )
                                        if reason:
                                            st.caption(f"Reasoning: {reason}")

                            if info.products:
                                with st.expander("Products"):
                                    for product in info.products:
                                        st.write(f"- {product}")

                            if info.competitors:
                                with st.expander("Competitors"):
                                    for competitor in info.competitors:
                                        st.write(f"- {competitor}")

                            gtm_fields = [
                                ("Growth Stage", info.growth_stage, info.growth_stage_reason),
                                (
                                    "Industry Vertical",
                                    info.industry_vertical,
                                    info.industry_vertical_reason,
                                ),
                                (
                                    "Sub-Industry Vertical",
                                    info.sub_industry_vertical,
                                    info.sub_industry_vertical_reason,
                                ),
                                ("Financial Health", info.financial_health, info.financial_health_reason),
                                (
                                    "Business & Technology Adoption",
                                    info.business_and_technology_adoption,
                                    info.business_and_technology_adoption_reason,
                                ),
                                (
                                    "Primary Workload Philosophy",
                                    info.primary_workload_philosophy,
                                    info.primary_workload_philosophy_reason,
                                ),
                                ("Buyer Journey", info.buyer_journey, info.buyer_journey_reason),
                                ("Budget Maturity", info.budget_maturity, info.budget_maturity_reason),
                                ("Cloud Spend Capacity", info.cloud_spend_capacity, info.cloud_spend_capacity_reason),
                                ("Procurement Process", info.procurement_process, info.procurement_process_reason),
                            ]

                            has_gtm_data = any(value for _, value, _ in gtm_fields) or bool(info.key_personas)

                            if has_gtm_data:
                                with st.expander("Go-To-Market Profiling"):
                                    for label, value, reason in gtm_fields:
                                        if not value and not reason:
                                            continue
                                        st.markdown(f"**{label}:** {value or 'Not identified'}")
                                        if reason:
                                            st.caption(f"Reasoning: {reason}")

                                    if info.key_personas:
                                        st.markdown("**Key Personas:**")
                                        for persona in info.key_personas:
                                            st.write(f"- {persona}")
                                        if info.key_personas_reason:
                                            st.caption(
                                                f"Why these personas matter: {info.key_personas_reason}"
                                            )

                        # Show raw result details
                        with st.expander("View Raw Result"):
                            st.json({
                                "success": result.success,
                                "company_name": result.company_name,
                                "raw_output": result.raw_output,
                                "iterations": result.iterations,
                                "execution_time_seconds": result.execution_time_seconds,
                                "model_input": result.model_input,
                            })

                        if verbose_mode and result.intermediate_steps:
                            with st.expander("🧠 Agent Reasoning & Tool Calls", expanded=False):
                                for step in result.intermediate_steps:
                                    step_type = step.get("type")
                                    iteration = step.get("iteration", "?")
                                    if step_type == "model":
                                        content = step.get("content", "").strip()
                                        if not content:
                                            content = "_No model content returned_"
                                        st.markdown(f"**Model Iteration {iteration}:**\n\n{content}")
                                    elif step_type == "tool":
                                        tool_name = step.get("tool_name", "unknown_tool")
                                        arguments = step.get("arguments", {}) or {}
                                        query_text = arguments.get("query") or arguments.get("input") or "(no query provided)"
                                        st.markdown(f"**Tool Call {iteration}: `{tool_name}`**")
                                        st.code(str(query_text), language="text")

                                        output_text = (step.get("output", "") or "").strip()
                                        raw_marker = "RAW_RESULTS_JSON:"
                                        formatted_text = output_text
                                        raw_json_text: str | None = None
                                        if raw_marker in output_text:
                                            formatted_text, raw_json_text = output_text.split(raw_marker, 1)
                                            formatted_text = formatted_text.strip()
                                            raw_json_text = raw_json_text.strip()

                                        if formatted_text:
                                            st.caption("Tool formatted response:")
                                            st.text(formatted_text[:1000] + ("…" if len(formatted_text) > 1000 else ""))

                                        if raw_json_text:
                                            st.caption("Raw provider response:")
                                            try:
                                                st.json(json.loads(raw_json_text))
                                            except json.JSONDecodeError:
                                                st.text(raw_json_text[:2000] + ("…" if len(raw_json_text) > 2000 else ""))
                                        elif not formatted_text:
                                            st.caption("Tool returned no content")

                    except Exception as e:
                        stage2.error("2️⃣ ❌ Agent execution failed")
                        st.error(f"❌ Error processing {company}: {e}")
                        st.code(str(e))

                        # Store error in session state
                        st.session_state.agent_results[company] = {
                            "error": str(e),
                            "execution_time": time.time() - start_time,
                            "timestamp": datetime.now()
                        }

            # Update progress bar
            progress_bar.progress((idx + 1) / len(companies))

        status_text.text("✅ All companies processed!")
        st.balloons()

# Display previous results summary
if st.session_state.agent_results:
    st.divider()
    st.header("📈 Results Summary")

    successful = sum(1 for r in st.session_state.agent_results.values() if "result" in r)
    failed = len(st.session_state.agent_results) - successful

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Processed", len(st.session_state.agent_results))

    with col2:
        st.metric("Successful", successful)

    with col3:
        st.metric("Failed", failed)

    with col4:
        avg_time = sum(r.get("execution_time", 0) for r in st.session_state.agent_results.values()) / len(st.session_state.agent_results)
        st.metric("Avg Time", f"{avg_time:.1f}s")

    # Results table
    st.subheader("Detailed Results")

    results_data = []
    for company, data in st.session_state.agent_results.items():
        results_data.append({
            "Company": company,
            "Status": "✅ Success" if "result" in data else "❌ Failed",
            "Time (s)": f"{data.get('execution_time', 0):.2f}",
            "Timestamp": data.get('timestamp', datetime.now()).strftime('%H:%M:%S'),
        })

    df = pd.DataFrame(results_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
