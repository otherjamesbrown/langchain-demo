# Two-Phase Research Architecture

## Overview

The improved two-phase architecture separates **search collection** from **LLM processing**, enabling:
- Model testing and comparison
- Prompt engineering without re-searching
- Full audit trails and reproducibility
- Cost efficiency (search once, test many times)

## Architecture Components

### Database Schema

#### New Tables
1. **`research_queries`** - Structured search queries for each company
2. **`processing_runs`** - LLM processing runs with full metadata
3. **`validation_results`** - Validation scores and metrics

#### Enhanced Tables
1. **`search_history`** - Now includes `raw_results` JSON field

### Phase 1: Search Collection

**Purpose**: Collect all search data upfront and store raw results.

**Components**:
- `query_generator.py` - Generates structured queries from templates
- `search_executor.py` - Executes searches and stores raw JSON results

**Workflow**:
1. Load companies from CSV
2. Generate research queries (e.g., "BitMovin employee count", "BitMovin revenue")
3. Execute searches via search API
4. Store raw results with full metadata (provider, timestamp, raw JSON)

**Key Features**:
- Structured query generation
- Raw result storage (full JSON)
- Idempotent (can re-run failed queries)
- Provider tracking

### Phase 2: LLM Processing

**Purpose**: Process stored search results through LLMs with full tracking.

**Components**:
- `prompt_builder.py` - Combines instructions with search results
- `llm_processor.py` - Processes through LLM and stores all metadata

**Workflow**:
1. Load instructions/prompts
2. Retrieve search results for company
3. Build prompt: Instructions + Search Results
4. Process through LLM
5. Store: prompt version, LLM config, output, execution time

**Key Features**:
- Prompt versioning
- Full metadata tracking
- Multi-model processing support
- Reproducible (same inputs → same outputs)

### Validation & Testing

**Components**:
- `validation.py` - Validation utilities and comparison tools

**Capabilities**:
- Completeness validation
- Multi-model comparison
- Consensus detection
- Quality metrics

## Usage Examples

### Phase 1: Collect Searches

```python
from src.research.workflows import phase1_collect_searches

# Collect searches for all companies in CSV
summary = phase1_collect_searches(
    csv_path="examples/companies/sample_companies.csv",
    provider="serper"  # or "tavily"
)
```

### Phase 2: Process with Single Model

```python
from src.research.workflows import phase2_process_with_llm

# Process company with specific LLM
result = phase2_process_with_llm(
    company_name="BitMovin",
    instructions_path="examples/instructions/research_instructions.md",
    llm_provider="openai",
    llm_model="gpt-4",
    temperature=0.7
)
```

### Phase 2: Compare Multiple Models

```python
from src.research.workflows import phase2_process_multiple_models

# Process same data with multiple models
results = phase2_process_multiple_models(
    company_name="BitMovin",
    instructions_path="examples/instructions/research_instructions.md",
    models=[
        {"provider": "openai", "model": "gpt-4"},
        {"provider": "anthropic", "model": "claude-3-opus"},
        {"provider": "local", "model": "llama-2-7b"}
    ]
)
```

### Full Pipeline

```python
from src.research.workflows import full_research_pipeline

# Complete workflow: Phase 1 + Phase 2
summary = full_research_pipeline(
    csv_path="examples/companies/sample_companies.csv",
    instructions_path="examples/instructions/research_instructions.md",
    llm_provider="openai",
    llm_model="gpt-4"
)
```

### Validation

```python
from src.research.validation import (
    validate_processing_run,
    compare_processing_runs
)

# Validate a processing run
validations = validate_processing_run(processing_run_id=1)

# Compare multiple runs
comparison = compare_processing_runs([run1, run2, run3])
```

## Command Line Usage

### Test Script

```bash
# Phase 1 only
python scripts/test_two_phase.py --phase 1

# Phase 2 only (requires Phase 1 to be run first)
python scripts/test_two_phase.py --phase 2

# Both phases
python scripts/test_two_phase.py --phase both

# Multi-model comparison
python scripts/test_two_phase.py --phase multi

# Specific company
python scripts/test_two_phase.py --phase 2 --company "BitMovin"
```

## Advantages

### 1. Cost Efficiency
- Search once, process many times
- No API costs for model testing
- Re-run processing without new searches

### 2. Reproducibility
- Same inputs → Same outputs
- Full audit trail
- Version tracking for prompts and models

### 3. Testing & Validation
- Test multiple models on identical data
- Compare prompt variations
- Measure performance objectively
- Regression testing

### 4. Data Integrity
- Know exactly what each model saw
- Historical comparison
- Debug issues with stored search results

### 5. Flexibility
- Change models without re-searching
- Update prompts without API costs
- Experiment with prompt engineering
- Test different temperature settings

## Database Queries

### Get all searches for a company
```python
from src.research.search_executor import get_search_results_for_company

results = get_search_results_for_company("BitMovin")
```

### Get processing runs for a company
```python
from src.database.schema import ProcessingRun, get_session

session = get_session()
runs = session.query(ProcessingRun).filter_by(company_name="BitMovin").all()
```

### Compare outputs
```python
from src.research.validation import compare_processing_runs

runs = session.query(ProcessingRun).filter_by(company_name="BitMovin").all()
comparison = compare_processing_runs(runs)
```

## Migration from Old Architecture

The old ReAct agent (`ResearchAgent`) is still available for quick/iterative research. The new architecture is recommended for:
- Production workflows
- Model testing and validation
- Cost-sensitive operations
- Reproducible research

You can use both architectures in the same codebase - they share the same database schema (backward compatible).

