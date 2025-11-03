# Testing Framework Thesis: LLM Output Validation with Prompt Engineering

## Executive Summary

This document outlines the **thesis** (core approach and reasoning) for a new testing framework that enables systematic prompt engineering through LLM-graded validation. The goal is to enable data-driven prompt improvement by tracking accuracy changes as prompts evolve.

---

## Core Thesis

### The Problem

1. **Prompt Engineering is Trial and Error**: Currently, we modify prompts and hope they work better, but have no systematic way to measure improvement.

2. **No Ground Truth**: We don't have a reliable "correct" answer to compare against, making it hard to measure model accuracy objectively.

3. **No Historical Tracking**: We can't compare how different prompt versions perform over time or across different companies.

4. **Subjective Validation**: Manual validation is time-consuming and inconsistent.

### The Solution

**Use Gemini 2.5 Pro as Ground Truth, Grade Other Models with Gemini Flash, and Track Prompt Versions**

This approach:
- Treats Gemini Pro output as the "correct" answer (assumed correct)
- Uses Gemini Flash to intelligently grade other models' outputs field-by-field
- Stores all outputs in a database linked to prompt versions
- Enables systematic comparison of prompt versions across companies and time

---

## Key Principles

### 1. Gemini Pro as Ground Truth (with Optional Validation)

**Why**: Gemini 2.5 Pro is a high-quality model. For testing purposes, we assume its output is correct. This gives us a consistent baseline to compare against.

**How**: 
- First, run the agent with Gemini Pro to get "ground truth" output
- Cache this for 24 hours (to avoid unnecessary API calls)
- All other models are graded against this output

**Validation Strategy** (Optional - Future Enhancement):
> **Note**: Database structure supports validation, but workflow implementation is deferred to later phase when time permits.

- **Database Fields Ready**: Structure includes validation status fields for future use
- **Initial Phase**: Ground truth marked as 'unvalidated' but still usable
- **Future Implementation**: When time permits, add:
  - Manual review workflow for initial companies
  - Flagging system (validated, needs_review, disputed)
  - Human override capability with audit trail
  - Periodic spot checks (e.g., 10% of runs)

**Database Schema** (Implemented in Phase 1, used in future phase):
```sql
-- Add to llm_output_validation table (structure only, workflow deferred)
ground_truth_status VARCHAR(50) DEFAULT 'unvalidated'  -- Ready for future use
human_validated_at TIMESTAMP NULL                       -- Populated when validation added
validation_notes TEXT NULL                              -- For future manual reviews
```

**Benefits**:
- Consistent baseline for all comparisons
- No need to maintain manual baseline files
- Automatically updates as model capabilities improve
- **Database ready for validation when time permits** (no schema changes needed later)
- Can start using immediately without validation workflow

### 2. LLM-Based Grading (Gemini Flash)

**Why**: Hard-coded validation rules are brittle. An LLM can understand nuance, synonyms, and context better than string matching.

**How**:
- For each field, Gemini Flash receives:
  - Field name (e.g., "industry")
  - Correct value (from Gemini Pro)
  - Actual value (from model being graded)
- Gemini Flash returns:
  - Accuracy percentage (0-100)
  - Match type (exact, semantic, partial, none)
  - Brief explanation
  - Confidence score (0-1)

**Grading Output Structure**:
```python
{
    "field_name": "industry",
    "accuracy_score": 85,  # 0-100
    "match_type": "semantic",  # exact | semantic | partial | none
    "explanation": "Gemini said 'SaaS' while model said 'Software as a Service' - semantically equivalent",
    "critical_field": true,  # Some fields matter more
    "confidence": 0.9  # Grader's confidence
}
```

**Benefits**:
- Handles variations in wording naturally
- Understands semantic similarity
- Provides explanations for scores
- More flexible than regex/keyword matching
- Confidence scores help identify uncertain gradings

### 3. Prompt Versioning in Database

**Why**: Both agent prompts AND grading prompts evolve. We need to track which versions were used in each test to understand what changes improved (or degraded) accuracy.

**How**:
- **Agent prompts** are stored in database with version numbers
- **Grading prompts** are stored separately with their own versions
- Each test run links to an agent prompt version
- Each validation result links to a grading prompt version
- Can compare accuracy across prompt versions

**Grading Prompt Requirements**:
1. Clear scoring rubric (what constitutes 100%, 75%, 50%, 0%)
2. Handle missing/null values explicitly
3. Account for semantic equivalence (e.g., "AI/ML" vs "Artificial Intelligence")
4. Provide reasoning with each score
5. Be deterministic when possible (reduce variance)

**Benefits**:
- Clear history of prompt changes for both agent and grading
- Easy A/B testing of prompts
- See correlation between prompt changes and accuracy
- Rollback to previous versions if needed
- Track grading consistency over time

### 4. Test Suite Concept (Multiple Companies)

**Why**: Testing on a single company may not reveal real improvements. Testing across multiple companies gives more reliable results.

**How**:
- Test runs can be grouped into "test suites"
- Each suite tests the same prompt version across multiple companies
- Aggregate accuracy scores across companies in the suite

**Company Selection Strategy**:

**Diversity Criteria**:
1. **Industry Variety**: Different industries (SaaS, Hardware, Fintech, etc.)
2. **Company Size**: Mix of startups, mid-size, enterprise
3. **Data Availability**: Range from data-rich to sparse
4. **Complexity**: Simple vs. complex business models
5. **Known Difficulty**: Include both "easy" and "challenging" companies

**Recommended Starting Suite** (5 companies):
1. Well-known SaaS (easy baseline)
2. Hardware/physical product (different vocabulary)
3. Emerging startup (limited data)
4. Multi-product enterprise (complexity)
5. Non-English name/global company (internationalization test)

**Suite Evolution**:
- Start with 3-5 companies
- Add "regression suite" of companies that previously revealed issues
- Maintain "golden set" of representative companies for consistency

**Benefits**:
- More robust evaluation across diverse companies
- Can identify if improvements are general or company-specific
- Better statistical confidence in results
- Tests generalization capabilities

### 5. Database as Source of Truth

**Why**: All data stored in database enables historical analysis, comparison, and programmatic access.

**How**:
- All model outputs stored in `llm_output_validation` table
- All accuracy scores stored in `llm_output_validation_results` table
- All test runs tracked with prompt versions and companies

**Benefits**:
- Historical comparison over time
- Query and analyze trends
- Export data for external analysis
- Reproducibility (can rerun analyses on historical data)

---

## Workflow

### Single Company Test

1. **Create Test Run**: Record prompt version, company name, test metadata
2. **Get Ground Truth**: Run Gemini Pro (or use cached if <24hrs old)
3. **Test Other Models**: Run agent for all other models with same prompt
4. **Grade Outputs**: Use Gemini Flash to grade each model's output field-by-field
5. **Store Results**: Save accuracy scores to database

### Multi-Company Test Suite

1. **Create Test Suite**: Name for grouping multiple companies
2. **Run Per Company**: Execute single company test for each company
3. **Aggregate Results**: Calculate average accuracy across all companies
4. **Compare**: Compare aggregated scores across prompt versions

---

## Evaluation Metrics

### Aggregation Methods

1. **Simple Average**: Mean of all field scores
2. **Weighted Average**: Critical fields count more (e.g., industry, target_market = 2x weight)
3. **Pass/Fail Threshold**: Score >= 80% considered "passing"
4. **Field-Level Pass Rate**: % of fields scoring >= threshold

### Success Thresholds

- **Excellent**: >= 90% average accuracy
- **Good**: 80-89%
- **Acceptable**: 70-79%
- **Needs Improvement**: < 70%

### Scoring Interpretation

- **100%**: Exact match
- **70-99%**: Close/similar meanings
- **40-69%**: Related but different
- **20-39%**: Partially correct
- **0-19%**: Completely wrong or missing

---

## Cost & Performance Analysis

### Token Usage Tracking

**Critical for Cost Analysis**:
- All agent runs (Gemini Pro, other models) track: `input_tokens`, `output_tokens`, `total_tokens`
- All grading runs (Gemini Flash) track: `grading_input_tokens`, `grading_output_tokens`, `grading_total_tokens`
- Costs automatically calculated based on model pricing: `estimated_cost_usd`, `grading_cost_usd`
- Stored in database for historical analysis

**Benefits**:
- Track actual costs vs estimates
- Identify expensive prompts (long prompts = high input tokens)
- Identify expensive companies (complex = high output tokens)
- Compare cost across prompt versions
- Budget forecasting for future test runs

### API Cost Estimation

**Per Company Test Run** (estimated):
- Gemini Pro (ground truth): ~1M tokens = ~$3.50
- Gemini Flash (grading ~20 fields): ~500K tokens = ~$0.50
- Local models (Llama): $0 (compute only)
- **Total per company**: ~$4.00

**Actual costs tracked in database per run**

**Test Suite (5 companies)**:
- Ground truth (cached after first): $3.50 initial, $0 subsequent
- Grading 3 models × 5 companies: $7.50
- **Total**: ~$11 per test suite (first run)
- **Total**: ~$7.50 per test suite (cached ground truth)

**Monthly Budget Estimate**:
- 4 prompt versions/month
- 5 companies per test
- 3 models to grade
- **Monthly cost**: ~$44-60 (based on actual tracking)

### Performance Optimization

1. **Cache Ground Truth**: 24-hour cache reduces redundant API calls
2. **Batch Grading**: Grade multiple fields in single API call
3. **Parallel Execution**: Run multiple company tests simultaneously (future)
4. **Smart Caching**: Cache by (company, prompt_version, model) tuple

---

## Edge Cases & Error Handling

### Model Output Issues

| Issue | Handling Strategy |
|-------|------------------|
| **Malformed JSON** | Parse error → 0% score + flag for review |
| **Missing Fields** | 0% for missing field, grade present fields |
| **Timeout** | Retry once, then mark as failed run |
| **Refusal** | ("I cannot...") → 0% + flag as refusal |
| **Hallucination** | Grader detects + low confidence → flag |
| **Partial Response** | Grade what's present, note incomplete |

### Grading Edge Cases

| Case | Handling |
|------|----------|
| **Both Empty** | 100% (both models provided nothing) |
| **Ground Truth Empty** | Flag for review (shouldn't happen) |
| **Contradictory Data** | Grade as-is, flag for human review |
| **Ambiguous Equivalence** | Grader provides reasoning, human spot-check |

---

## Reproducibility & Debugging

### Required Metadata

```python
{
    "test_run_id": "uuid",
    "timestamp": "2025-01-15T10:30:00Z",
    "agent_prompt_version": "1.2",
    "grading_prompt_version": "1.0",
    "model_name": "gemini-1.5-pro",
    "model_config": {"temperature": 0, "max_tokens": 8000},
    "langchain_version": "0.1.0",
    "environment": "production"
}
```

### Debug Mode Features

1. Store full agent reasoning (intermediate steps)
2. Store raw LLM responses before parsing
3. Store grading prompts and responses
4. Flag anomalies (unusually low scores, errors, timeouts)

### Comparison Tools

- Diff tool to compare two test runs field-by-field
- Highlight which fields improved/degraded
- Show reasoning for score changes

---

## Expected Outcomes

### Prompt Engineering Workflow

1. **Create Prompt v1.0**: Initial prompt version
2. **Run Test Suite**: Test across 5 companies, get baseline accuracy (e.g., 75%)
3. **Modify Prompt**: Edit prompt based on findings
4. **Create Prompt v1.1**: Save new version
5. **Run Test Suite**: Test again across same 5 companies
6. **Compare**: See if accuracy improved (e.g., now 82%)
7. **Iterate**: Continue improving based on data

### Analysis Capabilities

- **Compare Prompt Versions**: See accuracy difference between v1.0 and v1.1
- **Company-Specific Insights**: Identify which companies are harder/easier
- **Model Comparison**: Compare how different models perform
- **Trend Analysis**: Track accuracy over time as prompts improve
- **Cost Analysis**: Track costs by prompt version, company, and model
  - Which prompt versions are most expensive?
  - Which companies require more tokens?
  - What's the cost difference between models?
  - Budget vs actual spending

---

## Interpreting Results & Taking Action

### Analysis Patterns

**1. Overall Low Accuracy (<70%)**
→ **Action**: Fundamental prompt issue, major revision needed
→ **Check**: Is ground truth correct? Is task too complex?

**2. Specific Fields Always Fail**
→ **Action**: Add field-specific instructions to prompt
→ **Example**: If "target_market" always scores low, add examples to prompt

**3. Model-Specific Issues**
→ **Action**: May need model-specific prompt variants
→ **Example**: Llama needs more explicit structure instructions

**4. Company-Specific Failures**
→ **Action**: Identify what makes those companies hard
→ **Example**: Companies with sparse data may need different research strategy

**5. Inconsistent Scores Across Runs**
→ **Action**: Grading prompt may be too subjective
→ **Solution**: Refine grading prompt, lower temperature

### Prompt Improvement Workflow

1. Run Test Suite → Get baseline accuracy
2. Analyze Results → Identify failure patterns
3. Modify Prompt → Based on specific issues found
4. Increment Version → Create new prompt version
5. Run Test Suite → Compare with previous version
6. Evaluate Change → Did accuracy improve?
7. Iterate → Continue improving based on data

---

## Key Design Decisions

### Why Gemini Flash for Grading?

- **Fast**: Faster than Pro, lower cost
- **Good Enough**: For grading, Flash is sufficient quality
- **Consistent**: Same model used for all grading ensures consistency

### Why 24-Hour Cache for Ground Truth?

- **Efficiency**: Avoid unnecessary API calls
- **Cost**: Reduce API costs
- **Stability**: Ground truth stays stable for the test run period
- **Flexibility**: Can force refresh if needed

### Why Test Suites Instead of Single Test Runs?

- **Robustness**: Multiple companies give more reliable metrics
- **Generalization**: Ensures improvements aren't company-specific
- **Confidence**: Better statistical basis for decisions

### Why Database Storage Instead of Files?

- **Queryable**: Can run SQL queries for analysis
- **Historical**: Keep all past results
- **Relational**: Link test runs, prompt versions, companies
- **Programmatic**: Easy to build tools on top

---

## Success Criteria

### Core Requirements (Phase 1-4)

1. ✅ Can run tests for a single company and get accuracy scores **within 5 minutes**
2. ✅ Can run test suites across multiple companies **with cost under $15 per suite**
3. ✅ Can compare accuracy across prompt versions **with statistical confidence**
4. ✅ Can see **>10% accuracy improvement** when prompt genuinely improves
5. ✅ Can identify which companies are harder/easier **with variance metrics**
6. ✅ Can identify which fields are most problematic **with field-level analytics**
7. ✅ Can track accuracy trends over time **with automated regression detection**
8. ✅ **Grading consistency: Same input → within 5% score variance across 3 runs**
9. ✅ **Actionable insights: Clear recommendations from failed tests**
10. ✅ **Database structure supports ground truth validation** (workflow deferred)

### Future Enhancements (Optional)

11. 🔮 **Ground truth quality: >90% validation rate on manual spot checks** (when validation workflow added)
12. 🔮 **Manual validation UI** for reviewing and correcting ground truth
13. 🔮 **Automated flagging** of low-confidence ground truth for review

---

## Potential Concerns & Mitigations

### Concern: Gemini Pro Might Be Wrong

**Mitigation**: 
- If Gemini Pro output is clearly wrong, we can manually override or regenerate
- Over time, if we see consistent issues, we can add validation rules
- The framework allows manual review of ground truth before running tests

### Concern: Gemini Flash Grading Might Be Inconsistent

**Mitigation**:
- We store the grading prompt and responses for audit
- Can manually review gradings that seem off
- Over time, we can refine the grading prompt to be more consistent
- Multiple runs on same data should produce similar scores

### Concern: 24-Hour Cache Might Be Too Long/Short

**Mitigation**:
- Configurable cache duration
- Can force refresh when needed
- Can manually invalidate cache if ground truth is known to be wrong

### Concern: Testing Multiple Companies Takes Too Long

**Mitigation**:
- Test suites can be run in parallel (future enhancement)
- Can start with smaller suites (e.g., 2-3 companies)
- Can run tests asynchronously
- Cache ground truth across test runs to avoid redundant calls

---

## Future Enhancements (Out of Scope for Initial Implementation)

### Phase 2 Enhancements
1. **Manual Validation Workflow**: UI for reviewing and correcting ground truth
2. **Parallel Execution**: Run multiple company tests in parallel
3. **Regression Detection**: Alert when accuracy degrades
4. **Automated Testing**: Run tests on every prompt version change

### Advanced Features
5. **Automated Prompt Optimization**: Use results to suggest prompt improvements
6. **Field-Level Prompting**: Different prompts for different fields
7. **Statistical Analysis**: Confidence intervals, significance testing
8. **Multi-Model Ground Truth**: Use ensemble of models for ground truth
9. **Cost Optimization Suggestions**: Identify expensive patterns and suggest alternatives
10. **A/B Testing Framework**: Automated prompt comparison experiments

---

## Summary

This framework transforms prompt engineering from guesswork into a data-driven process:

- **Before**: Modify prompt → Hope it's better → No clear measure
- **After**: Modify prompt → Run test suite → See accuracy change → Iterate

The key insight is using **Gemini Pro as ground truth** and **Gemini Flash for grading**, combined with **prompt versioning** and **test suite tracking**, to enable systematic prompt improvement.

---

**Status**: 📋 **THESIS UPDATED & ENHANCED - READY FOR IMPLEMENTATION**  
**Last Updated**: 2025-11-03

**Key Enhancements**:
- ✅ Ground truth validation strategy with flagging system (structure only, workflow deferred)
- ✅ Grading prompt versioning and requirements
- ✅ Enhanced evaluation metrics with weighted scoring
- ✅ **Token usage tracking for comprehensive cost analysis**
- ✅ **Automated cost calculation and analytics**
- ✅ Cost & performance analysis with optimization strategies
- ✅ Company selection guidance for test suites
- ✅ Edge case handling strategies
- ✅ Reproducibility requirements
- ✅ Actionable insights framework
- ✅ Specific, measurable success criteria

