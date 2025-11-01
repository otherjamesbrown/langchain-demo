# UI Component Options for LangChain Research Agent

## Overview

While LangChain itself doesn't provide a built-in UI framework, there are several options to add a user interface to your research agent.

## Option 1: Streamlit (Recommended for Quick UI)

**Best for**: Rapid prototyping and simple dashboards

### Features
- **Easy to implement**: Pure Python, no HTML/CSS/JS needed
- **Data visualization**: Built-in support for charts, tables, and dataframes
- **File upload**: Built-in CSV and file upload widgets
- **Auto-refresh**: Automatic reruns on interaction
- **Deployment**: Easy deployment to Streamlit Cloud

### Installation
```bash
pip install streamlit streamlit-chat
```

### Example Implementation
```python
import streamlit as st
from src.agent.research_agent import ResearchAgent
from src.models.model_factory import get_llm

st.title("LangChain Research Agent")

# Sidebar configuration
st.sidebar.header("Configuration")
model_type = st.sidebar.selectbox("Model Type", ["local", "openai", "anthropic"])

# Main interface
uploaded_file = st.file_uploader("Upload CSV file", type="csv")
instructions = st.text_area("Research Instructions", height=150)

if st.button("Run Research"):
    llm = get_llm(model_type=model_type)
    agent = ResearchAgent(llm=llm)
    
    with st.spinner("Processing..."):
        results = agent.research_companies(
            csv_path=uploaded_file,
            instructions=instructions
        )
    
    st.success("Research complete!")
    st.dataframe(results)
```

### Run
```bash
streamlit run src/ui/streamlit_app.py
```

**Pros**: Fast development, built-in widgets, good for dashboards  
**Cons**: Limited customization, not suitable for complex apps

---

## Option 2: Gradio

**Best for**: Demo interfaces and sharing with non-technical users

### Features
- **User-friendly**: Very simple interface for end-users
- **Pre-built components**: Chat, file upload, output display
- **Sharing**: Built-in public sharing via HuggingFace Spaces
- **Examples**: Easy to showcase inputs/outputs

### Installation
```bash
pip install gradio
```

### Example Implementation
```python
import gradio as gr
from src.agent.research_agent import ResearchAgent
from src.models.model_factory import get_llm

def run_research(csv_file, instructions):
    llm = get_llm(model_type="local")
    agent = ResearchAgent(llm=llm)
    results = agent.research_companies(csv_path=csv_file.name, instructions=instructions)
    return results.to_html()

interface = gr.Interface(
    fn=run_research,
    inputs=[
        gr.File(label="Upload CSV"),
        gr.Textbox(label="Instructions", lines=5)
    ],
    outputs=gr.HTML(),
    title="LangChain Research Agent"
)

interface.launch(server_name="0.0.0.0", server_port=7860)
```

**Pros**: Very simple, good for demos, easy sharing  
**Cons**: Less flexible, limited for complex UIs

---

## Option 3: LangSmith (Monitoring Only)

**Best for**: Development, debugging, and monitoring agent execution

### Features
- **Tracing**: Visualize agent execution steps
- **Debugging**: Inspect intermediate outputs
- **Performance**: Track latency and token usage
- **Cost tracking**: Monitor API costs

### Setup
```bash
# Already in requirements.txt
pip install langsmith

# Configure
export LANGCHAIN_API_KEY="your_key"
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_PROJECT="research-agent"
```

**Pros**: Best for debugging and monitoring  
**Cons**: Not a user interface for running agents

---

## Option 4: Custom Web Interface (FastAPI + React)

**Best for**: Production applications with full control

### Stack
- **Backend**: FastAPI (Python)
- **Frontend**: React or Vue.js
- **Database**: SQLite/PostgreSQL

### Architecture
```
User Browser
    ↓
React Frontend (port 3000)
    ↓
FastAPI Backend (port 8000)
    ↓
LangChain Agent
    ↓
Database
```

### Features
- Full control over UI/UX
- RESTful API
- Real-time updates with WebSockets
- Multi-user support
- Authentication and authorization

**Pros**: Full flexibility, production-ready  
**Cons**: More development time, requires frontend knowledge

---

## Option 5: LangFlow (Visual Flow Builder)

**Best for**: Experimenting with different agent flows without coding

### Features
- **Drag-and-drop**: Visual flow builder
- **Component library**: Pre-built LangChain components
- **Experimentation**: Easy to test different configurations
- **Export**: Can export flows as code

### Installation
```bash
pip install langflow
```

### Usage
```bash
langflow run
# Opens browser at http://localhost:7860
```

**Pros**: Great for experimentation, visual debugging  
**Cons**: Not ideal for production deployment

---

## Recommendation for This Project

### Phase 1: Start with Streamlit
- Quick to implement
- Good for basic research workflow
- Easy to demonstrate functionality

### Phase 2: Add Gradio for Demos
- Share with stakeholders
- Simple user interface
- Easy deployment

### Phase 3: Build Custom Web UI (if needed)
- Full control and customization
- Production-ready
- Multi-user support

### Always: Use LangSmith for Development
- Essential for debugging
- Monitor agent performance
- Track costs

## Implementation Plan

1. **Add Streamlit UI**: Create `src/ui/streamlit_app.py`
2. **Add Gradio UI**: Create `src/ui/gradio_app.py`
3. **Configure LangSmith**: Set up monitoring
4. **Create API**: Build FastAPI backend (optional)
5. **Deploy**: Choose deployment method

## Example Directory Structure

```
langchain-demo/
├── src/
│   ├── agent/
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── streamlit_app.py
│   │   ├── gradio_app.py
│   │   └── api.py (FastAPI)
│   ├── models/
│   ├── database/
│   └── utils/
└── frontend/ (if using React)
    ├── src/
    └── public/
```

## Security Considerations

When deploying UI to production:

1. **Authentication**: Add user login/session management
2. **Rate limiting**: Prevent abuse
3. **Input validation**: Sanitize user inputs
4. **API keys**: Never expose keys in frontend code
5. **HTTPS**: Use SSL/TLS certificates
6. **Firewall**: Restrict access to authorized users only

## Next Steps

1. Choose UI framework based on needs
2. Implement basic interface
3. Test with sample data
4. Deploy to staging
5. Get user feedback
6. Iterate and improve

