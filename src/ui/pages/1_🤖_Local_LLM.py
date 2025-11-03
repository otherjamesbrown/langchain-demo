#!/usr/bin/env python3
"""
Local LLM Page

Interactive interface for calling local LLM models with real-time metrics.

URL: http://host:8501/Local_LLM
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
import time
from datetime import datetime

from src.utils.streamlit_helpers import init_streamlit_db
from src.database.operations import (
    ensure_default_configuration,
    get_model_configurations,
    get_last_used_model,
    set_last_used_model,
)
from src.utils.metrics import LLMMetrics
from src.utils.llm_logger import log_llm_call

# Page config
st.set_page_config(
    page_title="Local LLM - Dashboard",
    page_icon="🤖",
    layout="wide"
)

# Main page
st.title("🤖 Call Local LLM")
st.markdown("Interactively call your local LLM and see metrics in real-time")

# Initialize database
session = init_streamlit_db()

ensure_default_configuration(session=session)

# Model configuration sidebar
st.sidebar.header("⚙️ Model Configuration")

# Get all active local models from database
all_local_models = get_model_configurations(provider="local", session=session)

# Filter to only include valid local models (must have a valid path that exists)
valid_local_models = []
for model in all_local_models:
    if model.model_path:
        model_path = Path(model.model_path).expanduser()
        if model_path.exists():
            valid_local_models.append(model)
    # If no path or path doesn't exist, skip this model

local_models = valid_local_models

if not local_models:
    st.sidebar.error("No valid local models configured. Add models with valid file paths on the Home page.")
    st.stop()

last_used = get_last_used_model(session=session)
default_index = 0
if last_used and last_used.provider == "local":
    for idx, model in enumerate(local_models):
        if model.id == last_used.id:
            default_index = idx
            break

selected_name = st.sidebar.selectbox(
    "Local Model",
    options=[model.name for model in local_models],
    index=default_index,
    help="Switch between pre-configured quantised models stored in the database.",
)

selected_model = next(model for model in local_models if model.name == selected_name)
if not last_used or last_used.id != selected_model.id:
    set_last_used_model(selected_model.id, session=session)

model_key = selected_model.model_key or selected_model.name
# Model path already validated to exist in filter above
model_path = selected_model.model_path.strip()

metadata = selected_model.extra_metadata or {}
if metadata.get("description"):
    st.sidebar.caption(f"📝 {metadata['description']}")
if metadata.get("recommended_vram_gb") or metadata.get("context_window"):
    st.sidebar.caption(
        "💾 Recommended VRAM: "
        f"{metadata.get('recommended_vram_gb', 'N/A')}GB | "
        f"Context window: {metadata.get('context_window', 'N/A')}"
    )
# Path already validated, so it's safe to display
st.sidebar.code(model_path, language="bash")

default_max_tokens = int(metadata.get("max_output_tokens", 512))

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
    value=default_max_tokens,
    step=64,
    help="Maximum number of tokens to generate"
)

# Load model button
if st.sidebar.button("🔄 Reload Model"):
    st.cache_resource.clear()
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
def load_llm(model_key: str, model_path: str, temperature: float, max_tokens: int):
    """Load the local LLM model (cached to avoid reloading)."""
    try:
        from src.models.model_factory import get_llm

        llm = get_llm(
            model_type="local",
            model_path=model_path,
            local_model_name=model_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return llm, None
    except Exception as e:
        return None, str(e)

# Model path already validated in filter above, so we can safely use it
resolved_model_path = Path(model_path).expanduser()

# Show loading indicator
with st.spinner("Loading model..."):
    llm, error = load_llm(model_key, str(resolved_model_path), temperature, int(max_tokens))

if error:
    st.error(f"❌ Failed to load model: {error}")
    st.code(error)
    st.info("💡 Make sure the model path is correct and the model file exists")
    st.stop()

if llm is None:
    st.warning("⏳ Loading model... This may take 10-30 seconds on first load.")
    st.info("💡 The model will be cached after first load for faster subsequent calls")
    st.stop()

# Show model loaded successfully (only once)
selected_model_display = selected_model.name

if "model_loaded_shown" not in st.session_state:
    st.success(f"✅ Model loaded: {selected_model_display}")
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

                # Call LLM
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
                    # Fallback to LangChain wrapper
                    response_text = llm.invoke(prompt)
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
                    model_name=selected_model_display,
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
                            model_name=selected_model_display,
                            call_type="ui_interactive",
                            metadata={
                                "local_model_key": model_key,
                                "model_path": str(resolved_model_path),
                                "provider": "local",
                                "model_configuration_id": selected_model.id,
                            },
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
