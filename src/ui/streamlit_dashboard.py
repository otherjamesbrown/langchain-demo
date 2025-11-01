#!/usr/bin/env python3
"""
Streamlit Dashboard for LLM Call Logging and Monitoring

This UI provides:
- Call local LLM interactively
- Real-time view of LLM calls
- Token usage statistics
- Performance metrics
- Call history and details
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
import time
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from src.database.schema import LLMCallLog, get_session, create_database
from src.utils.metrics import LLMMetrics
from src.utils.llm_logger import log_llm_call

# Dashboard version - increment this when making UI changes
DASHBOARD_VERSION = "1.2.0"

# Page config
st.set_page_config(
    page_title="LLM Dashboard",
    page_icon="🤖",
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


def page_call_llm():
    """
    Page for calling the local LLM interactively.
    
    This page demonstrates:
    - Loading a local LLM model
    - Making interactive LLM calls
    - Displaying token usage metrics
    - Logging calls to the database
    """
    st.title("🤖 Call Local LLM")
    st.markdown("Interactively call your local LLM and see metrics in real-time")
    
    # Initialize database
    try:
        session = init_db()
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        st.stop()
    
    # Model configuration sidebar (appears below navigation divider)
    st.sidebar.markdown("---")  # Add separator from navigation
    st.sidebar.header("⚙️ Model Configuration")
    
    model_path = st.sidebar.text_input(
        "Model Path",
        value=os.getenv("MODEL_PATH", "./models/llama-2-7b-chat.Q4_K_M.gguf"),
        help="Path to your local LLM model file (.gguf)"
    )
    
    temperature = st.sidebar.slider(
        "Temperature",
        min_value=0.0,
        max_value=2.0,
        value=0.7,
        step=0.1,
        help="Controls randomness: 0 = deterministic, 2 = very creative"
    )
    
    max_tokens = st.sidebar.number_input(
        "Max Tokens",
        min_value=1,
        max_value=4096,
        value=512,
        step=64,
        help="Maximum number of tokens to generate"
    )
    
    # Load model button
    if st.sidebar.button("🔄 Reload Model"):
        st.cache_resource.clear()
        # Reset the loaded message flag so it shows again
        if "model_loaded_shown" in st.session_state:
            del st.session_state.model_loaded_shown
        st.rerun()
    
    # Main interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Prompt")
        prompt = st.text_area(
            "Enter your question or prompt:",
            height=200,
            placeholder="What is machine learning?",
            help="Type your question here and click 'Generate Response'"
        )
        
        # Generate button
        generate_button = st.button("🚀 Generate Response", type="primary", use_container_width=True)
    
    with col2:
        st.subheader("Settings")
        
        show_metrics = st.checkbox("Show Metrics", value=True)
        auto_log = st.checkbox("Log to Database", value=True)
        
        if st.button("📝 Clear History"):
            if "llm_responses" in st.session_state:
                del st.session_state.llm_responses
            st.rerun()
    
    # Initialize session state for responses
    if "llm_responses" not in st.session_state:
        st.session_state.llm_responses = []
    
    # Load model (cached)
    @st.cache_resource
    def load_llm(model_path: str, temperature: float):
        """
        Load the local LLM model (cached to avoid reloading).
        
        This function is cached so the model stays loaded across reruns,
        improving performance for subsequent calls.
        """
        try:
            from src.models.model_factory import get_llm
            
            llm = get_llm(
                model_type="local",
                model_path=model_path,
                temperature=temperature
            )
            
            return llm, None
        except Exception as e:
            return None, str(e)
    
    # Check if model file exists
    if not os.path.exists(model_path):
        st.error(f"❌ Model file not found: {model_path}")
        st.info("💡 Update the model path in the sidebar or set the MODEL_PATH environment variable")
        return
    
    # Show loading indicator
    with st.spinner("Loading model..."):
        llm, error = load_llm(model_path, temperature)
    
    if error:
        st.error(f"❌ Failed to load model: {error}")
        st.code(error)
        st.info("💡 Make sure the model path is correct and the model file exists")
        return
    
    if llm is None:
        st.warning("⏳ Loading model... This may take 10-30 seconds on first load.")
        st.info("💡 The model will be cached after first load for faster subsequent calls")
        return
    
    # Show model loaded successfully (only once)
    if "model_loaded_shown" not in st.session_state:
        st.success(f"✅ Model loaded: {os.path.basename(model_path)}")
        st.session_state.model_loaded_shown = True
    
    # Generate response when button is clicked
    if generate_button:
        if not prompt.strip():
            st.warning("⚠️ Please enter a prompt before generating a response")
        else:
            with st.spinner("🤔 Generating response..."):
                try:
                    # Record start time
                    start_time = time.time()
                    
                    # Call LLM via underlying client to get usage metrics
                    # LangChain wrapper doesn't expose usage, so we use the client directly
                    response_text = ""
                    prompt_tokens = 0
                    completion_tokens = 0
                    
                    if hasattr(llm, 'client'):
                        # Use underlying llama-cpp-python client for accurate metrics
                        result = llm.client(
                            prompt,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            stop=[],
                            echo=False
                        )
                        response_text = result['choices'][0]['text'].strip()
                        usage = result.get('usage', {})
                        prompt_tokens = usage.get('prompt_tokens', 0)
                        completion_tokens = usage.get('completion_tokens', 0)
                    else:
                        # Fallback to LangChain wrapper (less accurate metrics)
                        response_text = llm.invoke(prompt)
                        # Estimate tokens (rough approximation: ~1.3 tokens per word)
                        prompt_tokens = int(len(prompt.split()) * 1.3)
                        completion_tokens = int(len(response_text.split()) * 1.3)
                    
                    # Record end time
                    end_time = time.time()
                    generation_time = end_time - start_time
                    
                    total_tokens = prompt_tokens + completion_tokens
                    
                    # Create metrics object
                    metrics = LLMMetrics(
                        prompt_tokens=int(prompt_tokens),
                        completion_tokens=int(completion_tokens),
                        total_tokens=total_tokens,
                        start_time=start_time,
                        end_time=end_time,
                        generation_time=generation_time,
                        model_name=os.path.basename(model_path),
                        model_type="local"
                    )
                    
                    # Log to database if enabled
                    log_entry = None
                    if auto_log:
                        try:
                            log_entry = log_llm_call(
                                metrics=metrics,
                                prompt=prompt,
                                response=response_text,
                                model_name=os.path.basename(model_path),
                                call_type="ui_interactive",
                                session=session
                            )
                            session.commit()
                        except Exception as e:
                            st.warning(f"⚠️ Failed to log to database: {e}")
                    
                    # Store response in session state
                    response_data = {
                        "timestamp": datetime.now(),
                        "prompt": prompt,
                        "response": response_text,
                        "metrics": metrics,
                        "log_id": log_entry.id if log_entry else None
                    }
                    st.session_state.llm_responses.insert(0, response_data)
                    
                    # Display success message
                    if log_entry:
                        st.success(f"✅ Response generated and logged (ID: {log_entry.id})")
                    else:
                        st.success("✅ Response generated")
                    
                except Exception as e:
                    st.error(f"❌ Error generating response: {e}")
                    st.code(str(e))
    
    # Display latest response
    if st.session_state.llm_responses:
        latest = st.session_state.llm_responses[0]
        
        st.divider()
        st.subheader("📝 Latest Response")
        
        # Display prompt and response
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Your Prompt:**")
            st.write(latest["prompt"])
        
        with col2:
            st.write("**LLM Response:**")
            st.write(latest["response"])
        
        # Display metrics if enabled
        if show_metrics:
            st.divider()
            st.subheader("📊 Metrics")
            
            metrics = latest["metrics"]
            
            metric_cols = st.columns(4)
            
            with metric_cols[0]:
                st.metric("Prompt Tokens", f"{metrics.prompt_tokens:,}")
            
            with metric_cols[1]:
                st.metric("Completion Tokens", f"{metrics.completion_tokens:,}")
            
            with metric_cols[2]:
                st.metric("Total Tokens", f"{metrics.total_tokens:,}")
            
            with metric_cols[3]:
                st.metric("Generation Time", f"{metrics.generation_time:.2f}s")
            
            # Additional metrics
            st.caption(f"⚡ Speed: {metrics.tokens_per_second():.1f} tokens/second")
            st.caption(f"🕐 Timestamp: {latest['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            
            if latest["log_id"]:
                st.caption(f"📝 Logged to database (ID: {latest['log_id']})")
    
    # Display response history
    if len(st.session_state.llm_responses) > 1:
        st.divider()
        st.subheader("📜 Response History")
        
        with st.expander(f"View {len(st.session_state.llm_responses) - 1} previous responses"):
            for i, resp in enumerate(st.session_state.llm_responses[1:], 1):
                with st.container():
                    st.write(f"**Response #{i}** - {resp['timestamp'].strftime('%H:%M:%S')}")
                    st.caption(f"Prompt: {resp['prompt'][:100]}...")
                    st.caption(f"Tokens: {resp['metrics'].total_tokens} | Time: {resp['metrics'].generation_time:.2f}s")
                    if st.button(f"View Full Response #{i}", key=f"view_{i}"):
                        st.write("**Prompt:**", resp['prompt'])
                        st.write("**Response:**", resp['response'])
                    st.divider()


def page_monitor():
    """Monitoring page - shows call logs and statistics."""
    st.title("📊 LLM Call Monitor")
    st.markdown("Real-time monitoring and analysis of LLM API calls")
    
    # Initialize database
    try:
        session = init_db()
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        st.stop()
    
    # Sidebar filters (appears below navigation divider)
    st.sidebar.markdown("---")  # Add separator from navigation
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


def main():
    """Main Streamlit app with page navigation."""
    # Page selector in sidebar - always at the top, before any page content
    with st.sidebar:
        st.title("🧭 Navigation")
        st.markdown("---")
        page = st.radio(
            "Select Page",
            ["🤖 Call Local LLM", "📊 Monitor Calls"],
            label_visibility="visible",
            key="page_selector"
        )
        st.markdown("---")
        
        # Version number at bottom of sidebar for validation
        st.markdown("---")
        st.caption(f"Dashboard v{DASHBOARD_VERSION}")
    
    # Route to selected page (page functions will add their content below navigation)
    if "Call Local LLM" in page or "🤖" in page:
        page_call_llm()
    elif "Monitor Calls" in page or "📊" in page:
        page_monitor()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Error: {e}")
        import traceback
        st.code(traceback.format_exc())

