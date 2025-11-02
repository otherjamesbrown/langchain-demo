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
import pandas as pd

from src.database.operations import (
    ensure_default_configuration,
    get_model_configurations,
    get_last_used_model,
    set_last_used_model,
    get_api_key,
    upsert_api_key,
)
from src.database.schema import create_database

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


def _mask_key(value: str | None) -> str:
    """Return a shortened representation of a secret for display."""

    if not value:
        return "Not set"
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}***{value[-3:]}"

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
        create_database()
        ensure_default_configuration()
        st.metric("Database", "✅ Connected")
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
    ensure_default_configuration()
    configured_models = get_model_configurations()
    last_used_model = get_last_used_model()
    last_used_id = last_used_model.id if last_used_model else None

    if configured_models:
        option_labels = [model.name for model in configured_models]
        default_index = 0
        if last_used_id is not None:
            for idx, model in enumerate(configured_models):
                if model.id == last_used_id:
                    default_index = idx
                    break

        selected_name = st.selectbox(
            "Active Model",
            option_labels,
            index=default_index,
            help="Choose the model used by default across dashboard pages.",
        )

        active_model = next(model for model in configured_models if model.name == selected_name)
        if last_used_id != active_model.id:
            set_last_used_model(active_model.id)

        st.caption(f"Provider: `{active_model.provider}`")
        if active_model.model_path:
            st.caption(f"Model Path: `{active_model.model_path}`")
        if active_model.api_identifier:
            st.caption(f"API Identifier: `{active_model.api_identifier}`")

        metadata = active_model.extra_metadata or {}
        details: list[str] = []
        recommended = metadata.get("recommended_vram_gb")
        if recommended:
            details.append(f"Recommended VRAM: {recommended} GB")
        context_window = metadata.get("context_window")
        if context_window:
            details.append(f"Context Window: {context_window} tokens")
        description = metadata.get("description")
        if description:
            details.append(description)
        if details:
            st.info("\n".join(details))
    else:
        st.warning("No model configurations found. Use the instructions in docs to add models.")

    st.markdown("---")

    existing_keys = {
        "openai": get_api_key("openai"),
        "anthropic": get_api_key("anthropic"),
        "gemini": get_api_key("gemini"),
    }

    with st.expander("Manage API Credentials", expanded=False):
        st.caption("Credentials are stored in SQLite so all pages share the same configuration.")
        with st.form("api_credentials_form", clear_on_submit=False):
            openai_input = st.text_input(
                "OpenAI API Key",
                value=existing_keys["openai"] or "",
                type="password",
                help="Used when selecting OpenAI models.",
            )
            anthropic_input = st.text_input(
                "Anthropic API Key",
                value=existing_keys["anthropic"] or "",
                type="password",
                help="Used when selecting Anthropic models.",
            )
            gemini_input = st.text_input(
                "Gemini API Key",
                value=existing_keys["gemini"] or "",
                type="password",
                help="Used when selecting Gemini models.",
            )

            submitted = st.form_submit_button("Save API Keys")
            if submitted:
                if openai_input.strip():
                    upsert_api_key("openai", openai_input.strip())
                    existing_keys["openai"] = openai_input.strip()
                if anthropic_input.strip():
                    upsert_api_key("anthropic", anthropic_input.strip())
                    existing_keys["anthropic"] = anthropic_input.strip()
                if gemini_input.strip():
                    upsert_api_key("gemini", gemini_input.strip())
                    existing_keys["gemini"] = gemini_input.strip()
                st.success("API credentials updated")

    st.markdown("---")
    st.caption(f"Dashboard v{DASHBOARD_VERSION}")
    st.caption("Multi-page Streamlit App")


st.markdown("## Configured Models")

model_rows: list[dict[str, object]] = []
for model in configured_models:
    metadata = model.extra_metadata or {}
    model_rows.append(
        {
            "Name": model.name,
            "Provider": model.provider,
            "Model Key": model.model_key or "-",
            "Model Path": model.model_path or "-",
            "API Identifier": model.api_identifier or "-",
            "Context Window": metadata.get("context_window", "-"),
            "Recommended VRAM (GB)": metadata.get("recommended_vram_gb", "-"),
            "Description": metadata.get("description", ""),
        }
    )

if model_rows:
    st.dataframe(pd.DataFrame(model_rows))
else:
    st.info("No models are configured yet. Use the sidebar to add model details.")


st.markdown("## API Credential Status")

api_status_rows = [
    {
        "Provider": "OpenAI",
        "Configured": "✅" if existing_keys.get("openai") else "❌",
        "Preview": _mask_key(existing_keys.get("openai")),
    },
    {
        "Provider": "Anthropic",
        "Configured": "✅" if existing_keys.get("anthropic") else "❌",
        "Preview": _mask_key(existing_keys.get("anthropic")),
    },
    {
        "Provider": "Gemini",
        "Configured": "✅" if existing_keys.get("gemini") else "❌",
        "Preview": _mask_key(existing_keys.get("gemini")),
    },
]

st.table(pd.DataFrame(api_status_rows))
