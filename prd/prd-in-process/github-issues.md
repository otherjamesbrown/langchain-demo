# GitHub Issues for LangSmith Observability Enhancement

Copy each section below into a new GitHub issue.

---

## Issue 1: LangSmith Phase 1 - Core Infrastructure

**Title**: LangSmith Phase 1: Core Infrastructure

**Labels**: `enhancement`, `langsmith`, `monitoring`

**Body**:
```markdown
## Phase 1: Core Infrastructure (Week 1-2)

**Goals**: Establish automatic tracing foundation

### Tasks
- [ ] Enhance `src/utils/monitoring.py`:
  - Create `EnhancedLangSmithCallback` class
  - Add `configure_langsmith_tracing()` function
  - Add context managers for tracing
- [ ] Update environment configuration:
  - Ensure `LANGCHAIN_API_KEY` properly loaded
  - Add `LANGCHAIN_PROJECT` configuration
- [ ] Test basic tracing:
  - Write test script (`scripts/test_langsmith_basic.py`)
  - Verify traces appear in LangSmith UI

### Deliverables
- Enhanced `monitoring.py` with comprehensive callbacks
- Test script demonstrating tracing
- Basic documentation

### Related
- PRD: `prd/prd-in-process/PRD_LANGSMITH_OBSERVABILITY.md`
- Existing: `src/utils/monitoring.py`
```

---

## Issue 2: LangSmith Phase 2 - Two-Phase Integration

**Title**: LangSmith Phase 2: Two-Phase Integration

**Labels**: `enhancement`, `langsmith`, `research-workflow`

**Body**:
```markdown
## Phase 2: Two-Phase Integration (Week 3-4)

**Goals**: Integrate tracing into Phase 1 and Phase 2 workflows

### Tasks

**Phase 1 (Search Collection)**:
- [ ] Add tracing to `query_generator.py`
- [ ] Add tracing to `search_executor.py`
- [ ] Tag all traces with `phase:search-collection`

**Phase 2 (LLM Processing)**:
- [ ] Add tracing to `llm_processor.py`
- [ ] Add tracing to `prompt_builder.py`
- [ ] Tag all traces with `phase:llm-processing`

**Workflows**:
- [ ] Add tracing context managers to `workflows.py`
- [ ] Link Phase 1 and Phase 2 traces

### Deliverables
- Full tracing in `src/research/` module
- Test script (`scripts/test_langsmith_two_phase.py`)
- Trace visualization examples

### Prerequisites
- Issue #XX (Phase 1) must be complete

### Related
- PRD: `prd/prd-in-process/PRD_LANGSMITH_OBSERVABILITY.md`
```

---

## Issue 3: LangSmith Phase 3 - Analytics & Monitoring

**Title**: LangSmith Phase 3: Analytics & Monitoring

**Labels**: `enhancement`, `langsmith`, `analytics`

**Body**:
```markdown
## Phase 3: Analytics & Monitoring (Week 5-6)

**Goals**: Add performance analytics and cost tracking

### Tasks

**Token Usage Tracking**:
- [ ] Capture tokens in callback handlers
- [ ] Store in trace metadata
- [ ] Aggregate by company/model

**Cost Tracking**:
- [ ] Add cost calculation per model (OpenAI, Anthropic, Gemini)
- [ ] Store in trace metadata
- [ ] Create cost reporting utilities

**Latency Tracking**:
- [ ] Capture start/end times
- [ ] Calculate latency metrics
- [ ] Identify bottlenecks

### Deliverables
- Cost tracking utilities in `monitoring.py`
- Performance metrics in traces
- Cost reporting script

### Prerequisites
- Issue #XX (Phase 1) must be complete

### Related
- PRD: `prd/prd-in-process/PRD_LANGSMITH_OBSERVABILITY.md`
```

---

## Issue 4: LangSmith Phase 4 - Model Comparison

**Title**: LangSmith Phase 4: Model Comparison

**Labels**: `enhancement`, `langsmith`, `model-evaluation`

**Body**:
```markdown
## Phase 4: Model Comparison (Week 7-8)

**Goals**: Enable dataset-based model comparison

### Tasks

**Dataset Creation**:
- [ ] Function to convert Phase 1 results to LangSmith datasets
- [ ] Upload datasets to LangSmith

**Model Evaluation**:
- [ ] Run multiple models on same dataset
- [ ] Compare results in LangSmith

**Prompt Versioning**:
- [ ] Link traces to prompt versions
- [ ] Compare performance across versions

### Deliverables
- Dataset creation utilities (`src/utils/langsmith_datasets.py`)
- Model comparison scripts
- Prompt versioning documentation

### Prerequisites
- Issue #XX (Phase 2) must be complete

### Related
- PRD: `prd/prd-in-process/PRD_LANGSMITH_OBSERVABILITY.md`
```

---

## Issue 5: LangSmith Phase 5 - UI Integration & Documentation

**Title**: LangSmith Phase 5: UI Integration & Documentation

**Labels**: `enhancement`, `langsmith`, `documentation`, `ui`

**Body**:
```markdown
## Phase 5: UI Integration & Documentation (Week 9-10)

**Goals**: Integrate with Streamlit UI and create comprehensive documentation

### Tasks

**Streamlit Integration**:
- [ ] Add LangSmith trace links to monitoring page
- [ ] Add trace links to agent page
- [ ] Display metrics in UI

**Database Integration**:
- [ ] Add `langsmith_trace_id` columns to schema
- [ ] Store trace IDs during execution
- [ ] Create bidirectional lookup utilities

**Documentation**:
- [ ] Write `docs/implemented/LANGSMITH_INTEGRATION.md`
- [ ] Write `docs/reference/LANGSMITH_USAGE_GUIDE.md`
- [ ] Update main `README.md`
- [ ] Create example traces with annotations

**Testing**:
- [ ] Integration tests for tracing
- [ ] End-to-end testing with LangSmith
- [ ] Performance testing

### Deliverables
- UI with LangSmith integration
- Database schema updates
- Comprehensive documentation
- Test suite

### Prerequisites
- All previous phases must be complete

### Related
- PRD: `prd/prd-in-process/PRD_LANGSMITH_OBSERVABILITY.md`
```

---

## How to Create Issues

### Option 1: Manual Creation
1. Go to: https://github.com/Linode/langchain-demo/issues/new
2. Copy the title and body from each issue above
3. Add the specified labels
4. Click "Submit new issue"

### Option 2: GitHub CLI (if installed)
```bash
# Install gh CLI if needed: https://cli.github.com/

# Then run this script to create all issues
cd /Users/jabrown/Documents/GitHub/Linode/langchain-demo
# Copy commands from above and run them
```

### Option 3: GitHub API Script
```bash
# See scripts/create_langsmith_issues.sh (to be created)
```

