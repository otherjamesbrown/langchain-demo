# Improved Architecture Proposal

## Overview

A **two-phase, data-persistent architecture** that separates search execution from LLM processing, enabling model testing and validation.

## Phase 1: Search Collection

### Workflow
1. Load CSV → Extract company names
2. Generate search queries for each company (template-based or LLM-generated)
3. Execute searches via search API
4. Store raw results with full metadata

### Database Schema: `research_queries` table
```sql
- id (PK)
- company_name
- query_text (e.g., "BitMovin employee count")
- query_type (e.g., "company_size", "revenue", "general")
- status (pending, completed, failed)
- created_at
```

### Database Schema: `search_results` table (enhanced)
```sql
- id (PK)
- research_query_id (FK to research_queries)
- search_provider ('tavily' or 'serper')
- raw_results (JSON) - Full structured results
- results_summary (TEXT) - Formatted summary
- num_results (INT)
- execution_time_ms (FLOAT)
- success (BOOL)
- error_message (TEXT)
- created_at (TIMESTAMP)
```

### Key Features
- **Query Templates**: Predefined queries like "{{company}} employee count", "{{company}} revenue"
- **Search Result Storage**: Full JSON of all results (title, URL, content, relevance)
- **Idempotent**: Can re-run searches for failed queries without affecting completed ones
- **Provider Tracking**: Know which provider returned what data

## Phase 2: LLM Processing

### Workflow
1. Load prompt templates/instructions
2. For each company, gather all search results
3. Construct prompt: Instructions + Search Results + Company Name
4. Run through LLM
5. Store: prompt version, LLM model, search results used, output

### Database Schema: `processing_runs` table
```sql
- id (PK)
- company_name
- prompt_version (hash or version string)
- prompt_template (TEXT) - The actual prompt used
- llm_model (e.g., "gpt-4", "claude-3-opus", "llama-2-7b")
- llm_provider (e.g., "openai", "anthropic", "local")
- search_results_ids (JSON array) - Links to search_results
- input_context (JSON) - All search results combined
- output (JSON) - Structured CompanyInfo
- raw_output (TEXT) - Unparsed LLM response
- execution_time_seconds (FLOAT)
- temperature (FLOAT)
- success (BOOL)
- error_message (TEXT)
- created_at (TIMESTAMP)
```

### Key Features
- **Reproducibility**: Same search results → Same LLM input
- **Model Comparison**: Run same data through multiple models
- **Prompt Versioning**: Track prompt improvements
- **Audit Trail**: Full traceability from search to output

## Phase 3: Validation & Testing

### New Capabilities
1. **A/B Testing Models**: Compare outputs from different LLMs on same data
2. **Prompt Testing**: Test different prompts with same search results
3. **Quality Metrics**: Measure consistency, accuracy, completeness
4. **Regression Testing**: Ensure model updates don't degrade performance

### Database Schema: `validation_results` table
```sql
- id (PK)
- processing_run_id (FK)
- validation_type (e.g., "completeness", "accuracy", "consistency")
- score (FLOAT)
- details (JSON)
- validated_by (e.g., "human", "automated")
- created_at (TIMESTAMP)
```

## Advantages of This Architecture

### 1. Cost Efficiency
- Search once, process many times
- No need to re-search when testing new models/prompts
- API costs only for searches, not for model testing

### 2. Reproducibility
- Same inputs → Same outputs (with same model)
- Can verify model behavior hasn't changed
- Can debug issues by examining stored search results

### 3. Testing & Validation
- Test multiple models on identical data
- Compare prompt variations
- Measure model performance objectively
- Build regression test suites

### 4. Data Integrity
- Full audit trail
- Know exactly what data each model saw
- Can re-process with improved prompts/models
- Historical comparison of results

### 5. Flexibility
- Change models without re-searching
- Update prompts without new API costs
- Test different temperature settings
- Experiment with prompt engineering

## Implementation Components Needed

### 1. Query Generator
```python
def generate_search_queries(company_name: str, query_templates: list) -> list[dict]:
    """Generate structured search queries from templates."""
    queries = []
    for template in query_templates:
        queries.append({
            "company_name": company_name,
            "query_text": template.format(company=company_name),
            "query_type": template["type"]
        })
    return queries
```

### 2. Search Executor
```python
def execute_search_queries(queries: list, provider: str) -> list[SearchResult]:
    """Execute searches and store raw results."""
    # Returns list with search_query_id, raw_results, metadata
```

### 3. Prompt Builder
```python
def build_prompt(instructions: str, search_results: list, company_name: str) -> str:
    """Combine instructions with search results into final prompt."""
```

### 4. LLM Processor
```python
def process_with_llm(prompt: str, llm_config: dict) -> dict:
    """Run prompt through LLM and store all metadata."""
```

### 5. Validator
```python
def validate_output(processing_run: ProcessingRun) -> ValidationResult:
    """Validate completeness, accuracy, etc."""
```

## Migration Path

1. **Add new database tables** (research_queries, enhanced search_results, processing_runs)
2. **Create Phase 1 workflow** (query generation + search execution)
3. **Create Phase 2 workflow** (LLM processing)
4. **Add validation framework**
5. **Keep old ReAct agent** as option for quick/iterative searches

## Example Usage

```python
# Phase 1: Collect searches
queries = generate_queries("BitMovin", query_templates)
search_results = execute_searches(queries, provider="serper")

# Phase 2: Process with different models
for model in ["gpt-4", "claude-3-opus", "llama-2-7b"]:
    result = process_with_llm(
        prompt=build_prompt(instructions, search_results, "BitMovin"),
        llm_config={"model": model, "temperature": 0.7}
    )
    
# Phase 3: Compare results
comparison = compare_outputs(results)
```

