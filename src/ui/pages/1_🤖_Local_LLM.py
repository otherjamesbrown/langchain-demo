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

from src.database.schema import get_session, create_database
from src.models.local_registry import list_local_models
from src.utils.metrics import LLMMetrics
from src.utils.llm_logger import log_llm_call

# Page config
st.set_page_config(
    page_title="Local LLM - Dashboard",
    page_icon="🤖",
    layout="wide"
)

# Initialize database
@st.cache_resource
def init_db():
    """Initialize database connection."""
    create_database()
    return get_session()

# Main page
st.title("🤖 Call Local LLM")
st.markdown("Interactively call your local LLM and see metrics in real-time")

# Initialize database
try:
    session = init_db()
except Exception as e:
    st.error(f"Failed to connect to database: {e}")
    st.stop()

# Model configuration sidebar
st.sidebar.header("⚙️ Model Configuration")

available_models = list_local_models()
model_display_to_config = {config.display_name: config for config in available_models}
model_options = list(model_display_to_config.keys()) + ["Custom path"]

env_default_key = os.getenv("LOCAL_MODEL_NAME")
default_index = 0
if env_default_key:
    for idx, config in enumerate(available_models):
        if config.key.lower() == env_default_key.lower():
            default_index = idx
            break

selected_option = st.sidebar.selectbox(
    "Local Model",
    options=model_options,
    index=default_index if default_index < len(model_options) - 1 else 0,
    help="Switch between pre-configured quantised models without editing env vars"
)

if selected_option in model_display_to_config:
    selected_config = model_display_to_config[selected_option]
    model_key = selected_config.key
    default_model_path = str(selected_config.resolve_path())
    st.sidebar.caption(
        f"📝 {selected_config.description}"
    )
    st.sidebar.caption(
        f"💾 Recommended VRAM: {selected_config.recommended_vram_gb}GB | "
        f"Context window: {selected_config.context_window}"
    )
else:
    selected_config = None
    model_key = "custom"
    default_model_path = os.getenv("MODEL_PATH", "./models/llama-2-7b-chat.Q4_K_M.gguf")

model_path = st.sidebar.text_input(
    "Model Path",
    value=default_model_path,
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
def load_llm(model_key: str, model_path: str, temperature: float):
    """Load the local LLM model (cached to avoid reloading)."""
    try:
        from src.models.model_factory import get_llm

        llm = get_llm(
            model_type="local",
            model_path=model_path,
            local_model_name=None if model_key == "custom" else model_key,
            temperature=temperature
        )

        return llm, None
    except Exception as e:
        return None, str(e)

# Check if model file exists
resolved_model_path = Path(model_path).expanduser()
if not resolved_model_path.exists():
    st.error(f"❌ Model file not found: {resolved_model_path}")
    st.info("💡 Update the model path in the sidebar or set the MODEL_PATH environment variable")
    st.stop()

# Show loading indicator
with st.spinner("Loading model..."):
    llm, error = load_llm(model_key, str(resolved_model_path), temperature)

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
if selected_config is None:
    selected_model_display = resolved_model_path.name or "Custom path"
else:
    selected_model_display = selected_config.display_name

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
