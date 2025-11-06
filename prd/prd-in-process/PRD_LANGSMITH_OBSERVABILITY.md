# Product Requirements Document: LangSmith Observability Enhancement

**Document Status:** Draft  
**Version:** 1.0  
**Created:** 2025-11-06  
**Target Completion:** Q1 2026  
**Priority:** High  
**Related Docs:** 
- [`PRD.md`](PRD.md) - Original project requirements
- [`PRD_CURRENT_STATE.md`](PRD_CURRENT_STATE.md) - Current implementation state
- [`docs/implemented/TWO_PHASE_ARCHITECTURE.md`](../docs/implemented/TWO_PHASE_ARCHITECTURE.md) - Architecture details

---

## Executive Summary

This PRD outlines requirements for **enhancing LangSmith integration** to provide comprehensive observability across the LangChain research agent system. While basic LangSmith configuration exists, it is currently underutilized. This enhancement will provide production-grade monitoring, debugging, and performance analytics capabilities.

### Problem Statement

**Current State:**
- Basic LangSmith configuration exists but is minimal (`src/utils/monitoring.py`)
- LangSmith marked as "optional" - not integrated into core workflows
- No comprehensive tracing across two-phase architecture
- Limited visibility into agent decision-making and LLM performance
- Difficult to debug failures or optimize prompt engineering
- No cost tracking for API-based model usage

**Impact:**
- Debugging agent failures is time-consuming (manual log analysis)
- Cannot easily compare model performance across runs
- No visibility into prompt effectiveness or token usage patterns
- Difficult to optimize costs for production deployments
- Limited educational value for understanding agent behavior

### Proposed Solution

Implement **comprehensive LangSmith observability** that provides:

1. **Automatic Tracing**: Full execution traces for all LLM calls across both phases
2. **Two-Phase Visibility**: Specialized monitoring for Phase 1 (search) and Phase 2 (processing)
3. **Performance Analytics**: Token usage, latency, and cost tracking
4. **Comparative Analysis**: Side-by-side model comparison with LangSmith datasets
5. **Educational Insights**: Agent reasoning visibility for learning purposes
6. **Production Monitoring**: Error tracking, alerting, and performance baselines

---

## Goals & Success Criteria

### Primary Goals

1. **🔍 Comprehensive Tracing**: All LLM calls automatically traced with full context
2. **📊 Performance Analytics**: Token usage, latency, and cost tracking per model/run
3. **🐛 Enhanced Debugging**: Easy identification of failures and performance bottlenecks
4. **💰 Cost Optimization**: Track and optimize API costs across model providers
5. **🎓 Educational Value**: Visualize agent reasoning for learning purposes

### Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| LLM Call Visibility | 0% (logs only) | 100% | % of calls traced in LangSmith |
| Debug Time | ~30 min/issue | ~5 min/issue | Avg time to identify failures |
| Cost Visibility | None | Real-time | API cost tracking accuracy |
| Prompt Iteration Speed | Slow (re-run searches) | Fast (Phase 2 only) | Time to test prompt changes |
| Agent Understanding | Limited | High | User feedback on clarity |

### Out of Scope

- Custom LangSmith UI development (use existing LangSmith platform)
- Real-time alerting system (use LangSmith built-in alerts)
- Advanced analytics beyond LangSmith capabilities
- Multi-tenant LangSmith setup (single project for now)

---

## User Stories

### As a Developer

1. **Debugging**: "When an agent run fails, I want to see the full execution trace in LangSmith so I can quickly identify the root cause."

2. **Prompt Engineering**: "When iterating on prompts, I want to compare multiple prompt versions side-by-side using LangSmith datasets so I can optimize for quality."

3. **Model Comparison**: "When evaluating models, I want to see token usage, cost, and quality metrics in LangSmith so I can choose the best model for production."

4. **Performance Optimization**: "When a run is slow, I want to see which LLM calls or tool calls are bottlenecks so I can optimize them."

### As a Student/Learner

5. **Understanding Agents**: "When learning LangChain, I want to see the agent's reasoning steps in LangSmith so I can understand how ReAct agents work."

6. **Comparing Architectures**: "When studying the two-phase architecture, I want to see Phase 1 and Phase 2 as separate traces so I understand the separation of concerns."

### As a Production Operator

7. **Cost Tracking**: "When running in production, I want to see real-time cost estimates per company processed so I can budget effectively."

8. **Error Monitoring**: "When errors occur, I want to be alerted via LangSmith so I can respond quickly."

9. **Performance Baselines**: "When deploying changes, I want to compare performance metrics against baselines so I know if I've regressed."

---

## Technical Requirements

### 1. Core Tracing Infrastructure

#### 1.1 Automatic Tracing Configuration

**Requirement**: All LLM calls automatically traced without manual intervention.

**Implementation**:
- Enhance `src/utils/monitoring.py` with robust LangSmith setup
- Automatic tracing enablement when `LANGCHAIN_API_KEY` is set
- Project-based organization (Phase 1, Phase 2, Testing, etc.)
- Thread-safe tracing context management

**Acceptance Criteria**:
- ✅ All LLM calls in `src/research/` automatically traced
- ✅ All LLM calls in `src/agent/` automatically traced
- ✅ Traces include full input prompts and outputs
- ✅ Traces include token usage and latency metrics
- ✅ Graceful degradation when LangSmith unavailable

#### 1.2 Two-Phase Architecture Integration

**Requirement**: Specialized tracing for Phase 1 (search collection) and Phase 2 (LLM processing).

**Implementation**:
- **Phase 1 Traces**: 
  - Query generation steps
  - Search API calls (Tavily, Serper)
  - Results storage operations
  - Tag: `phase:search-collection`

- **Phase 2 Traces**:
  - Prompt building from instructions + results
  - LLM processing with full context
  - Structured output parsing
  - Validation steps
  - Tag: `phase:llm-processing`

**Acceptance Criteria**:
- ✅ Phase 1 and Phase 2 have separate trace groupings
- ✅ Company name tagged on all traces
- ✅ Model provider/name tagged on Phase 2 traces
- ✅ Can filter traces by phase, company, or model

#### 1.3 Callback Handler Enhancement

**Requirement**: Replace minimal `LangSmithCallback` with comprehensive handlers.

**Implementation**:
```python
class EnhancedLangSmithCallback(BaseCallbackHandler):
    """
    Comprehensive LangSmith callback with:
    - Token usage tracking
    - Cost calculation per model
    - Execution time tracking
    - Error capture with context
    - Custom metadata (company, phase, model)
    """
```

**Acceptance Criteria**:
- ✅ Captures all LLM events (start, end, error)
- ✅ Captures all tool events (search, data loading)
- ✅ Captures agent events (action, observation, finish)
- ✅ Includes custom metadata for filtering
- ✅ Handles errors gracefully

### 2. Performance Analytics

#### 2.1 Token Usage Tracking

**Requirement**: Comprehensive token usage tracking per company, model, and phase.

**Implementation**:
- Track prompt tokens, completion tokens, total tokens
- Store in LangSmith metadata
- Aggregate by company, model, phase
- Export to database (`llm_call_logs` table) for long-term analysis

**Acceptance Criteria**:
- ✅ Token usage visible in LangSmith UI per trace
- ✅ Can query token usage by company
- ✅ Can compare token usage across models
- ✅ Historical token usage data retained

#### 2.2 Cost Tracking

**Requirement**: Real-time cost estimation for API-based models.

**Implementation**:
- Cost calculation per model provider:
  - OpenAI: GPT-4, GPT-3.5 pricing
  - Anthropic: Claude pricing
  - Google: Gemini pricing
- Cost metadata in traces
- Aggregated cost reporting

**Acceptance Criteria**:
- ✅ Cost displayed in LangSmith trace metadata
- ✅ Can filter high-cost traces
- ✅ Monthly cost reporting available
- ✅ Cost per company calculated

#### 2.3 Latency Monitoring

**Requirement**: Track execution time for LLM calls and tool operations.

**Implementation**:
- Start/end timestamps for all operations
- Latency calculation and storage
- P50, P95, P99 latency metrics
- Bottleneck identification

**Acceptance Criteria**:
- ✅ Latency visible per trace
- ✅ Can identify slow LLM calls
- ✅ Can identify slow tool calls
- ✅ Latency trends over time visible

### 3. Debugging & Troubleshooting

#### 3.1 Error Tracing

**Requirement**: Comprehensive error capture with full context.

**Implementation**:
- Automatic error trace creation
- Full stack traces in metadata
- Input/output at time of failure
- Related traces linked (e.g., Phase 1 → Phase 2 failure)

**Acceptance Criteria**:
- ✅ All errors automatically traced
- ✅ Stack traces visible in LangSmith
- ✅ Can filter by error type
- ✅ Error rate tracking available

#### 3.2 Agent Reasoning Visibility

**Requirement**: Visualize agent decision-making process in LangSmith.

**Implementation**:
- Trace agent thoughts (ReAct reasoning)
- Trace tool selection decisions
- Trace observation processing
- Trace final answer synthesis

**Acceptance Criteria**:
- ✅ Agent reasoning steps visible as nested traces
- ✅ Tool selection rationale captured
- ✅ Observation → Action → Thought flow visible
- ✅ Can replay agent execution step-by-step

### 4. Model Comparison

#### 4.1 LangSmith Datasets

**Requirement**: Create datasets for comparing model performance on identical inputs.

**Implementation**:
- Dataset creation from Phase 1 results
- Multiple model evaluation on same dataset
- Side-by-side comparison in LangSmith UI
- Quality scoring and ranking

**Example Dataset Structure**:
```json
{
  "dataset_name": "bitmovin_research_2025_01",
  "examples": [
    {
      "inputs": {
        "company_name": "BitMovin",
        "instructions": "...",
        "search_results": [...]
      },
      "outputs": {
        "expected_fields": ["company_size", "revenue_range", ...]
      }
    }
  ]
}
```

**Acceptance Criteria**:
- ✅ Can create datasets from Phase 1 results
- ✅ Can run multiple models on same dataset
- ✅ Side-by-side comparison in LangSmith
- ✅ Quality scoring automated

#### 4.2 Prompt Versioning

**Requirement**: Track and compare prompt versions over time.

**Implementation**:
- Prompt version hashing (already exists in `prompt_builder.py`)
- Link traces to prompt versions
- Compare performance across versions
- Rollback to previous prompt versions

**Acceptance Criteria**:
- ✅ Prompt version visible in traces
- ✅ Can filter traces by prompt version
- ✅ Can compare metrics across versions
- ✅ Prompt content visible in LangSmith

### 5. Integration Points

#### 5.1 Two-Phase Workflow Integration

**Requirement**: Seamless tracing in `src/research/workflows.py`.

**Files to Modify**:
- `src/research/workflows.py` - Add tracing to all workflow functions
- `src/research/llm_processor.py` - Enhance tracing in LLM processing
- `src/research/search_executor.py` - Add tracing to search execution
- `src/research/query_generator.py` - Add tracing to query generation

**Implementation Pattern**:
```python
from langchain.callbacks import langchain_config

def phase2_process_with_llm(company_name, instructions_path, llm_provider, llm_model):
    with langchain_config(
        project_name=f"research-agent-phase2-{llm_provider}",
        tags=["phase:llm-processing", f"company:{company_name}", f"model:{llm_model}"],
        metadata={"phase": 2, "company": company_name, "model": llm_model}
    ):
        # ... existing code ...
```

**Acceptance Criteria**:
- ✅ All workflow functions traced
- ✅ Nested traces show execution flow
- ✅ Can filter by workflow function
- ✅ Performance metrics per workflow

#### 5.2 Streamlit UI Integration

**Requirement**: Display LangSmith links in Streamlit dashboard.

**Files to Modify**:
- `src/ui/pages/2_📊_Monitoring.py` - Add LangSmith trace links
- `src/ui/pages/3_🔬_Agent.py` - Link agent runs to LangSmith

**Implementation**:
- Show LangSmith trace URL after each execution
- Embed LangSmith metrics in Streamlit UI
- Link from database logs to LangSmith traces

**Acceptance Criteria**:
- ✅ Trace URLs displayed in Streamlit
- ✅ Click-through to LangSmith from UI
- ✅ Metrics synchronized between DB and LangSmith
- ✅ Educational annotations in UI

#### 5.3 Database Integration

**Requirement**: Link LangSmith traces to database records.

**Implementation**:
- Store LangSmith trace IDs in `processing_runs` table
- Store LangSmith trace IDs in `llm_call_logs` table
- Enable bidirectional lookup (DB → LangSmith, LangSmith → DB)

**Schema Changes**:
```sql
ALTER TABLE processing_runs ADD COLUMN langsmith_trace_id TEXT;
ALTER TABLE llm_call_logs ADD COLUMN langsmith_trace_id TEXT;
```

**Acceptance Criteria**:
- ✅ Trace IDs stored in database
- ✅ Can query database by trace ID
- ✅ Can link from trace to database record
- ✅ No breaking changes to existing schema

### 6. Educational Features

#### 6.1 Example Traces

**Requirement**: Create well-documented example traces for learning.

**Implementation**:
- Pre-populated LangSmith project with examples
- Annotated traces explaining each step
- Tutorial documentation referencing traces
- Example datasets for experimentation

**Acceptance Criteria**:
- ✅ 5+ example traces with annotations
- ✅ Examples cover all major workflows
- ✅ Tutorial docs link to examples
- ✅ Examples include good and bad traces

#### 6.2 Documentation

**Requirement**: Comprehensive documentation for using LangSmith with this project.

**Files to Create**:
- `docs/implemented/LANGSMITH_INTEGRATION.md` - Full integration guide
- `docs/reference/LANGSMITH_USAGE_GUIDE.md` - How-to guide for common tasks
- Update `README.md` with LangSmith setup instructions

**Acceptance Criteria**:
- ✅ Setup instructions (getting API key, configuration)
- ✅ Usage examples (viewing traces, creating datasets)
- ✅ Troubleshooting guide
- ✅ Best practices documented

---

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1-2)

**Goals**: Establish automatic tracing foundation

**Tasks**:
1. Enhance `src/utils/monitoring.py`:
   - Create `EnhancedLangSmithCallback` class
   - Add `configure_langsmith_tracing()` function
   - Add context managers for tracing
2. Update environment configuration:
   - Ensure `LANGCHAIN_API_KEY` properly loaded
   - Add `LANGCHAIN_PROJECT` configuration
3. Test basic tracing:
   - Write test script (`scripts/test_langsmith_basic.py`)
   - Verify traces appear in LangSmith UI

**Deliverables**:
- Enhanced `monitoring.py` with comprehensive callbacks
- Test script demonstrating tracing
- Basic documentation

### Phase 2: Two-Phase Integration (Week 3-4)

**Goals**: Integrate tracing into Phase 1 and Phase 2 workflows

**Tasks**:
1. **Phase 1 (Search Collection)**:
   - Add tracing to `query_generator.py`
   - Add tracing to `search_executor.py`
   - Tag all traces with `phase:search-collection`

2. **Phase 2 (LLM Processing)**:
   - Add tracing to `llm_processor.py`
   - Add tracing to `prompt_builder.py`
   - Tag all traces with `phase:llm-processing`

3. **Workflows**:
   - Add tracing context managers to `workflows.py`
   - Link Phase 1 and Phase 2 traces

**Deliverables**:
- Full tracing in `src/research/` module
- Test script (`scripts/test_langsmith_two_phase.py`)
- Trace visualization examples

### Phase 3: Analytics & Monitoring (Week 5-6)

**Goals**: Add performance analytics and cost tracking

**Tasks**:
1. Implement token usage tracking:
   - Capture tokens in callback handlers
   - Store in trace metadata
   - Aggregate by company/model
2. Implement cost tracking:
   - Add cost calculation per model
   - Store in trace metadata
   - Create cost reporting utilities
3. Implement latency tracking:
   - Capture start/end times
   - Calculate latency metrics
   - Identify bottlenecks

**Deliverables**:
- Cost tracking utilities in `monitoring.py`
- Performance metrics in traces
- Cost reporting script

### Phase 4: Model Comparison (Week 7-8)

**Goals**: Enable dataset-based model comparison

**Tasks**:
1. Create dataset creation utilities:
   - Function to convert Phase 1 results to LangSmith datasets
   - Upload datasets to LangSmith
2. Create model evaluation utilities:
   - Run multiple models on same dataset
   - Compare results in LangSmith
3. Add prompt versioning support:
   - Link traces to prompt versions
   - Compare performance across versions

**Deliverables**:
- Dataset creation utilities (`src/utils/langsmith_datasets.py`)
- Model comparison scripts
- Prompt versioning documentation

### Phase 5: UI Integration & Documentation (Week 9-10)

**Goals**: Integrate with Streamlit UI and create comprehensive documentation

**Tasks**:
1. **Streamlit Integration**:
   - Add LangSmith trace links to monitoring page
   - Add trace links to agent page
   - Display metrics in UI

2. **Database Integration**:
   - Add `langsmith_trace_id` columns
   - Store trace IDs during execution
   - Create bidirectional lookup utilities

3. **Documentation**:
   - Write `LANGSMITH_INTEGRATION.md`
   - Write `LANGSMITH_USAGE_GUIDE.md`
   - Update main `README.md`
   - Create example traces with annotations

4. **Testing**:
   - Integration tests for tracing
   - End-to-end testing with LangSmith
   - Performance testing

**Deliverables**:
- UI with LangSmith integration
- Database schema updates
- Comprehensive documentation
- Test suite

---

## Configuration

### Environment Variables

**Required**:
```bash
# LangSmith API Key (get from https://smith.langchain.com)
LANGCHAIN_API_KEY=ls__your_api_key_here

# Enable tracing
LANGCHAIN_TRACING_V2=true

# Project name (organize traces)
LANGCHAIN_PROJECT=research-agent-dev
```

**Optional**:
```bash
# Custom endpoint (for enterprise)
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

# Sampling rate (trace X% of calls, for high-volume production)
LANGSMITH_SAMPLING_RATE=1.0  # 1.0 = 100% (default)
```

### Project Organization

**LangSmith Projects**:
- `research-agent-dev` - Development and testing
- `research-agent-phase1` - Phase 1 (search collection) traces
- `research-agent-phase2` - Phase 2 (LLM processing) traces
- `research-agent-prod` - Production traces
- `research-agent-examples` - Educational examples

**Tagging Strategy**:
- `phase:search-collection` or `phase:llm-processing`
- `company:<company_name>` (e.g., `company:bitmovin`)
- `model:<provider>:<model>` (e.g., `model:openai:gpt-4`)
- `prompt_version:<hash>` (e.g., `prompt_version:a3f5c2`)
- `workflow:<function>` (e.g., `workflow:full_research_pipeline`)

---

## Testing Strategy

### Unit Tests

**Location**: `tests/test_langsmith_integration.py`

**Tests**:
- Callback handler initialization
- Token usage calculation
- Cost calculation per model
- Trace metadata creation
- Error handling (LangSmith unavailable)

### Integration Tests

**Location**: `tests/test_langsmith_workflows.py`

**Tests**:
- Phase 1 tracing end-to-end
- Phase 2 tracing end-to-end
- Full pipeline tracing
- Dataset creation from Phase 1 results
- Model comparison workflows

### Manual Testing

**Test Cases**:
1. **Basic Tracing**: Run simple LLM call, verify trace in LangSmith
2. **Phase 1**: Run search collection, verify traces
3. **Phase 2**: Run LLM processing, verify traces and metadata
4. **Error Handling**: Force failure, verify error trace
5. **Cost Tracking**: Run with OpenAI, verify cost calculation
6. **Model Comparison**: Run multiple models, compare in LangSmith
7. **UI Integration**: Run from Streamlit, click through to LangSmith

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **LangSmith API Rate Limits** | High | Low | Implement sampling, use async uploads |
| **Additional Latency** | Medium | Low | Async callbacks, negligible overhead (<10ms) |
| **API Key Exposure** | High | Medium | Clear documentation, environment variable validation |
| **Increased Costs** | Medium | Low | LangSmith free tier sufficient, monitor usage |
| **Breaking Changes** | Medium | Low | Graceful degradation if LangSmith unavailable |
| **Data Privacy** | High | Low | Document what data is sent, allow opt-out |

---

## Success Criteria & Metrics

### Acceptance Criteria

**Must Have**:
- ✅ All LLM calls automatically traced when `LANGCHAIN_API_KEY` set
- ✅ Phase 1 and Phase 2 traces separated and tagged
- ✅ Token usage and cost visible in traces
- ✅ Agent reasoning visible in traces
- ✅ Documentation complete and clear
- ✅ Graceful degradation when LangSmith unavailable

**Should Have**:
- ✅ Dataset creation from Phase 1 results
- ✅ Model comparison workflows
- ✅ Streamlit UI integration
- ✅ Database trace ID storage
- ✅ Example traces with annotations

**Nice to Have**:
- ✅ Prompt versioning comparison
- ✅ Cost reporting dashboard
- ✅ Performance baselines and alerts

### Metrics to Track

**Post-Implementation** (3 months after launch):

| Metric | Baseline | Target |
|--------|----------|--------|
| Debug time per issue | ~30 min | <5 min |
| Prompt iteration time | ~2 hours (re-run searches) | <15 min (Phase 2 only) |
| Cost visibility | 0% | 100% |
| Model comparison frequency | Never | 2-3x per project |
| Developer satisfaction | N/A | >4/5 on surveys |

---

## Dependencies

### External Services

- **LangSmith Account**: Free tier sufficient for development
  - Sign up: https://smith.langchain.com
  - Free tier: 5,000 traces/month
  - Paid tier: $39/month (25k traces)

### Python Packages

**Already Installed**:
- `langsmith>=0.0.60` (in `requirements.txt`)
- `langchain` (base library)

**No Additional Dependencies Required**

### Infrastructure

- **Internet Access**: Required for LangSmith API calls
- **Minimal Latency Impact**: <10ms per LLM call (async callbacks)
- **Storage**: Trace data stored in LangSmith cloud (not local)

---

## Future Enhancements (Out of Scope for v1)

### Advanced Features

1. **Custom Evaluators**:
   - Automated quality scoring of LLM outputs
   - Custom metrics beyond token/cost tracking
   - Integration with validation framework

2. **Real-Time Alerting**:
   - Slack/email alerts for errors
   - Performance degradation alerts
   - Cost threshold alerts

3. **Advanced Analytics**:
   - Trend analysis over time
   - A/B testing framework
   - Anomaly detection

4. **Multi-Tenant Support**:
   - Separate projects per customer
   - Team collaboration features
   - Access control and permissions

5. **LangSmith Hub Integration**:
   - Publish prompts to LangSmith Hub
   - Share datasets with community
   - Reusable evaluator templates

---

## Documentation Deliverables

### Implementation Documentation

1. **`docs/implemented/LANGSMITH_INTEGRATION.md`**:
   - Complete integration guide
   - Architecture overview
   - Code examples
   - Troubleshooting

2. **`docs/reference/LANGSMITH_USAGE_GUIDE.md`**:
   - How-to guides for common tasks
   - Viewing and analyzing traces
   - Creating datasets
   - Comparing models
   - Cost tracking

3. **Updated `README.md`**:
   - LangSmith setup instructions
   - Quick start guide
   - Link to detailed documentation

### Educational Documentation

4. **Blog Post**: "Comprehensive Observability with LangSmith"
   - Why observability matters
   - LangSmith integration walkthrough
   - Real-world debugging examples
   - Model comparison tutorial

5. **Video Tutorial** (Optional):
   - Screen recording of LangSmith in action
   - Debugging a real agent failure
   - Comparing models with datasets

---

## Glossary

- **Trace**: A complete record of an LLM execution, including inputs, outputs, metadata
- **Run**: A single execution of a chain/agent/LLM
- **Dataset**: A collection of input/output examples for model evaluation
- **Project**: A LangSmith workspace for organizing traces
- **Tag**: A label for filtering and organizing traces
- **Callback Handler**: LangChain component that captures execution events
- **Sampling**: Tracing only a percentage of executions (for high-volume production)

---

## Appendix A: Cost Analysis

### LangSmith Pricing

| Tier | Traces/Month | Cost | Best For |
|------|--------------|------|----------|
| **Hobby** | 5,000 | Free | Development, learning |
| **Plus** | 25,000 | $39/month | Small teams, prototypes |
| **Team** | 100,000 | $199/month | Production, multiple projects |
| **Enterprise** | Custom | Custom | Large organizations |

**Recommendation**: Start with Hobby tier, upgrade to Plus if needed.

### Operational Costs

**Impact on Existing Costs**:
- **Latency**: <10ms per trace (negligible)
- **Network**: ~5KB per trace (minimal)
- **Compute**: Async callbacks, no measurable CPU impact

**Total Additional Cost**: $0-39/month (LangSmith subscription only)

---

## Appendix B: Example Trace Structure

```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "project": "research-agent-phase2",
  "name": "phase2_process_with_llm",
  "start_time": "2025-11-06T10:30:00Z",
  "end_time": "2025-11-06T10:30:15Z",
  "duration_ms": 15000,
  "tags": [
    "phase:llm-processing",
    "company:bitmovin",
    "model:openai:gpt-4"
  ],
  "metadata": {
    "company_name": "BitMovin",
    "model_provider": "openai",
    "model_name": "gpt-4",
    "prompt_version": "a3f5c2",
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "inputs": {
    "instructions": "Research the following company...",
    "search_results": [...]
  },
  "outputs": {
    "company_info": {
      "company_size": "51-200",
      "revenue_range": "$10M-50M",
      ...
    }
  },
  "metrics": {
    "prompt_tokens": 3500,
    "completion_tokens": 800,
    "total_tokens": 4300,
    "cost_usd": 0.12,
    "latency_ms": 12000
  },
  "error": null,
  "runs": [
    {
      "name": "ChatOpenAI.invoke",
      "type": "llm",
      "inputs": {...},
      "outputs": {...},
      "metrics": {...}
    }
  ]
}
```

---

## Appendix C: LangSmith Setup Quickstart

### Step 1: Create LangSmith Account

1. Go to https://smith.langchain.com
2. Sign up with GitHub or email
3. Create a new API key
4. Copy the API key (starts with `ls__`)

### Step 2: Configure Environment

```bash
# Add to .env file
echo "LANGCHAIN_API_KEY=ls__your_api_key_here" >> .env
echo "LANGCHAIN_TRACING_V2=true" >> .env
echo "LANGCHAIN_PROJECT=research-agent-dev" >> .env
```

### Step 3: Test Integration

```bash
# Run test script
python scripts/test_langsmith_basic.py

# Check LangSmith UI
# Go to https://smith.langchain.com/projects/research-agent-dev
# You should see a trace for the test run
```

### Step 4: Run Research Agent

```python
from src.research.workflows import phase2_process_with_llm

# This will automatically trace to LangSmith
result = phase2_process_with_llm(
    company_name="BitMovin",
    instructions_path="examples/instructions/research_instructions.md",
    llm_provider="openai",
    llm_model="gpt-4"
)

# Check trace in LangSmith UI
print(f"Trace URL: https://smith.langchain.com/...")
```

---

**Document End**

**Next Steps**:
1. Review and approve this PRD
2. Create GitHub issues for each implementation phase
3. Set up LangSmith account and test basic tracing
4. Begin Phase 1 implementation

**Questions or Feedback**: Contact project maintainer

