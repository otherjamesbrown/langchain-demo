# Staged Implementation Plan - Testing Framework

> **📖 See Also**: 
> - [TESTING_FRAMEWORK_THESIS.md](./TESTING_FRAMEWORK_THESIS.md) for conceptual foundation
> - [TESTING_FRAMEWORK_PLAN.md](./TESTING_FRAMEWORK_PLAN.md) for detailed implementation specs

## Overview

This document breaks down the testing framework implementation into **small, testable stages**. Each stage:
- ✅ Can be independently tested and verified
- ✅ Builds on previous stages
- ✅ Has clear deliverables and acceptance criteria
- ✅ Includes verification steps before moving to the next stage

**Estimated Total Time**: 4-5 weeks (working incrementally)

---

## Stage 0: Prerequisites & Setup

**Goal**: Verify current state and prepare for implementation

**Duration**: 30 minutes

**Tasks**:
1. Verify database connection works
2. Review existing `src/database/schema.py` structure
3. Identify where to add new tables
4. Verify `ResearchAgent` can be imported and used
5. Locate existing prompt files (`prompts/research-agent-prompt.md`)

**Verification**:
```bash
# Test database connection
python -c "from src.database.operations import get_session; s = get_session(); print('DB OK'); s.close()"

# Verify ResearchAgent exists
python -c "from src.agent.research_agent import ResearchAgent; print('Agent OK')"

# Check prompt file exists
ls prompts/research-agent-prompt.md
```

**Acceptance Criteria**:
- ✅ Database connection works
- ✅ Can import ResearchAgent
- ✅ Prompt file exists and is readable
- ✅ Understand current schema structure

---

## Stage 1: Database Schema - Core Tables (Part 1)

**Goal**: Add prompt versioning tables to database

**Duration**: 1-2 hours

**Tasks**:
1. Add `PromptVersion` table to `src/database/schema.py`
   - Fields: id, prompt_name, version, instructions_content, classification_reference_content, full_content, description, created_by, is_active, created_at
   - Unique constraint: (prompt_name, version)
   - Indexes: prompt_name, version, created_at
2. Add `GradingPromptVersion` table
   - Fields: id, version, prompt_template, scoring_rubric, description, is_active, consistency_score, created_at
   - Unique constraint: version
   - Index: version, created_at
3. Update `create_database()` function to create new tables
4. Test table creation

**Files to Modify**:
- `src/database/schema.py`

**Verification Script**:
```python
# test_stage1.py
from src.database.schema import PromptVersion, GradingPromptVersion, create_database
from src.database.operations import get_session

# Create tables
create_database()

# Verify tables exist
session = get_session()
try:
    # Check PromptVersion table
    count = session.query(PromptVersion).count()
    print(f"✅ PromptVersion table exists (count: {count})")
    
    # Check GradingPromptVersion table
    count = session.query(GradingPromptVersion).count()
    print(f"✅ GradingPromptVersion table exists (count: {count})")
    
    # Test unique constraint
    from src.database.schema import PromptVersion
    test = PromptVersion(
        prompt_name="test-prompt",
        version="1.0",
        instructions_content="test",
        full_content="test"
    )
    session.add(test)
    session.commit()
    print("✅ Can create prompt version")
    
    # Try duplicate (should fail)
    try:
        duplicate = PromptVersion(
            prompt_name="test-prompt",
            version="1.0",
            instructions_content="test2",
            full_content="test2"
        )
        session.add(duplicate)
        session.commit()
        print("❌ Unique constraint failed!")
    except Exception as e:
        print(f"✅ Unique constraint works: {e}")
        session.rollback()
    
    # Cleanup
    session.query(PromptVersion).filter(PromptVersion.prompt_name == "test-prompt").delete()
    session.commit()
    
finally:
    session.close()
```

**Acceptance Criteria**:
- ✅ Tables created successfully
- ✅ Unique constraints work
- ✅ Indexes created
- ✅ Can insert and query records

---

## Stage 2: Database Schema - Test Run Tables (Part 2)

**Goal**: Add test run and output storage tables

**Duration**: 1-2 hours

**Tasks**:
1. Add `TestRun` table to `src/database/schema.py`
   - Fields: id, test_name, company_name, test_suite_name, prompt_version_id, prompt_name, prompt_version, description, executed_by, created_at
   - Foreign key: prompt_version_id → prompt_versions.id
   - Indexes: test_name, company_name, test_suite_name, prompt_version_id
2. Add `LLMOutputValidation` table
   - All CompanyInfo fields as columns
   - Execution metadata (time, iterations, success, raw_output, error_message)
   - Token tracking fields (input_tokens, output_tokens, total_tokens, estimated_cost_usd)
   - Ground truth validation fields (ground_truth_status, human_validated_at, validation_notes)
   - Foreign key: test_run_id → test_runs.id
   - Indexes: test_run_id, test_name, company_name, model_name, model_provider
3. Update `create_database()` function
4. Test table creation and relationships

**Files to Modify**:
- `src/database/schema.py`

**Verification Script**:
```python
# test_stage2.py
from src.database.schema import TestRun, LLMOutputValidation, PromptVersion, create_database
from src.database.operations import get_session
from datetime import datetime

create_database()
session = get_session()

try:
    # Create test prompt version
    pv = PromptVersion(
        prompt_name="test-prompt",
        version="1.0",
        instructions_content="test",
        full_content="test"
    )
    session.add(pv)
    session.commit()
    
    # Create test run
    test_run = TestRun(
        test_name="llm-output-validation",
        company_name="BitMovin",
        prompt_version_id=pv.id,
        prompt_name=pv.prompt_name,
        prompt_version=pv.version
    )
    session.add(test_run)
    session.commit()
    
    # Create output record
    output = LLMOutputValidation(
        test_run_id=test_run.id,
        test_name="llm-output-validation",
        company_name="BitMovin",
        model_name="test-model",
        model_provider="test",
        company_name_field="BitMovin",
        industry="SaaS",
        success=True,
        input_tokens=1000,
        output_tokens=500,
        total_tokens=1500,
        estimated_cost_usd=0.01,
        ground_truth_status="unvalidated"
    )
    session.add(output)
    session.commit()
    
    # Verify relationships
    assert output.test_run.id == test_run.id
    assert test_run.prompt_version_obj.id == pv.id
    print("✅ Relationships work correctly")
    
    # Cleanup
    session.query(LLMOutputValidation).filter(LLMOutputValidation.test_run_id == test_run.id).delete()
    session.query(TestRun).filter(TestRun.id == test_run.id).delete()
    session.query(PromptVersion).filter(PromptVersion.id == pv.id).delete()
    session.commit()
    
finally:
    session.close()
```

**Acceptance Criteria**:
- ✅ Tables created successfully
- ✅ Foreign key relationships work
- ✅ Can create linked records
- ✅ JSON fields work (for products, competitors, key_personas)

---

## Stage 3: Database Schema - Results Table (Part 3)

**Goal**: Add accuracy results table

**Duration**: 1 hour

**Tasks**:
1. Add `LLMOutputValidationResult` table to `src/database/schema.py`
   - Foreign keys: output_id, test_run_id, grading_prompt_version_id
   - Field accuracy scores (JSON with structured data)
   - Aggregate scores (overall, required_fields, optional_fields, weighted)
   - Grading metadata (model, prompt version, response, confidence)
   - Token tracking for grading (input/output/total tokens, cost)
   - Indexes: output_id, test_run_id, test_name, company_name, model_name
2. Update `create_database()` function
3. Test JSON field storage for structured field scores

**Files to Modify**:
- `src/database/schema.py`

**Verification Script**:
```python
# test_stage3.py
from src.database.schema import (
    LLMOutputValidationResult, LLMOutputValidation, 
    TestRun, PromptVersion, GradingPromptVersion, create_database
)
from src.database.operations import get_session

create_database()
session = get_session()

try:
    # Create all linked records
    pv = PromptVersion(
        prompt_name="test-prompt", version="1.0",
        instructions_content="test", full_content="test"
    )
    gpv = GradingPromptVersion(
        version="1.0", prompt_template="test", scoring_rubric="test"
    )
    session.add_all([pv, gpv])
    session.commit()
    
    test_run = TestRun(
        test_name="test", company_name="BitMovin",
        prompt_version_id=pv.id, prompt_name=pv.prompt_name,
        prompt_version=pv.version
    )
    session.add(test_run)
    session.commit()
    
    output = LLMOutputValidation(
        test_run_id=test_run.id, test_name="test",
        company_name="BitMovin", model_name="test", model_provider="test",
        success=True
    )
    session.add(output)
    session.commit()
    
    # Create result with structured JSON
    field_scores = {
        "industry": {
            "score": 85,
            "match_type": "semantic",
            "explanation": "Close match",
            "confidence": 0.9
        },
        "company_size": {
            "score": 100,
            "match_type": "exact",
            "explanation": "Exact match",
            "confidence": 1.0
        }
    }
    
    result = LLMOutputValidationResult(
        output_id=output.id,
        test_run_id=test_run.id,
        test_name="test",
        company_name="BitMovin",
        model_name="test",
        model_provider="test",
        field_accuracy_scores=field_scores,
        overall_accuracy=92.5,
        required_fields_accuracy=90.0,
        optional_fields_accuracy=95.0,
        weighted_accuracy=91.0,
        graded_by_model="gemini-flash-latest",
        grading_prompt_version_id=gpv.id,
        grading_confidence=0.95,
        grading_input_tokens=500,
        grading_output_tokens=200,
        grading_total_tokens=700,
        grading_cost_usd=0.01
    )
    session.add(result)
    session.commit()
    
    # Verify JSON storage
    retrieved = session.query(LLMOutputValidationResult).first()
    assert retrieved.field_accuracy_scores["industry"]["score"] == 85
    print("✅ JSON field storage works")
    
    # Cleanup
    session.query(LLMOutputValidationResult).delete()
    session.query(LLMOutputValidation).delete()
    session.query(TestRun).delete()
    session.query(GradingPromptVersion).delete()
    session.query(PromptVersion).delete()
    session.commit()
    
finally:
    session.close()
```

**Acceptance Criteria**:
- ✅ Table created successfully
- ✅ Can store structured JSON in field_accuracy_scores
- ✅ All foreign keys work
- ✅ Can query and retrieve results

---

## Stage 4: Prompt Manager - Basic CRUD

**Goal**: Create prompt manager with basic operations

**Duration**: 2-3 hours

**Tasks**:
1. Create `src/prompts/__init__.py`
2. Create `src/prompts/prompt_manager.py` with `PromptManager` class
3. Implement `load_prompt_from_file()` - Parse markdown sections
4. Implement `create_version_from_file()` - Create prompt version from file
5. Implement `get_active_version()` - Get active version
6. Implement `get_version()` - Get specific version
7. Implement `list_versions()` - List all versions

**Files to Create**:
- `src/prompts/__init__.py`
- `src/prompts/prompt_manager.py`

**Verification Script**:
```python
# test_stage4.py
from src.prompts.prompt_manager import PromptManager
from pathlib import Path
from src.database.operations import get_session

# Test loading from file
prompt_path = Path("prompts/research-agent-prompt.md")
sections = PromptManager.load_prompt_from_file(prompt_path)
print(f"✅ Loaded prompt sections: {list(sections.keys())}")
assert "instructions" in sections
assert "full_content" in sections

# Test creating version
session = get_session()
try:
    pv = PromptManager.create_version_from_file(
        prompt_name="research-agent-prompt",
        prompt_path=prompt_path,
        version="1.0",
        description="Initial version",
        created_by="test",
        session=session
    )
    print(f"✅ Created prompt version: {pv.prompt_name}@{pv.version}")
    
    # Test retrieving
    active = PromptManager.get_active_version("research-agent-prompt", session=session)
    assert active.id == pv.id
    print("✅ Can retrieve active version")
    
    specific = PromptManager.get_version("research-agent-prompt", "1.0", session=session)
    assert specific.id == pv.id
    print("✅ Can retrieve specific version")
    
    versions = PromptManager.list_versions("research-agent-prompt", session=session)
    assert len(versions) >= 1
    print(f"✅ Can list versions ({len(versions)} found)")
    
    session.commit()
    
finally:
    session.close()
```

**Acceptance Criteria**:
- ✅ Can load prompts from markdown files
- ✅ Can create prompt versions
- ✅ Can retrieve versions
- ✅ Can list all versions

---

## Stage 5: Grading Prompt Manager

**Goal**: Create grading prompt manager

**Duration**: 1-2 hours

**Tasks**:
1. Create `src/prompts/grading_prompt_manager.py` with `GradingPromptManager` class
2. Implement `create_version()` - Create grading prompt version
3. Implement `get_active_version()` - Get active grading prompt
4. Implement `get_version()` - Get specific version
5. Create default grading prompt template (v1.0) with clear scoring rubric

**Files to Create**:
- `src/prompts/grading_prompt_manager.py`

**Verification Script**:
```python
# test_stage5.py
from src.prompts.grading_prompt_manager import GradingPromptManager

default_template = """You are grading the accuracy of a data field extracted by an LLM.

Field name: {field_name}
Correct value (from Gemini Pro): {correct_value}
Actual value (to grade): {actual_value}

Rate the accuracy and provide structured output:
1. Score (0-100)
2. Match type: exact | semantic | partial | none
3. Brief explanation
4. Confidence (0-1)

Respond in format:
SCORE: <number>
MATCH_TYPE: <type>
CONFIDENCE: <0-1>
EXPLANATION: <text>"""

session = get_session()
try:
    gpv = GradingPromptManager.create_version(
        version="1.0",
        prompt_template=default_template,
        scoring_rubric="Exact=100%, Semantic=70-99%, Partial=40-69%, None=0-19%",
        description="Initial grading prompt",
        session=session
    )
    print(f"✅ Created grading prompt version: {gpv.version}")
    
    active = GradingPromptManager.get_active_version(session=session)
    assert active.id == gpv.id
    print("✅ Can retrieve active grading prompt")
    
    specific = GradingPromptManager.get_version("1.0", session=session)
    assert specific.id == gpv.id
    print("✅ Can retrieve specific grading prompt version")
    
    session.commit()
    
finally:
    session.close()
```

**Acceptance Criteria**:
- ✅ Can create grading prompt versions
- ✅ Can retrieve active and specific versions
- ✅ Default prompt template has clear scoring rubric

---

## Stage 6: Initialize Prompts Script

**Goal**: Create CLI script to initialize prompts from files

**Duration**: 1 hour

**Tasks**:
1. Create `scripts/initialize_prompts.py`
2. Support loading agent prompts from markdown files
3. Support creating grading prompts programmatically
4. Add command-line arguments for version, description, etc.
5. Test script execution

**Files to Create**:
- `scripts/initialize_prompts.py`

**Verification Script**:
```bash
# test_stage6.sh
# Initialize agent prompt
python scripts/initialize_prompts.py \
    --prompt prompts/research-agent-prompt.md \
    --version 1.0 \
    --description "Initial version" \
    --created-by "System"

# Verify it was created
python -c "
from src.prompts.prompt_manager import PromptManager
pv = PromptManager.get_version('research-agent-prompt', '1.0')
print(f'✅ Prompt version exists: {pv.prompt_name}@{pv.version}')
"
```

**Acceptance Criteria**:
- ✅ Script runs without errors
- ✅ Prompts are created in database
- ✅ Can specify version and description
- ✅ Handles missing files gracefully

---

## Stage 7: ResearchAgent Integration - Database Prompts

**Goal**: Update ResearchAgent to load prompts from database

**Duration**: 2-3 hours

**Tasks**:
1. Update `ResearchAgent.__init__()` in `src/agent/research_agent.py`
2. Add parameters: `prompt_version_id`, `prompt_name`, `prompt_version`
3. Implement database prompt loading logic
4. Maintain backward compatibility with file-based prompts
5. Test both modes

**Files to Modify**:
- `src/agent/research_agent.py`

**Verification Script**:
```python
# test_stage7.py
from src.agent.research_agent import ResearchAgent
from src.prompts.prompt_manager import PromptManager

# Test database prompt loading
session = get_session()
try:
    # Get a prompt version
    pv = PromptManager.get_active_version("research-agent-prompt", session=session)
    
    # Test with prompt_version_id
    agent1 = ResearchAgent(
        model_type="local",
        prompt_version_id=pv.id,
        verbose=False
    )
    assert agent1._instructions is not None
    print("✅ Can load prompt by ID")
    
    # Test with prompt_name
    agent2 = ResearchAgent(
        model_type="local",
        prompt_name="research-agent-prompt",
        verbose=False
    )
    assert agent2._instructions is not None
    print("✅ Can load prompt by name")
    
    # Test with prompt_name + version
    agent3 = ResearchAgent(
        model_type="local",
        prompt_name="research-agent-prompt",
        prompt_version="1.0",
        verbose=False
    )
    assert agent3._instructions is not None
    print("✅ Can load prompt by name and version")
    
    # Test legacy file-based (should still work)
    agent4 = ResearchAgent(
        model_type="local",
        verbose=False
        # No prompt parameters = file-based
    )
    assert agent4._instructions is not None
    print("✅ Legacy file-based loading still works")
    
finally:
    session.close()
```

**Acceptance Criteria**:
- ✅ Can load prompts from database
- ✅ Backward compatibility maintained
- ✅ All three modes work (ID, name, name+version)
- ✅ Existing code continues to work

---

## Stage 8: Test Runner - Core Structure & Ground Truth

**Goal**: Implement test runner with Gemini Pro ground truth logic

**Duration**: 3-4 hours

**Tasks**:
1. Create `src/testing/llm_output_validation_runner.py`
2. Implement `LLMOutputValidationRunner` class
3. Implement `_ensure_gemini_pro_output()` with 24hr cache logic
4. Implement `_run_gemini_pro_and_store()` - Run agent and store output
5. Implement `_store_output()` - Store CompanyInfo in database
6. Implement `_calculate_cost()` - Calculate token costs
7. Test ground truth generation and caching

**Files to Create**:
- `src/testing/llm_output_validation_runner.py`

**Verification Script**:
```python
# test_stage8.py
from src.testing.llm_output_validation_runner import LLMOutputValidationRunner
from src.prompts.prompt_manager import PromptManager

# Get prompt version
pv = PromptManager.get_active_version("research-agent-prompt")

# Create runner
runner = LLMOutputValidationRunner(
    prompt_version_id=pv.id,
    test_run_description="Stage 8 test"
)

# Test ground truth generation (this will call API - be careful!)
# Uncomment when ready to test with real API
# result = runner.run_test(
#     company_name="BitMovin",
#     other_models=[],  # No other models yet
#     max_iterations=5
# )
# print(f"✅ Test run created: {result['test_run_id']}")
# print(f"✅ Ground truth stored: {result['gemini_pro_output_id']}")

# Test caching logic (should reuse existing if <24hrs)
# result2 = runner.run_test(
#     company_name="BitMovin",
#     other_models=[],
#     force_refresh=False
# )
# print(f"✅ Cached ground truth reused: {result2['gemini_pro_output_id']}")

print("✅ Runner structure created (API test skipped for now)")
```

**Acceptance Criteria**:
- ✅ Runner class created
- ✅ Can create test run records
- ✅ Ground truth generation works (with API key)
- ✅ 24-hour caching works
- ✅ Outputs stored correctly in database

---

## Stage 9: Test Runner - Model Execution & Storage

**Goal**: Implement running and storing outputs for other models

**Duration**: 2-3 hours

**Tasks**:
1. Implement `_run_model_and_store()` - Run agent for a model and store output
2. Implement `_get_other_models()` - Get active models (excluding Gemini Pro)
3. Implement `_delete_other_model_outputs()` - Clean up old outputs
4. Update `run_test()` to execute all models
5. Test multi-model execution

**Files to Modify**:
- `src/testing/llm_output_validation_runner.py`

**Verification Script**:
```python
# test_stage9.py
from src.testing.llm_output_validation_runner import LLMOutputValidationRunner
from src.prompts.prompt_manager import PromptManager
from src.database.schema import ModelConfiguration

pv = PromptManager.get_active_version("research-agent-prompt")
runner = LLMOutputValidationRunner(prompt_version_id=pv.id)

# Get active models
session = get_session()
try:
    models = runner._get_other_models(session=session)
    print(f"✅ Found {len(models)} active models to test")
    
    # Test running one model (if you have a local model configured)
    # result = runner.run_test(
    #     company_name="BitMovin",
    #     other_models=models[:1],  # Just one model
    #     max_iterations=5
    # )
    # print(f"✅ Tested {result['other_outputs_count']} models")
    
finally:
    session.close()
```

**Acceptance Criteria**:
- ✅ Can run agent for multiple models
- ✅ Outputs stored correctly
- ✅ Old outputs cleaned up for test run
- ✅ Token usage tracked

---

## Stage 10: Grading System - Field-Level Grading

**Goal**: Implement Gemini Flash grading for individual fields

**Duration**: 3-4 hours

**Tasks**:
1. Implement `_grade_field()` - Grade single field using Gemini Flash
2. Implement `_get_fields_to_grade()` - List all CompanyInfo fields
3. Load grading prompt from database (GradingPromptManager)
4. Parse structured grading response (SCORE, MATCH_TYPE, CONFIDENCE, EXPLANATION)
5. Handle edge cases (missing values, parse errors)
6. Track grading token usage

**Files to Modify**:
- `src/testing/llm_output_validation_runner.py`

**Verification Script**:
```python
# test_stage10.py
from src.testing.llm_output_validation_runner import LLMOutputValidationRunner
from src.prompts.prompt_manager import PromptManager
from src.models.model_factory import get_chat_model

pv = PromptManager.get_active_version("research-agent-prompt")
runner = LLMOutputValidationRunner(prompt_version_id=pv.id)

# Test field grading (with API - be careful!)
flash_model = get_chat_model(
    model_type="gemini",
    model_kwargs={"model_name": "gemini-flash-latest"}
)

# Test grading a field
result = runner._grade_field(
    flash_model=flash_model,
    field_name="industry",
    correct_value="SaaS",
    actual_value="Software as a Service"
)

print(f"✅ Field grading result:")
print(f"   Score: {result['score']}%")
print(f"   Match type: {result['match_type']}")
print(f"   Confidence: {result['confidence']}")
print(f"   Explanation: {result['explanation']}")

assert 0 <= result['score'] <= 100
assert result['match_type'] in ['exact', 'semantic', 'partial', 'none']
assert 0 <= result['confidence'] <= 1
```

**Acceptance Criteria**:
- ✅ Can grade individual fields
- ✅ Returns structured output (score, match_type, explanation, confidence)
- ✅ Handles edge cases (None values, parse errors)
- ✅ Token usage tracked

---

## Stage 11: Grading System - Aggregate Scoring

**Goal**: Implement aggregate accuracy calculations

**Duration**: 2 hours

**Tasks**:
1. Implement aggregate score calculation in `_grade_output_with_flash()`
   - Overall accuracy (average of all fields)
   - Required fields accuracy (company_name, industry, company_size, headquarters, founded)
   - Optional fields accuracy (all others)
   - Weighted accuracy (critical fields count 2x)
2. Store results in `LLMOutputValidationResult` table
3. Test aggregate calculations

**Files to Modify**:
- `src/testing/llm_output_validation_runner.py`

**Verification Script**:
```python
# test_stage11.py
from src.testing.llm_output_validation_runner import LLMOutputValidationRunner

# Mock field scores for testing
field_scores = {
    "industry": {"score": 85, "match_type": "semantic", "explanation": "test", "confidence": 0.9},
    "company_size": {"score": 100, "match_type": "exact", "explanation": "test", "confidence": 1.0},
    "headquarters": {"score": 90, "match_type": "semantic", "explanation": "test", "confidence": 0.95},
    "description": {"score": 75, "match_type": "partial", "explanation": "test", "confidence": 0.8},
}

# Calculate aggregates (simulate logic)
all_scores = [r['score'] for r in field_scores.values()]
overall = sum(all_scores) / len(all_scores)
print(f"✅ Overall accuracy: {overall:.1f}%")

required_fields = ["industry", "company_size", "headquarters"]
required_scores = [field_scores[f]['score'] for f in required_fields if f in field_scores]
required_avg = sum(required_scores) / len(required_scores) if required_scores else 0
print(f"✅ Required fields accuracy: {required_avg:.1f}%")

critical_fields = ["industry", "company_size"]
weighted_scores = []
for field, result in field_scores.items():
    weight = 2.0 if field in critical_fields else 1.0
    weighted_scores.extend([result['score']] * int(weight))
weighted_avg = sum(weighted_scores) / len(weighted_scores) if weighted_scores else 0
print(f"✅ Weighted accuracy: {weighted_avg:.1f}%")
```

**Acceptance Criteria**:
- ✅ All aggregate scores calculated correctly
- ✅ Required vs optional fields separated
- ✅ Weighted scoring works (critical fields count 2x)
- ✅ Results stored in database

---

## Stage 12: Complete Test Run Workflow

**Goal**: Complete end-to-end test run workflow

**Duration**: 2-3 hours

**Tasks**:
1. Complete `run_test()` method - Full workflow
2. Implement `_copy_output_to_test_run()` - Reuse cached ground truth
3. Test complete workflow with real models (if available)
4. Verify all data stored correctly

**Files to Modify**:
- `src/testing/llm_output_validation_runner.py`

**Verification Script**:
```python
# test_stage12.py
from src.testing.llm_output_validation_runner import LLMOutputValidationRunner
from src.prompts.prompt_manager import PromptManager

pv = PromptManager.get_active_version("research-agent-prompt")
runner = LLMOutputValidationRunner(
    prompt_version_id=pv.id,
    test_run_description="Stage 12 end-to-end test"
)

# Run complete test (requires API keys and models)
# result = runner.run_test(
#     company_name="BitMovin",
#     force_refresh=False,  # Use cached ground truth if available
#     max_iterations=5
# )

# print(f"✅ Test run ID: {result['test_run_id']}")
# print(f"✅ Ground truth: {result['gemini_pro_output_id']}")
# print(f"✅ Other models tested: {result['other_outputs_count']}")
# print(f"✅ Grading results: {result['grading_results_count']}")

# Verify results in database
# from src.database.schema import TestRun, LLMOutputValidation, LLMOutputValidationResult
# session = get_session()
# try:
#     test_run = session.query(TestRun).filter(TestRun.id == result['test_run_id']).first()
#     outputs = session.query(LLMOutputValidation).filter(LLMOutputValidation.test_run_id == test_run.id).all()
#     results = session.query(LLMOutputValidationResult).filter(LLMOutputValidationResult.test_run_id == test_run.id).all()
#     
#     print(f"✅ Test run has {len(outputs)} outputs")
#     print(f"✅ Test run has {len(results)} grading results")
#     
#     if results:
#         print(f"✅ Average accuracy: {results[0].overall_accuracy:.1f}%")
# finally:
#     session.close()
```

**Acceptance Criteria**:
- ✅ Complete workflow runs end-to-end
- ✅ Ground truth cached and reused
- ✅ All models tested
- ✅ All outputs graded
- ✅ All data stored correctly

---

## Stage 13: Test Suite Support

**Goal**: Implement multi-company test suite execution

**Duration**: 2 hours

**Tasks**:
1. Implement `run_test_suite()` method
2. Aggregate accuracy scores across companies
3. Test suite name grouping
4. Handle failures gracefully

**Files to Modify**:
- `src/testing/llm_output_validation_runner.py`

**Verification Script**:
```python
# test_stage13.py
from src.testing.llm_output_validation_runner import LLMOutputValidationRunner
from src.prompts.prompt_manager import PromptManager

pv = PromptManager.get_active_version("research-agent-prompt")
runner = LLMOutputValidationRunner(prompt_version_id=pv.id)

# Test suite (with cached ground truth)
# suite_result = runner.run_test_suite(
#     company_names=["BitMovin", "Stripe"],  # Start with 2 companies
#     test_suite_name="stage-13-test",
#     max_iterations=5
# )

# print(f"✅ Test suite: {suite_result['test_suite_name']}")
# print(f"✅ Successfully tested: {suite_result['successful_companies']}/{suite_result['total_companies']}")
# print(f"✅ Aggregated overall accuracy: {suite_result['aggregated_accuracy']['overall']:.1f}%")
# print(f"✅ Aggregated required fields: {suite_result['aggregated_accuracy']['required_fields']:.1f}%")
```

**Acceptance Criteria**:
- ✅ Can run tests across multiple companies
- ✅ Results aggregated correctly
- ✅ Test suite name groups results
- ✅ Failures handled gracefully

---

## Stage 14: CLI Script - Run Tests

**Goal**: Create CLI script for running tests

**Duration**: 2 hours

**Tasks**:
1. Create `scripts/run_llm_output_validation.py`
2. Add command-line arguments:
   - `--company` (single company)
   - `--companies` (multiple companies)
   - `--prompt-name` / `--prompt-version`
   - `--test-suite-name`
   - `--force-refresh`
   - `--max-iterations`
3. Add help text and error handling
4. Format output nicely

**Files to Create**:
- `scripts/run_llm_output_validation.py`

**Verification Script**:
```bash
# test_stage14.sh
# Run single company test
python scripts/run_llm_output_validation.py \
    --company "BitMovin" \
    --test-run-description "CLI test"

# Run test suite
python scripts/run_llm_output_validation.py \
    --companies "BitMovin" "Stripe" \
    --test-suite-name "cli-test-suite" \
    --max-iterations 5

# Run with specific prompt version
python scripts/run_llm_output_validation.py \
    --company "BitMovin" \
    --prompt-name research-agent-prompt \
    --prompt-version 1.0
```

**Acceptance Criteria**:
- ✅ Script runs without errors
- ✅ All arguments work correctly
- ✅ Help text is clear
- ✅ Errors handled gracefully
- ✅ Output is readable

---

## Stage 15: Analytics - Prompt Comparison

**Goal**: Implement prompt version comparison analytics

**Duration**: 2-3 hours

**Tasks**:
1. Create `src/testing/prompt_analytics.py`
2. Implement `compare_prompt_versions()` - Compare accuracy across versions
3. Implement `get_test_run_history()` - Get historical test runs
4. Test analytics queries

**Files to Create**:
- `src/testing/prompt_analytics.py`

**Verification Script**:
```python
# test_stage15.py
from src.testing.prompt_analytics import PromptAnalytics

# Compare prompt versions (need test data first)
# comparison = PromptAnalytics.compare_prompt_versions(
#     prompt_name="research-agent-prompt",
#     company_name="BitMovin"
# )

# for version_data in comparison:
#     print(f"Version {version_data['prompt_version']}: "
#           f"{version_data['average_overall_accuracy']:.1f}% accuracy")

# Get test run history
# history = PromptAnalytics.get_test_run_history(
#     prompt_name="research-agent-prompt",
#     limit=10
# )

# print(f"✅ Found {len(history)} test runs")
```

**Acceptance Criteria**:
- ✅ Can compare prompt versions
- ✅ Can retrieve test run history
- ✅ Queries are efficient
- ✅ Results are accurate

---

## Stage 16: Analytics - Cost Analysis

**Goal**: Implement cost analysis functions

**Duration**: 2 hours

**Tasks**:
1. Implement `get_cost_analysis()` in `PromptAnalytics`
2. Aggregate costs by prompt version, company, and model
3. Calculate token usage statistics
4. Test cost calculations

**Files to Modify**:
- `src/testing/prompt_analytics.py`

**Verification Script**:
```python
# test_stage16.py
from src.testing.prompt_analytics import PromptAnalytics

# Get cost analysis (need test data first)
# cost_analysis = PromptAnalytics.get_cost_analysis(
#     prompt_name="research-agent-prompt"
# )

# print(f"Total cost: ${cost_analysis['total']['total_cost']:.2f}")
# print(f"Agent cost: ${cost_analysis['total']['agent_cost']:.2f}")
# print(f"Grading cost: ${cost_analysis['total']['grading_cost']:.2f}")
# print(f"Total tokens: {cost_analysis['total']['total_tokens']:,}")
```

**Acceptance Criteria**:
- ✅ Cost analysis works correctly
- ✅ Aggregates by prompt version, company, model
- ✅ Token usage tracked
- ✅ Calculations are accurate

---

## Stage 17: CLI Script - Compare Versions

**Goal**: Create CLI script for comparing prompt versions

**Duration**: 1 hour

**Tasks**:
1. Create `scripts/compare_prompt_versions.py`
2. Display comparison results nicely
3. Support filtering by company or test suite
4. Show cost analysis

**Files to Create**:
- `scripts/compare_prompt_versions.py`

**Verification Script**:
```bash
# test_stage17.sh
# Compare versions for single company
python scripts/compare_prompt_versions.py \
    --prompt research-agent-prompt \
    --company BitMovin

# Compare versions across test suite
python scripts/compare_prompt_versions.py \
    --prompt research-agent-prompt \
    --test-suite-name "test-suite-v1.0"

# Show cost analysis
python scripts/compare_prompt_versions.py \
    --prompt research-agent-prompt \
    --show-costs
```

**Acceptance Criteria**:
- ✅ Script runs and displays results
- ✅ Comparison is clear and readable
- ✅ Cost analysis displayed correctly

---

## Stage 18: UI Integration - Basic Page

**Goal**: Create basic Streamlit UI page

**Duration**: 3-4 hours

**Tasks**:
1. Create `src/ui/pages/5_🧪_LLM_Output_Validation.py`
2. Add prompt version selector
3. Add company input
4. Add test run button
5. Display basic results

**Files to Create**:
- `src/ui/pages/5_🧪_LLM_Output_Validation.py`

**Verification**:
- Open Streamlit UI
- Navigate to LLM Output Validation page
- Select prompt version
- Enter company name
- Run test
- Verify results display

**Acceptance Criteria**:
- ✅ UI page loads correctly
- ✅ Can select prompt version
- ✅ Can run tests from UI
- ✅ Results display correctly

---

## Stage 19: UI Integration - Results Display

**Goal**: Enhance UI with detailed results display

**Duration**: 2-3 hours

**Tasks**:
1. Display accuracy scores (overall, required, optional, weighted)
2. Show field-level accuracy breakdown
3. Display token usage and costs
4. Add comparison view (if multiple test runs)

**Files to Modify**:
- `src/ui/pages/5_🧪_LLM_Output_Validation.py`

**Verification**:
- Run test from UI
- Verify all scores display
- Verify field-level breakdown shows
- Verify costs display

**Acceptance Criteria**:
- ✅ All accuracy metrics displayed
- ✅ Field-level breakdown visible
- ✅ Costs and tokens displayed
- ✅ UI is clear and readable

---

## Stage 20: UI Integration - Comparison & Analytics

**Goal**: Add comparison and analytics views to UI

**Duration**: 2-3 hours

**Tasks**:
1. Add prompt version comparison chart
2. Add accuracy trends over time
3. Add cost analysis visualization
4. Add test suite aggregation view

**Files to Modify**:
- `src/ui/pages/5_🧪_LLM_Output_Validation.py`

**Verification**:
- Navigate to comparison view
- Verify charts display correctly
- Verify trends are visible
- Verify cost analysis shows

**Acceptance Criteria**:
- ✅ Comparison charts work
- ✅ Trends visible over time
- ✅ Cost analysis displayed
- ✅ UI is interactive and useful

---

## Stage 21: Testing & Edge Cases

**Goal**: Comprehensive testing and edge case handling

**Duration**: 3-4 hours

**Tasks**:
1. Test with malformed JSON outputs
2. Test with missing fields
3. Test with timeout errors
4. Test with model refusals
5. Test with empty ground truth
6. Test grading consistency (same input multiple times)
7. Write integration tests

**Verification Script**:
```python
# test_stage21.py
# Test various edge cases
# - Malformed JSON
# - Missing fields
# - Timeouts
# - Refusals
# - Empty values
# - Grading consistency

# Run each test case and verify handling
```

**Acceptance Criteria**:
- ✅ All edge cases handled gracefully
- ✅ Errors don't crash system
- ✅ Grading is consistent (within 5% variance)
- ✅ Integration tests pass

---

## Stage 22: Documentation & Finalization

**Goal**: Complete documentation and finalize implementation

**Duration**: 2-3 hours

**Tasks**:
1. Update README with usage examples
2. Document API/changes
3. Create user guide
4. Add troubleshooting section
5. Verify all examples work

**Files to Create/Modify**:
- `docs/reference/TESTING_FRAMEWORK_USAGE.md`
- `README.md` (update)
- Code comments

**Acceptance Criteria**:
- ✅ Documentation is complete
- ✅ Examples work correctly
- ✅ Troubleshooting guide helpful
- ✅ Code is well-commented

---

## Testing Checklist (After Each Stage)

After completing each stage, verify:

- [ ] Code runs without errors
- [ ] Database changes applied correctly (if applicable)
- [ ] Can test functionality manually
- [ ] No breaking changes to existing code
- [ ] Error handling works
- [ ] Documentation updated (if needed)

---

## Quick Reference: Stage Dependencies

```
Stage 0: Prerequisites
  ↓
Stage 1: Database Schema Part 1 (PromptVersion, GradingPromptVersion)
  ↓
Stage 2: Database Schema Part 2 (TestRun, LLMOutputValidation)
  ↓
Stage 3: Database Schema Part 3 (LLMOutputValidationResult)
  ↓
Stage 4: Prompt Manager (CRUD operations)
  ↓
Stage 5: Grading Prompt Manager
  ↓
Stage 6: Initialize Prompts Script
  ↓
Stage 7: ResearchAgent Integration
  ↓
Stage 8: Test Runner - Ground Truth
  ↓
Stage 9: Test Runner - Model Execution
  ↓
Stage 10: Grading System - Field Level
  ↓
Stage 11: Grading System - Aggregate Scoring
  ↓
Stage 12: Complete Test Run Workflow
  ↓
Stage 13: Test Suite Support
  ↓
Stage 14: CLI Script - Run Tests
  ↓
Stage 15: Analytics - Prompt Comparison
  ↓
Stage 16: Analytics - Cost Analysis
  ↓
Stage 17: CLI Script - Compare Versions
  ↓
Stage 18: UI Integration - Basic Page
  ↓
Stage 19: UI Integration - Results Display
  ↓
Stage 20: UI Integration - Comparison & Analytics
  ↓
Stage 21: Testing & Edge Cases
  ↓
Stage 22: Documentation & Finalization
```

---

## Estimated Timeline

**Total Estimated Time**: 4-5 weeks (working incrementally)

- **Weeks 1-2**: Stages 1-7 (Database, Prompt Management, ResearchAgent Integration)
- **Week 2-3**: Stages 8-13 (Test Runner, Grading, Complete Workflow)
- **Week 3-4**: Stages 14-17 (CLI, Analytics)
- **Week 4-5**: Stages 18-22 (UI, Testing, Documentation)

**Note**: Adjust timeline based on available time and complexity encountered.

---

## Next Steps

1. **Start with Stage 0** - Verify prerequisites
2. **Work through stages sequentially** - Each stage builds on previous
3. **Test after each stage** - Don't move on until current stage works
4. **Update this document** - Mark stages as complete as you go
5. **Ask for help** - If stuck on any stage, ask for clarification

---

**Status**: 📋 **STAGED PLAN CREATED - READY FOR IMPLEMENTATION**  
**Last Updated**: 2025-01-15

**Key Features**:
- ✅ 22 incremental stages
- ✅ Each stage independently testable
- ✅ Clear verification steps
- ✅ Acceptance criteria for each stage
- ✅ Dependency tracking
- ✅ Estimated timeline

