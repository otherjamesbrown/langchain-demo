#!/usr/bin/env python3
"""
LLM Dashboard - Home Page

Multi-page Streamlit application for LLM research and monitoring.

Pages are automatically discovered from the pages/ directory:
- 1_🤖_Local_LLM.py -> http://host:8501/Local_LLM
- 2_📊_Monitoring.py -> http://host:8501/Monitoring
- 3_🔬_Agent.py -> http://host:8501/Agent
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Change to project directory so imports work correctly
import os
os.chdir(project_root)

import streamlit as st

# Dashboard version
DASHBOARD_VERSION = "1.4.0"

# Page config
st.set_page_config(
    page_title="LLM Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Main content
st.title("🤖 LLM Research & Monitoring Dashboard")
st.markdown(f"**Version {DASHBOARD_VERSION}**")

st.markdown("---")

st.markdown("""
Welcome to the LLM Dashboard! This application provides tools for local LLM interaction,
monitoring, and research agent execution.

## Available Pages

Use the sidebar to navigate between pages:

### 🤖 Local LLM
- Interactively call your local LLM
- Real-time token usage metrics
- Response history tracking
- Automatic database logging

**URL:** `/Local_LLM`

### 📊 Monitoring
- View LLM call logs and statistics
- Track token usage and performance
- Filter by model type and time range
- Detailed call inspection

**URL:** `/Monitoring`

### 🔬 Agent
- Execute research agent on multiple companies
- Real-time execution stage visualization
- Configure model type and iterations
- Results summary with metrics

**URL:** `/Agent`

## Quick Start

1. **Select a page** from the sidebar navigation
2. **Configure settings** in the sidebar for each page
3. **Execute tasks** and view results in real-time

## Features

- ✅ Multi-page architecture with clean URLs
- ✅ Persistent database for logging
- ✅ Real-time metrics and monitoring
- ✅ Support for local and remote LLMs
- ✅ Research agent with ReAct framework
- ✅ Interactive dashboards

## System Information

""")

# System info
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Dashboard Version", DASHBOARD_VERSION)

with col2:
    try:
        from src.database.schema import get_session, create_database
        create_database()
        session = get_session()
        st.metric("Database", "✅ Connected")
        session.close()
    except Exception as e:
        st.metric("Database", "❌ Error")

with col3:
    import platform
    st.metric("Platform", platform.system())

st.markdown("---")

st.markdown("""
## Documentation

- [Architecture Overview](../../docs/ARCHITECTURE.md)
- [Streamlit Workflow](../../docs/STREAMLIT_WORKFLOW.md)
- [LLM Logging Guide](../../docs/LLM_LOGGING_GUIDE.md)

## Support

For issues or questions, please refer to the project documentation or contact the development team.
""")

# Sidebar
with st.sidebar:
    st.markdown("---")
    st.caption(f"Dashboard v{DASHBOARD_VERSION}")
    st.caption("Multi-page Streamlit App")
