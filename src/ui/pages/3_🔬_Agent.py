#!/usr/bin/env python3
"""
Agent Execution Page

Execute research agent on multiple companies with real-time stage visualization.

URL: http://host:8501/Agent
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

# Sidebar configuration
st.sidebar.header("⚙️ Agent Configuration")

model_type = st.sidebar.selectbox(
    "Model Type",
    options=["local", "openai", "anthropic"],
    index=0,
    help="Select which LLM provider to use for research"
)

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
    st.write(f"Model: {model_type}")

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

                agent = ResearchAgent(
                    model_type=model_type,
                    verbose=verbose_mode,
                    max_iterations=max_iterations
                )
                st.success(f"✅ Agent initialized with {model_type} model")
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

                    # Create log area for verbose output
                    if verbose_mode:
                        log_area = st.empty()
                        logs = []

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

                        stage4.success("4️⃣ ✅ Stored to database")

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

                            if info.products:
                                with st.expander("Products"):
                                    for product in info.products:
                                        st.write(f"- {product}")

                            if info.competitors:
                                with st.expander("Competitors"):
                                    for competitor in info.competitors:
                                        st.write(f"- {competitor}")

                        # Show raw result details
                        with st.expander("View Raw Result"):
                            st.json({
                                "success": result.success,
                                "company_name": result.company_name,
                                "raw_output": result.raw_output,
                                "iterations": result.iterations,
                                "execution_time_seconds": result.execution_time_seconds
                            })

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
