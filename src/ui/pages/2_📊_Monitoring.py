#!/usr/bin/env python3
"""
Monitoring Page

Real-time monitoring and analysis of LLM API calls with filtering and detailed inspection.

URL: http://host:8501/Monitoring
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
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from src.database.schema import LLMCallLog, get_session, create_database

# Page config
st.set_page_config(
    page_title="Monitoring - Dashboard",
    page_icon="📊",
    layout="wide"
)

# Initialize database
@st.cache_resource
def init_db():
    """Initialize database connection."""
    create_database()
    return get_session()

def get_call_logs(session: Session, limit: int = 100, model_type: str = None,
                   start_date: datetime = None, end_date: datetime = None):
    """Get LLM call logs from database."""
    query = session.query(LLMCallLog)

    if model_type:
        query = query.filter(LLMCallLog.model_type == model_type)

    if start_date:
        query = query.filter(LLMCallLog.created_at >= start_date)

    if end_date:
        query = query.filter(LLMCallLog.created_at <= end_date)

    return query.order_by(desc(LLMCallLog.created_at)).limit(limit).all()


def get_summary_stats(session: Session, model_type: str = None,
                      start_date: datetime = None, end_date: datetime = None):
    """Get summary statistics for LLM calls."""
    query = session.query(LLMCallLog)

    if model_type:
        query = query.filter(LLMCallLog.model_type == model_type)

    if start_date:
        query = query.filter(LLMCallLog.created_at >= start_date)

    if end_date:
        query = query.filter(LLMCallLog.created_at <= end_date)

    stats = {
        'total_calls': query.count(),
        'total_prompt_tokens': query.with_entities(func.sum(LLMCallLog.prompt_tokens)).scalar() or 0,
        'total_completion_tokens': query.with_entities(func.sum(LLMCallLog.completion_tokens)).scalar() or 0,
        'total_tokens': query.with_entities(func.sum(LLMCallLog.total_tokens)).scalar() or 0,
        'total_time': query.with_entities(func.sum(LLMCallLog.generation_time_seconds)).scalar() or 0.0,
        'successful_calls': query.filter(LLMCallLog.success == True).count(),
        'failed_calls': query.filter(LLMCallLog.success == False).count(),
        'avg_tokens_per_second': query.with_entities(func.avg(LLMCallLog.tokens_per_second)).scalar() or 0.0,
    }

    return stats


# Main page
st.title("📊 LLM Call Monitor")
st.markdown("Real-time monitoring and analysis of LLM API calls")

# Initialize database
try:
    session = init_db()
except Exception as e:
    st.error(f"Failed to connect to database: {e}")
    st.stop()

# Sidebar filters
st.sidebar.header("🔍 Filters")

model_types = session.query(LLMCallLog.model_type).distinct().all()
model_types = [m[0] for m in model_types if m[0]]
model_filter = st.sidebar.selectbox(
    "Model Type",
    options=["All"] + model_types,
    index=0
)

date_range = st.sidebar.selectbox(
    "Time Range",
    options=["Last hour", "Last 24 hours", "Last 7 days", "Last 30 days", "All time"],
    index=1
)

# Calculate date range
now = datetime.utcnow()
if date_range == "Last hour":
    start_date = now - timedelta(hours=1)
    end_date = None
elif date_range == "Last 24 hours":
    start_date = now - timedelta(days=1)
    end_date = None
elif date_range == "Last 7 days":
    start_date = now - timedelta(days=7)
    end_date = None
elif date_range == "Last 30 days":
    start_date = now - timedelta(days=30)
    end_date = None
else:
    start_date = None
    end_date = None

# Get data
model_type_filter = None if model_filter == "All" else model_filter

# Summary stats
stats = get_summary_stats(session, model_type_filter, start_date, end_date)

# Display summary metrics
st.header("Summary Statistics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Calls", stats['total_calls'])
    st.metric("Successful", stats['successful_calls'],
             delta=None if stats['failed_calls'] == 0 else f"-{stats['failed_calls']} failed")

with col2:
    st.metric("Total Tokens", f"{stats['total_tokens']:,}")
    st.caption(f"Prompt: {stats['total_prompt_tokens']:,} | Completion: {stats['total_completion_tokens']:,}")

with col3:
    st.metric("Total Time", f"{stats['total_time']:.1f}s")
    if stats['total_time'] > 0:
        avg_speed = stats['avg_tokens_per_second']
        st.caption(f"Avg: {avg_speed:.1f} tokens/sec")

with col4:
    if stats['total_calls'] > 0 and stats['total_time'] > 0:
        calls_per_min = (stats['total_calls'] / stats['total_time']) * 60
        st.metric("Call Rate", f"{calls_per_min:.1f}/min")
    else:
        st.metric("Call Rate", "N/A")

st.divider()

# Recent calls table
st.header("Recent LLM Calls")

logs = get_call_logs(session, limit=100, model_type=model_type_filter,
                    start_date=start_date, end_date=end_date)

if not logs:
    st.info("No LLM calls found for the selected filters.")
else:
    # Create dataframe
    data = []
    for log in logs:
        data.append({
            "ID": log.id,
            "Time": log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "Model": log.model_name,
            "Type": log.model_type,
            "Prompt Tokens": log.prompt_tokens,
            "Completion Tokens": log.completion_tokens,
            "Total Tokens": log.total_tokens,
            "Time (s)": f"{log.generation_time_seconds:.2f}",
            "Speed (tok/s)": f"{log.tokens_per_second:.1f}" if log.tokens_per_second else "N/A",
            "Success": "✅" if log.success else "❌",
        })

    df = pd.DataFrame(data)

    # Display table
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

    # Call details expander
    st.subheader("Call Details")

    selected_id = st.selectbox(
        "Select a call to view details:",
        options=[log.id for log in logs],
        format_func=lambda x: f"Call #{x} - {next((log.created_at.strftime('%Y-%m-%d %H:%M:%S') for log in logs if log.id == x), 'Unknown')}"
    )

    if selected_id:
        selected_log = next(log for log in logs if log.id == selected_id)

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Model Information**")
            st.write(f"Model Type: {selected_log.model_type}")
            st.write(f"Model Name: {selected_log.model_name}")
            st.write(f"Call Type: {selected_log.call_type}")
            st.write(f"Success: {'✅ Yes' if selected_log.success else '❌ No'}")
            if selected_log.error_message:
                st.error(f"Error: {selected_log.error_message}")

        with col2:
            st.write("**Metrics**")
            st.write(f"Prompt Tokens: {selected_log.prompt_tokens:,}")
            st.write(f"Completion Tokens: {selected_log.completion_tokens:,}")
            st.write(f"Total Tokens: {selected_log.total_tokens:,}")
            st.write(f"Generation Time: {selected_log.generation_time_seconds:.2f}s")
            if selected_log.tokens_per_second:
                st.write(f"Speed: {selected_log.tokens_per_second:.1f} tokens/sec")

        st.write("**Prompt**")
        st.code(selected_log.prompt or "No prompt stored", language=None)

        st.write("**Response**")
        st.code(selected_log.response or "No response stored", language=None)

        if selected_log.extra_metadata:
            with st.expander("Additional Metadata"):
                st.json(selected_log.extra_metadata)

# Auto-refresh
if st.sidebar.button("🔄 Refresh"):
    st.rerun()

auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=False)

if auto_refresh:
    st.sidebar.info("Auto-refresh enabled. Page will reload every 30 seconds.")
    time.sleep(30)
    st.rerun()
