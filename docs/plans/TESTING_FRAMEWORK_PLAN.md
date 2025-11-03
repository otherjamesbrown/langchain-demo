# Comprehensive Testing Framework Plan - LLM Output Validation

> **📖 See Also**: [TESTING_FRAMEWORK_THESIS.md](./TESTING_FRAMEWORK_THESIS.md) for the conceptual foundation and reasoning behind this implementation plan.

## Overview

This document outlines a comprehensive plan for building a robust testing framework that:
- Uses **Gemini 2.5 Pro as ground truth** with validation workflow
- Stores all model outputs in database for comparison
- Uses **Gemini Flash to grade** other models' outputs with structured scoring
- Tracks **both agent and grading prompt versions** to enable systematic prompt engineering
- Implements **weighted accuracy** scoring for critical fields
- Links results to **test runs** for historical comparison
- Supports both automated CLI execution and interactive UI execution
- Provides clear, actionable accuracy scores with confidence metrics
- Includes ground truth validation workflow for quality assurance

---

## Goals

1. **Ground Truth**: Gemini Pro output is the source of truth for validation
2. **LLM-Based Grading**: Use Gemini Flash to intelligently grade field-level accuracy
3. **Prompt Versioning**: Track which prompt version was used in each test run
4. **Historical Tracking**: Compare accuracy across prompt versions over time
5. **Automation**: Can run via CLI/scripts without UI
6. **Visibility**: Rich UI display of results with accuracy comparisons
7. **Prompt Engineering**: Enable tweaking prompts and seeing accuracy improvements

---

## Current State Analysis

### Existing Components

✅ **Test Infrastructure**:
- `scripts/test_bitmovin_research.py` - Standalone test script
- `tests/test_bitmovin_research.py` - Pytest-based tests
- `src/ui/pages/4_🧪_Test_BitMovin.py` - Streamlit UI page
- `src/testing/test_runner.py` - Baseline-based test runner (legacy approach)

✅ **Prompt System**:
- `prompts/research-agent-prompt.md` - Main prompt file
- `src/agent/research_agent.py` - Loads prompts from files

❌ **Missing Components**:
- Database storage for model outputs
- Prompt versioning system
- Test run tracking
- LLM-based grading (Gemini Flash)
- Accuracy comparison across prompt versions

---

## Architecture Design

### 1. Database Schema

#### 1.1 Prompt Versioning Tables

```python
# src/database/schema.py

class PromptVersion(Base):
    """Stores versioned prompts for research agent."""
    
    __tablename__ = "prompt_versions"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Prompt identification
    prompt_name = Column(String(255), nullable=False, index=True)  # e.g., "research-agent-prompt"
    version = Column(String(50), nullable=False, index=True)  # e.g., "1.0", "1.1", "v2-base"
    
    # Prompt content
    instructions_content = Column(Text, nullable=False)  # RESEARCH INSTRUCTIONS section
    classification_reference_content = Column(Text, nullable=True)  # CLASSIFICATION REFERENCE section
    full_content = Column(Text, nullable=True)  # Full markdown content for reference
    
    # Prompt metadata
    description = Column(Text, nullable=True)  # Description of changes in this version
    created_by = Column(String(255), nullable=True)  # User/author who created this version
    is_active = Column(Boolean, default=True, nullable=False)  # Whether this version is currently active
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Composite unique constraint
    __table_args__ = (
        UniqueConstraint('prompt_name', 'version', name='uq_prompt_version'),
    )
    
    def __repr__(self) -> str:
        return f"<PromptVersion(id={self.id}, name='{self.prompt_name}', version='{self.version}')>"


class GradingPromptVersion(Base):
    """Stores versioned grading prompts for LLM output validation."""
    
    __tablename__ = "grading_prompt_versions"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Prompt identification
    version = Column(String(50), nullable=False, unique=True, index=True)  # e.g., "1.0", "1.1"
    
    # Prompt content
    prompt_template = Column(Text, nullable=False)  # Template with placeholders
    scoring_rubric = Column(Text, nullable=True)  # Detailed scoring rules
    
    # Prompt metadata
    description = Column(Text, nullable=True)  # Description of changes in this version
    is_active = Column(Boolean, default=True, nullable=False)
    consistency_score = Column(Float, nullable=True)  # Track grading consistency (0-1)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self) -> str:
        return f"<GradingPromptVersion(id={self.id}, version='{self.version}')>"


class TestRun(Base):
    """Represents a single test run with a specific prompt version."""
    
    __tablename__ = "test_runs"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Test identification
    test_name = Column(String(255), nullable=False, index=True)  # e.g., "llm-output-validation"
    company_name = Column(String(255), nullable=False, index=True)
    
    # Test suite grouping (for multi-company test runs)
    test_suite_name = Column(String(255), nullable=True, index=True)  # Groups multiple companies together
    
    # Prompt version used
    prompt_version_id = Column(Integer, ForeignKey("prompt_versions.id"), nullable=False, index=True)
    prompt_name = Column(String(255), nullable=False)  # Denormalized for easy querying
    prompt_version = Column(String(50), nullable=False)  # Denormalized for easy querying
    
    # Test run metadata
    description = Column(Text, nullable=True)  # Optional description of this test run
    executed_by = Column(String(255), nullable=True)  # User who ran the test
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationship
    prompt_version_obj = relationship("PromptVersion", backref="test_runs")
    
    def __repr__(self) -> str:
        suite_info = f", suite='{self.test_suite_name}'" if self.test_suite_name else ""
        return f"<TestRun(id={self.id}, test='{self.test_name}', company='{self.company_name}'{suite_info}, prompt='{self.prompt_name}@{self.prompt_version}')>"
```

#### 1.2 Model Output Storage Table

```python
# src/database/schema.py

class LLMOutputValidation(Base):
    """Stores LLM outputs for validation testing."""
    
    __tablename__ = "llm_output_validation"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Link to test run
    test_run_id = Column(Integer, ForeignKey("test_runs.id"), nullable=False, index=True)
    
    # Test identification
    test_name = Column(String(255), nullable=False, index=True)  # e.g., "llm-output-validation"
    company_name = Column(String(255), nullable=False, index=True)
    model_configuration_id = Column(Integer, ForeignKey("model_configurations.id"), nullable=True, index=True)
    model_name = Column(String(255), nullable=False)
    model_provider = Column(String(50), nullable=False)
    
    # All CompanyInfo fields as columns
    company_name_field = Column(String(255), nullable=True)
    industry = Column(String(255), nullable=True)
    company_size = Column(String(100), nullable=True)
    headquarters = Column(String(255), nullable=True)
    founded = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    website = Column(String(512), nullable=True)
    products = Column(JSON, nullable=True)  # List[str]
    competitors = Column(JSON, nullable=True)  # List[str]
    revenue = Column(String(100), nullable=True)
    funding_stage = Column(String(100), nullable=True)
    growth_stage = Column(String(100), nullable=True)
    industry_vertical = Column(String(255), nullable=True)
    sub_industry_vertical = Column(String(255), nullable=True)
    financial_health = Column(String(100), nullable=True)
    business_and_technology_adoption = Column(String(255), nullable=True)
    primary_workload_philosophy = Column(String(255), nullable=True)
    buyer_journey = Column(String(100), nullable=True)
    budget_maturity = Column(String(100), nullable=True)
    cloud_spend_capacity = Column(String(100), nullable=True)
    procurement_process = Column(String(100), nullable=True)
    key_personas = Column(JSON, nullable=True)  # List[str]
    
    # Execution metadata
    execution_time_seconds = Column(Float, nullable=True)
    iterations = Column(Integer, nullable=True)
    success = Column(Boolean, nullable=False)
    raw_output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Token usage tracking (for cost analysis)
    input_tokens = Column(Integer, nullable=True)  # Tokens sent to model
    output_tokens = Column(Integer, nullable=True)  # Tokens generated by model
    total_tokens = Column(Integer, nullable=True)  # input + output
    estimated_cost_usd = Column(Float, nullable=True)  # Calculated cost based on model pricing
    
    # Ground truth validation (for Gemini Pro outputs)
    ground_truth_status = Column(String(50), nullable=True)  # 'unvalidated', 'validated', 'disputed', 'corrected'
    human_validated_at = Column(DateTime, nullable=True)
    validation_notes = Column(Text, nullable=True)
    
    # Timestamp for refresh logic
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    test_run = relationship("TestRun", backref="llm_outputs")
    
    def __repr__(self) -> str:
        return f"<LLMOutputValidation(id={self.id}, test='{self.test_name}', company='{self.company_name}', model='{self.model_name}')>"
```

#### 1.3 Accuracy Results Table

```python
# src/database/schema.py

class LLMOutputValidationResult(Base):
    """Stores accuracy scores from Gemini Flash grading."""
    
    __tablename__ = "llm_output_validation_results"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Link to output record and test run
    output_id = Column(Integer, ForeignKey("llm_output_validation.id"), nullable=False, index=True)
    test_run_id = Column(Integer, ForeignKey("test_runs.id"), nullable=False, index=True)
    
    # Test identification
    test_name = Column(String(255), nullable=False, index=True)
    company_name = Column(String(255), nullable=False, index=True)
    model_name = Column(String(255), nullable=False, index=True)
    model_provider = Column(String(50), nullable=False)
    
    # Field-level accuracy scores with enhanced metadata
    field_accuracy_scores = Column(JSON, nullable=False)  # {field_name: {score, match_type, explanation, confidence}}
    
    # Aggregate scores
    overall_accuracy = Column(Float, nullable=False)  # Average of all field scores (0-100)
    required_fields_accuracy = Column(Float, nullable=True)  # Average of required fields
    optional_fields_accuracy = Column(Float, nullable=True)  # Average of optional fields
    weighted_accuracy = Column(Float, nullable=True)  # Weighted average (critical fields count more)
    
    # Grading metadata
    graded_by_model = Column(String(100), nullable=False, default="gemini-flash-latest")
    grading_prompt_version_id = Column(Integer, ForeignKey("grading_prompt_versions.id"), nullable=True, index=True)
    grading_prompt = Column(Text, nullable=True)  # Store the prompt used for grading
    grading_response = Column(Text, nullable=True)  # Store raw grading response
    grading_errors = Column(JSON, nullable=True)  # Any errors during grading
    grading_confidence = Column(Float, nullable=True)  # Average confidence from grader (0-1)
    
    # Token usage for grading (for cost analysis)
    grading_input_tokens = Column(Integer, nullable=True)  # Tokens sent to grader
    grading_output_tokens = Column(Integer, nullable=True)  # Tokens generated by grader
    grading_total_tokens = Column(Integer, nullable=True)  # input + output
    grading_cost_usd = Column(Float, nullable=True)  # Cost of grading operation
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    output = relationship("LLMOutputValidation", backref="validation_results")
    test_run = relationship("TestRun", backref="validation_results")
    
    def __repr__(self) -> str:
        return f"<LLMOutputValidationResult(id={self.id}, output_id={self.output_id}, overall={self.overall_accuracy:.1f}%)>"
```

### 2. Prompt Management System

#### 2.1 Prompt Manager

```python
# src/prompts/prompt_manager.py

from typing import Optional, List, Dict, Any
from pathlib import Path
from sqlalchemy.orm import Session
from src.database.schema import PromptVersion, get_session

class PromptManager:
    """
    Manages prompt versions in the database.
    
    Educational: This shows how to version prompts for A/B testing and
    tracking prompt engineering experiments.
    """
    
    @staticmethod
    def load_prompt_from_file(prompt_path: Path) -> Dict[str, str]:
        """Load prompt sections from markdown file."""
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
        content = prompt_path.read_text(encoding="utf-8").strip()
        
        # Extract RESEARCH INSTRUCTIONS section
        instructions = ""
        if "# RESEARCH INSTRUCTIONS" in content:
            parts = content.split("# RESEARCH INSTRUCTIONS", 1)
            if len(parts) > 1:
                instructions = parts[1].split("# CLASSIFICATION REFERENCE", 1)[0].strip()
        
        # Extract CLASSIFICATION REFERENCE section
        classification_ref = ""
        if "# CLASSIFICATION REFERENCE" in content:
            parts = content.split("# CLASSIFICATION REFERENCE", 1)
            if len(parts) > 1:
                # Stop at next major section
                classification_ref = parts[1].split("# DETAILED CLASSIFICATION DEFINITIONS", 1)[0].strip()
        
        return {
            "instructions": instructions or content,  # Fallback to full content
            "classification_reference": classification_ref,
            "full_content": content,
        }
    
    @staticmethod
    def create_version_from_file(
        prompt_name: str,
        prompt_path: Path,
        version: str,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> PromptVersion:
        """Create a new prompt version from a file."""
        sections = PromptManager.load_prompt_from_file(prompt_path)
        
        db_session = session or get_session()
        try:
            # Check if version already exists
            existing = (
                db_session.query(PromptVersion)
                .filter(
                    PromptVersion.prompt_name == prompt_name,
                    PromptVersion.version == version,
                )
                .first()
            )
            if existing:
                raise ValueError(f"Prompt version {prompt_name}@{version} already exists")
            
            prompt_version = PromptVersion(
                prompt_name=prompt_name,
                version=version,
                instructions_content=sections["instructions"],
                classification_reference_content=sections["classification_reference"],
                full_content=sections["full_content"],
                description=description,
                created_by=created_by,
                is_active=True,
            )
            
            db_session.add(prompt_version)
            db_session.commit()
            return prompt_version
            
        finally:
            if not session:
                db_session.close()
    
    @staticmethod
    def get_active_version(
        prompt_name: str,
        session: Optional[Session] = None,
    ) -> Optional[PromptVersion]:
        """Get the active version of a prompt."""
        db_session = session or get_session()
        try:
            return (
                db_session.query(PromptVersion)
                .filter(
                    PromptVersion.prompt_name == prompt_name,
                    PromptVersion.is_active == True,
                )
                .order_by(PromptVersion.created_at.desc())
                .first()
            )
        finally:
            if not session:
                db_session.close()
    
    @staticmethod
    def get_version(
        prompt_name: str,
        version: str,
        session: Optional[Session] = None,
    ) -> Optional[PromptVersion]:
        """Get a specific version of a prompt."""
        db_session = session or get_session()
        try:
            return (
                db_session.query(PromptVersion)
                .filter(
                    PromptVersion.prompt_name == prompt_name,
                    PromptVersion.version == version,
                )
                .first()
            )
        finally:
            if not session:
                db_session.close()
    
    @staticmethod
    def get_version_by_id(
        version_id: int,
        session: Optional[Session] = None,
    ) -> Optional[PromptVersion]:
        """Get a prompt version by ID."""
        db_session = session or get_session()
        try:
            return db_session.query(PromptVersion).filter(PromptVersion.id == version_id).first()
        finally:
            if not session:
                db_session.close()
    
    @staticmethod
    def list_versions(
        prompt_name: str,
        session: Optional[Session] = None,
    ) -> List[PromptVersion]:
        """List all versions of a prompt."""
        db_session = session or get_session()
        try:
            return (
                db_session.query(PromptVersion)
                .filter(PromptVersion.prompt_name == prompt_name)
                .order_by(PromptVersion.created_at.desc())
                .all()
            )
        finally:
            if not session:
                db_session.close()
```

### 3. Test Execution Engine

#### 3.1 LLM Output Validation Runner

```python
# src/testing/llm_output_validation_runner.py

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from src.agent.research_agent import ResearchAgent, ResearchAgentResult
from src.database.schema import (
    LLMOutputValidation, LLMOutputValidationResult, 
    TestRun, ModelConfiguration, PromptVersion
)
from src.database.operations import get_session
from src.tools.models import CompanyInfo
from src.prompts.prompt_manager import PromptManager


class LLMOutputValidationRunner:
    """
    Test runner that uses Gemini Pro as ground truth and Gemini Flash for grading.
    
    Educational: This demonstrates a different testing approach where:
    - One model's output is treated as ground truth
    - Another model is used to grade other models' outputs
    - Results are stored in database for comparison over time
    - Prompt versions are tracked to enable prompt engineering experiments
    """
    
    def __init__(
        self, 
        test_name: str = "llm-output-validation",
        prompt_version_id: Optional[int] = None,
        prompt_name: Optional[str] = None,
        prompt_version: Optional[str] = None,
        test_run_description: Optional[str] = None,
    ):
        self.test_name = test_name
        self.gemini_pro_model_name = "gemini-2.0-flash-exp"  # Update to actual Gemini 2.5 Pro identifier
        self.gemini_flash_model_name = "gemini-flash-latest"
        
        # Prompt version management
        self.prompt_version_id = prompt_version_id
        self.prompt_name = prompt_name
        self.prompt_version = prompt_version
        self.test_run_description = test_run_description
        
        # Validate and resolve prompt version
        self._resolved_prompt_version = self._resolve_prompt_version()
    
    def _resolve_prompt_version(self) -> Optional[PromptVersion]:
        """Resolve the prompt version to use."""
        if self.prompt_version_id:
            pv = PromptManager.get_version_by_id(self.prompt_version_id)
            if not pv:
                raise ValueError(f"Prompt version ID {self.prompt_version_id} not found")
            return pv
        elif self.prompt_name:
            if self.prompt_version:
                pv = PromptManager.get_version(self.prompt_name, self.prompt_version)
            else:
                pv = PromptManager.get_active_version(self.prompt_name)
            
            if not pv:
                raise ValueError(f"Prompt '{self.prompt_name}' (version: {self.prompt_version or 'active'}) not found")
            
            self.prompt_version_id = pv.id
            return pv
        else:
            # Use active version of default prompt
            pv = PromptManager.get_active_version("research-agent-prompt")
            if pv:
                self.prompt_version_id = pv.id
                return pv
            else:
                # Fallback: allow running without prompt version (will use file-based)
                return None
    
    def run_test(
        self,
        company_name: str,
        other_models: Optional[List[ModelConfiguration]] = None,
        force_refresh: bool = False,
        max_iterations: int = 10,
        test_suite_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run the LLM output validation test.
        
        Workflow:
        1. Create test run record with prompt version
        2. Check if Gemini Pro output exists and is fresh (<24hrs) for this test run
        3. If not, run agent with Gemini Pro to get ground truth
        4. Delete old outputs from other models for this test run
        5. Run agent for all other models
        6. Store all outputs in database
        7. Grade each other model's output using Gemini Flash
        8. Store accuracy scores in results table
        
        Args:
            company_name: Company to research
            other_models: List of model configs to test (excludes Gemini Pro)
            force_refresh: Force refresh even if Gemini Pro data is fresh
            max_iterations: Max agent iterations
            test_suite_name: Optional name to group multiple company tests together
            
        Returns:
            Dict with test results summary
        """
        session = get_session()
        try:
            # Step 1: Create test run record
            if not self._resolved_prompt_version:
                raise ValueError("No prompt version available. Initialize prompts first using initialize_prompts.py")
            
            test_run = TestRun(
                test_name=self.test_name,
                company_name=company_name,
                test_suite_name=test_suite_name,
                prompt_version_id=self.prompt_version_id,
                prompt_name=self._resolved_prompt_version.prompt_name,
                prompt_version=self._resolved_prompt_version.version,
                description=self.test_run_description,
            )
            session.add(test_run)
            session.commit()
            
            # Step 2: Check/refresh Gemini Pro output (ground truth)
            gemini_pro_output = self._ensure_gemini_pro_output(
                session=session,
                company_name=company_name,
                test_run_id=test_run.id,
                force_refresh=force_refresh,
                max_iterations=max_iterations,
            )
            
            if not gemini_pro_output:
                return {
                    "success": False,
                    "error": "Failed to get Gemini Pro ground truth output",
                    "test_run_id": test_run.id,
                }
            
            # Step 3: Delete old outputs from other models (for this test run only)
            self._delete_other_model_outputs(
                session=session,
                company_name=company_name,
                test_run_id=test_run.id,
            )
            
            # Step 4: Get list of other models to test
            if other_models is None:
                other_models = self._get_other_models(session=session)
            
            # Step 5: Run agent for all other models
            other_outputs = []
            for model_config in other_models:
                output = self._run_model_and_store(
                    session=session,
                    company_name=company_name,
                    test_run_id=test_run.id,
                    model_config=model_config,
                    max_iterations=max_iterations,
                )
                if output:
                    other_outputs.append(output)
            
            # Step 6: Grade all other models using Gemini Flash
            grading_results = []
            for output in other_outputs:
                result = self._grade_output_with_flash(
                    session=session,
                    gemini_pro_output=gemini_pro_output,
                    other_output=output,
                    company_name=company_name,
                    test_run_id=test_run.id,
                )
                if result:
                    grading_results.append(result)
            
            return {
                "success": True,
                "test_run_id": test_run.id,
                "prompt_version": self._resolved_prompt_version.version,
                "company_name": company_name,
                "gemini_pro_output_id": gemini_pro_output.id,
                "other_outputs_count": len(other_outputs),
                "grading_results_count": len(grading_results),
                "results": grading_results,
            }
            
        finally:
            session.close()
    
    def _ensure_gemini_pro_output(
        self,
        session: Session,
        company_name: str,
        test_run_id: int,
        force_refresh: bool,
        max_iterations: int,
    ) -> Optional[LLMOutputValidation]:
        """Ensure Gemini Pro output exists and is fresh."""
        # Check for existing output from THIS test run
        existing = (
            session.query(LLMOutputValidation)
            .filter(
                LLMOutputValidation.test_name == self.test_name,
                LLMOutputValidation.company_name == company_name,
                LLMOutputValidation.model_provider == "gemini",
                LLMOutputValidation.model_name == self.gemini_pro_model_name,
                LLMOutputValidation.test_run_id == test_run_id,
            )
            .first()
        )
        
        if existing:
            return existing
        
        # Check if we can reuse from a different test run (same prompt version, <24hrs old)
        if not force_refresh:
            hours_threshold = 24
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_threshold)
            
            # Get prompt version for this test run
            test_run = session.query(TestRun).filter(TestRun.id == test_run_id).first()
            if test_run:
                recent_output = (
                    session.query(LLMOutputValidation)
                    .join(TestRun)
                    .filter(
                        LLMOutputValidation.test_name == self.test_name,
                        LLMOutputValidation.company_name == company_name,
                        LLMOutputValidation.model_provider == "gemini",
                        LLMOutputValidation.model_name == self.gemini_pro_model_name,
                        TestRun.prompt_version_id == test_run.prompt_version_id,
                        LLMOutputValidation.created_at >= cutoff_time,
                    )
                    .order_by(LLMOutputValidation.created_at.desc())
                    .first()
                )
                
                if recent_output:
                    # Copy to this test run
                    copied_output = self._copy_output_to_test_run(
                        session=session,
                        source_output=recent_output,
                        target_test_run_id=test_run_id,
                    )
                    if copied_output:
                        return copied_output
        
        # Need to refresh - run agent with Gemini Pro
        return self._run_gemini_pro_and_store(
            session=session,
            company_name=company_name,
            test_run_id=test_run_id,
            max_iterations=max_iterations,
        )
    
    def _run_gemini_pro_and_store(
        self,
        session: Session,
        company_name: str,
        test_run_id: int,
        max_iterations: int,
    ) -> Optional[LLMOutputValidation]:
        """Run agent with Gemini Pro and store result."""
        try:
            # Initialize agent with prompt version
            agent_kwargs = {
                "model_type": "gemini",
                "model_kwargs": {"model_name": self.gemini_pro_model_name},
                "max_iterations": max_iterations,
                "verbose": False,
            }
            
            if self.prompt_version_id:
                agent_kwargs["prompt_version_id"] = self.prompt_version_id
            elif self.prompt_name:
                agent_kwargs["prompt_name"] = self.prompt_name
                if self.prompt_version:
                    agent_kwargs["prompt_version"] = self.prompt_version
            
            agent = ResearchAgent(**agent_kwargs)
            result: ResearchAgentResult = agent.research_company(company_name)
            
            if not result.success or not result.company_info:
                return None
            
            # Store in database with test_run_id
            output = self._store_output(
                session=session,
                company_name=company_name,
                result=result,
                model_name=self.gemini_pro_model_name,
                model_provider="gemini",
                model_config_id=None,
                test_run_id=test_run_id,
            )
            
            session.commit()
            return output
            
        except Exception as e:
            session.rollback()
            print(f"Error running Gemini Pro: {e}")
            return None
    
    def _run_model_and_store(
        self,
        session: Session,
        company_name: str,
        test_run_id: int,
        model_config: ModelConfiguration,
        max_iterations: int,
    ) -> Optional[LLMOutputValidation]:
        """Run agent for a model and store output."""
        try:
            agent_kwargs = {
                "model_type": model_config.provider,
                "max_iterations": max_iterations,
                "verbose": False,
            }
            
            # Use same prompt version as test run
            if self.prompt_version_id:
                agent_kwargs["prompt_version_id"] = self.prompt_version_id
            
            if model_config.provider == "local":
                if model_config.model_path:
                    agent_kwargs["model_path"] = model_config.model_path
                if model_config.model_key:
                    agent_kwargs["local_model"] = model_config.model_key
            else:
                if model_config.api_identifier:
                    agent_kwargs["model_kwargs"] = {
                        "model_name": model_config.api_identifier
                    }
            
            agent = ResearchAgent(**agent_kwargs)
            result: ResearchAgentResult = agent.research_company(company_name)
            
            if not result.success or not result.company_info:
                return None
            
            # Store in database
            output = self._store_output(
                session=session,
                company_name=company_name,
                result=result,
                model_name=model_config.name,
                model_provider=model_config.provider,
                model_config_id=model_config.id,
                test_run_id=test_run_id,
            )
            
            session.commit()
            return output
            
        except Exception as e:
            session.rollback()
            print(f"Error running model {model_config.name}: {e}")
            return None
    
    def _store_output(
        self,
        session: Session,
        company_name: str,
        result: ResearchAgentResult,
        model_name: str,
        model_provider: str,
        model_config_id: Optional[int],
        test_run_id: int,
    ) -> LLMOutputValidation:
        """Store agent result in LLMOutputValidation table."""
        company_info = result.company_info
        
        # Calculate token usage and cost (if available from result)
        input_tokens = getattr(result, 'input_tokens', None)
        output_tokens = getattr(result, 'output_tokens', None)
        total_tokens = None
        estimated_cost = None
        
        if input_tokens and output_tokens:
            total_tokens = input_tokens + output_tokens
            # Calculate cost based on model provider
            estimated_cost = self._calculate_cost(
                model_provider=model_provider,
                model_name=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        
        output = LLMOutputValidation(
            test_run_id=test_run_id,
            test_name=self.test_name,
            company_name=company_name,
            model_configuration_id=model_config_id,
            model_name=model_name,
            model_provider=model_provider,
            company_name_field=company_info.company_name,
            industry=company_info.industry,
            company_size=company_info.company_size,
            headquarters=company_info.headquarters,
            founded=company_info.founded,
            description=company_info.description,
            website=company_info.website,
            products=company_info.products or [],
            competitors=company_info.competitors or [],
            revenue=company_info.revenue,
            funding_stage=company_info.funding_stage,
            growth_stage=company_info.growth_stage,
            industry_vertical=company_info.industry_vertical,
            sub_industry_vertical=company_info.sub_industry_vertical,
            financial_health=company_info.financial_health,
            business_and_technology_adoption=company_info.business_and_technology_adoption,
            primary_workload_philosophy=company_info.primary_workload_philosophy,
            buyer_journey=company_info.buyer_journey,
            budget_maturity=company_info.budget_maturity,
            cloud_spend_capacity=company_info.cloud_spend_capacity,
            procurement_process=company_info.procurement_process,
            key_personas=company_info.key_personas or [],
            execution_time_seconds=result.execution_time_seconds,
            iterations=result.iterations,
            success=result.success,
            raw_output=result.raw_output,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
        )
        
        session.add(output)
        return output
    
    def _calculate_cost(
        self,
        model_provider: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate estimated cost in USD based on model pricing."""
        # Pricing per 1M tokens (as of 2025)
        pricing = {
            "gemini": {
                "gemini-2.0-flash-exp": {"input": 0.15, "output": 0.60},  # Flash pricing
                "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
                "gemini-flash-latest": {"input": 0.075, "output": 0.30},
            },
            "openai": {
                "gpt-4o": {"input": 2.50, "output": 10.00},
                "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            },
            "anthropic": {
                "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
                "claude-3-haiku": {"input": 0.25, "output": 1.25},
            },
        }
        
        provider_pricing = pricing.get(model_provider, {})
        model_pricing = provider_pricing.get(model_name, {"input": 0, "output": 0})
        
        input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (output_tokens / 1_000_000) * model_pricing["output"]
        
        return round(input_cost + output_cost, 6)  # 6 decimal places for precision
    
    def _copy_output_to_test_run(
        self,
        session: Session,
        source_output: LLMOutputValidation,
        target_test_run_id: int,
    ) -> LLMOutputValidation:
        """Copy an existing output to a new test run."""
        # Create a new output record with same data but new test_run_id
        copied = LLMOutputValidation(
            test_run_id=target_test_run_id,
            test_name=source_output.test_name,
            company_name=source_output.company_name,
            model_configuration_id=source_output.model_configuration_id,
            model_name=source_output.model_name,
            model_provider=source_output.model_provider,
            company_name_field=source_output.company_name_field,
            industry=source_output.industry,
            company_size=source_output.company_size,
            headquarters=source_output.headquarters,
            founded=source_output.founded,
            description=source_output.description,
            website=source_output.website,
            products=source_output.products,
            competitors=source_output.competitors,
            revenue=source_output.revenue,
            funding_stage=source_output.funding_stage,
            growth_stage=source_output.growth_stage,
            industry_vertical=source_output.industry_vertical,
            sub_industry_vertical=source_output.sub_industry_vertical,
            financial_health=source_output.financial_health,
            business_and_technology_adoption=source_output.business_and_technology_adoption,
            primary_workload_philosophy=source_output.primary_workload_philosophy,
            buyer_journey=source_output.buyer_journey,
            budget_maturity=source_output.budget_maturity,
            cloud_spend_capacity=source_output.cloud_spend_capacity,
            procurement_process=source_output.procurement_process,
            key_personas=source_output.key_personas,
            execution_time_seconds=source_output.execution_time_seconds,
            iterations=source_output.iterations,
            success=source_output.success,
            raw_output=source_output.raw_output,
        )
        
        session.add(copied)
        return copied
    
    def _delete_other_model_outputs(
        self,
        session: Session,
        company_name: str,
        test_run_id: int,
    ) -> None:
        """Delete outputs from other models for this test run."""
        (
            session.query(LLMOutputValidation)
            .filter(
                LLMOutputValidation.test_name == self.test_name,
                LLMOutputValidation.company_name == company_name,
                LLMOutputValidation.model_provider != "gemini",
                LLMOutputValidation.test_run_id == test_run_id,
            )
            .delete()
        )
        session.commit()
    
    def _get_other_models(self, session: Session) -> List[ModelConfiguration]:
        """Get all active models except Gemini Pro."""
        return (
            session.query(ModelConfiguration)
            .filter(
                ModelConfiguration.is_active == True,
                # Exclude Gemini Pro (could also filter by name if needed)
            )
            .all()
        )
    
    def _get_fields_to_grade(self) -> List[str]:
        """Get list of all fields to grade."""
        # Based on CompanyInfo model
        return [
            "company_name", "industry", "company_size", "headquarters", "founded",
            "description", "website", "products", "competitors", "revenue",
            "funding_stage", "growth_stage", "industry_vertical", 
            "sub_industry_vertical", "financial_health",
            "business_and_technology_adoption", "primary_workload_philosophy",
            "buyer_journey", "budget_maturity", "cloud_spend_capacity",
            "procurement_process", "key_personas",
        ]
    
    def _grade_output_with_flash(
        self,
        session: Session,
        gemini_pro_output: LLMOutputValidation,
        other_output: LLMOutputValidation,
        company_name: str,
        test_run_id: int,
    ) -> Optional[LLMOutputValidationResult]:
        """Grade other model's output using Gemini Flash."""
        from src.models.model_factory import get_chat_model
        import re
        
        try:
            # Get fields to grade
            fields_to_grade = self._get_fields_to_grade()
            
            # Grade each field
            field_scores = {}
            grading_responses = []
            total_grading_input_tokens = 0
            total_grading_output_tokens = 0
            
            flash_model = get_chat_model(
                model_type="gemini",
                model_kwargs={"model_name": self.gemini_flash_model_name},
            )
            
            for field_name in fields_to_grade:
                correct_value = getattr(gemini_pro_output, field_name, None)
                actual_value = getattr(other_output, field_name, None)
                
                field_result = self._grade_field(
                    flash_model=flash_model,
                    field_name=field_name,
                    correct_value=correct_value,
                    actual_value=actual_value,
                )
                
                # Store enhanced field result
                field_scores[field_name] = {
                    "score": field_result["score"],
                    "match_type": field_result["match_type"],
                    "explanation": field_result["explanation"],
                    "confidence": field_result["confidence"],
                }
                
                # Accumulate token usage
                total_grading_input_tokens += field_result.get("input_tokens", 0)
                total_grading_output_tokens += field_result.get("output_tokens", 0)
                
                grading_responses.append(
                    f"{field_name}: {field_result['score']}% "
                    f"({field_result['match_type']}) - {field_result['explanation']}"
                )
            
            # Calculate aggregate scores
            all_scores = [result['score'] for result in field_scores.values() if result is not None]
            overall_accuracy = sum(all_scores) / len(all_scores) if all_scores else 0.0
            
            # Calculate average confidence
            all_confidences = [result['confidence'] for result in field_scores.values() if result is not None]
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
            
            # Separate required vs optional fields
            required_fields = [
                "company_name", "industry", "company_size", 
                "headquarters", "founded"
            ]
            required_scores = [
                field_scores[f]['score'] for f in required_fields 
                if f in field_scores and field_scores[f] is not None
            ]
            required_accuracy = (
                sum(required_scores) / len(required_scores) 
                if required_scores else 0.0
            )
            
            optional_scores = [
                result['score'] for f, result in field_scores.items() 
                if f not in required_fields and result is not None
            ]
            optional_accuracy = (
                sum(optional_scores) / len(optional_scores) 
                if optional_scores else 0.0
            )
            
            # Calculate weighted accuracy (critical fields count 2x)
            critical_fields = ["industry", "company_size", "industry_vertical"]
            weighted_scores = []
            for field, result in field_scores.items():
                if result is not None:
                    weight = 2.0 if field in critical_fields else 1.0
                    weighted_scores.extend([result['score']] * int(weight))
            weighted_accuracy = sum(weighted_scores) / len(weighted_scores) if weighted_scores else 0.0
            
            # Calculate grading cost
            grading_total_tokens = total_grading_input_tokens + total_grading_output_tokens
            grading_cost = self._calculate_cost(
                model_provider="gemini",
                model_name=self.gemini_flash_model_name,
                input_tokens=total_grading_input_tokens,
                output_tokens=total_grading_output_tokens,
            )
            
            # Store result
            result = LLMOutputValidationResult(
                output_id=other_output.id,
                test_run_id=test_run_id,
                test_name=self.test_name,
                company_name=company_name,
                model_name=other_output.model_name,
                model_provider=other_output.model_provider,
                field_accuracy_scores=field_scores,  # Now includes {score, match_type, explanation, confidence}
                overall_accuracy=overall_accuracy,
                required_fields_accuracy=required_accuracy,
                optional_fields_accuracy=optional_accuracy,
                weighted_accuracy=weighted_accuracy,
                graded_by_model=self.gemini_flash_model_name,
                grading_prompt_version_id=None,  # TODO: Get from active grading prompt version
                grading_response="\n".join(grading_responses),
                grading_confidence=avg_confidence,
                grading_input_tokens=total_grading_input_tokens,
                grading_output_tokens=total_grading_output_tokens,
                grading_total_tokens=grading_total_tokens,
                grading_cost_usd=grading_cost,
            )
            
            session.add(result)
            session.commit()
            return result
            
        except Exception as e:
            session.rollback()
            print(f"Error grading output: {e}")
            return None
    
    def _grade_field(
        self,
        flash_model,
        field_name: str,
        correct_value: Any,
        actual_value: Any,
    ) -> Dict[str, Any]:
        """Grade a single field using Gemini Flash with enhanced output."""
        
        if correct_value is None:
            # If ground truth is None, check if actual is also None
            is_match = actual_value is None
            return {
                "score": 100 if is_match else 0,
                "match_type": "exact" if is_match else "none",
                "explanation": "Correct value is None, actual is " + ("None" if is_match else "not None"),
                "confidence": 1.0,
            }
        
        if actual_value is None:
            return {
                "score": 0,
                "match_type": "none",
                "explanation": "Field is missing",
                "confidence": 1.0,
            }
        
        # Create grading prompt (version should come from GradingPromptVersion table)
        prompt = f"""You are grading the accuracy of a data field extracted by an LLM.

Field name: {field_name}
Correct value (from Gemini Pro): {correct_value}
Actual value (to grade): {actual_value}

Rate the accuracy and provide structured output:

1. Score (0-100):
   - Exact matches = 100%
   - Close/similar meanings = 70-99%
   - Related but different = 40-69%
   - Partially correct = 20-39%
   - Completely wrong or missing = 0-19%

2. Match type: exact | semantic | partial | none

3. Brief explanation

4. Confidence (0-1): How confident are you in this grading?

Respond in this format:
SCORE: <number>
MATCH_TYPE: <type>
CONFIDENCE: <0-1>
EXPLANATION: <text>"""

        try:
            response = flash_model.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Extract token usage from response metadata (if available)
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, 'response_metadata'):
                usage = response.response_metadata.get('usage', {})
                input_tokens = usage.get('prompt_tokens', 0) or usage.get('input_tokens', 0)
                output_tokens = usage.get('completion_tokens', 0) or usage.get('output_tokens', 0)
            elif hasattr(response, 'usage_metadata'):
                input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
                output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
            
            # Parse structured response
            score_match = re.search(r'SCORE:\s*(\d+)', response_text)
            match_type_match = re.search(r'MATCH_TYPE:\s*(\w+)', response_text)
            confidence_match = re.search(r'CONFIDENCE:\s*([\d.]+)', response_text)
            explanation_match = re.search(r'EXPLANATION:\s*(.+)', response_text, re.DOTALL)
            
            score = int(score_match.group(1)) if score_match else 0
            score = max(0, min(100, score))  # Clamp to 0-100
            
            match_type = match_type_match.group(1).lower() if match_type_match else "unknown"
            if match_type not in ["exact", "semantic", "partial", "none"]:
                match_type = "unknown"
            
            confidence = float(confidence_match.group(1)) if confidence_match else 0.5
            confidence = max(0, min(1, confidence))  # Clamp to 0-1
            
            explanation = explanation_match.group(1).strip() if explanation_match else response_text
            
            return {
                "score": score,
                "match_type": match_type,
                "explanation": explanation,
                "confidence": confidence,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
                
        except Exception as e:
            return {
                "score": 0,
                "match_type": "error",
                "explanation": f"Error: {e}",
                "confidence": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
            }
    
    def run_test_suite(
        self,
        company_names: List[str],
        other_models: Optional[List[ModelConfiguration]] = None,
        force_refresh: bool = False,
        max_iterations: int = 10,
        test_suite_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run tests across multiple companies as part of a test suite.
        
        This creates a test run for each company, all linked by test_suite_name.
        Useful for testing prompt accuracy across a broader set of companies.
        
        Args:
            company_names: List of company names to test
            other_models: List of model configs to test (excludes Gemini Pro)
            force_refresh: Force refresh even if Gemini Pro data is fresh
            max_iterations: Max agent iterations
            test_suite_name: Name for this test suite (auto-generated if not provided)
            
        Returns:
            Dict with aggregated results across all companies
        """
        import uuid
        
        if not test_suite_name:
            # Generate a unique test suite name
            test_suite_name = f"test-suite-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
        
        results = []
        successful_companies = []
        failed_companies = []
        
        for company_name in company_names:
            try:
                result = self.run_test(
                    company_name=company_name,
                    other_models=other_models,
                    force_refresh=force_refresh,
                    max_iterations=max_iterations,
                    test_suite_name=test_suite_name,
                )
                
                if result.get("success"):
                    successful_companies.append(company_name)
                    results.append(result)
                else:
                    failed_companies.append({
                        "company": company_name,
                        "error": result.get("error", "Unknown error")
                    })
            except Exception as e:
                failed_companies.append({
                    "company": company_name,
                    "error": str(e)
                })
        
        # Aggregate accuracy scores across all companies
        all_overall_accuracies = []
        all_required_accuracies = []
        all_optional_accuracies = []
        
        for result in results:
            for validation_result in result.get("results", []):
                if hasattr(validation_result, 'overall_accuracy'):
                    all_overall_accuracies.append(validation_result.overall_accuracy)
                if hasattr(validation_result, 'required_fields_accuracy'):
                    all_required_accuracies.append(validation_result.required_fields_accuracy)
                if hasattr(validation_result, 'optional_fields_accuracy'):
                    all_optional_accuracies.append(validation_result.optional_fields_accuracy)
        
        return {
            "success": len(successful_companies) > 0,
            "test_suite_name": test_suite_name,
            "total_companies": len(company_names),
            "successful_companies": len(successful_companies),
            "failed_companies": len(failed_companies),
            "company_results": results,
            "failed_details": failed_companies,
            "aggregated_accuracy": {
                "overall": sum(all_overall_accuracies) / len(all_overall_accuracies) if all_overall_accuracies else 0.0,
                "required_fields": sum(all_required_accuracies) / len(all_required_accuracies) if all_required_accuracies else 0.0,
                "optional_fields": sum(all_optional_accuracies) / len(all_optional_accuracies) if all_optional_accuracies else 0.0,
            },
            "prompt_version": self._resolved_prompt_version.version if self._resolved_prompt_version else None,
        }
```

### 4. Prompt Analytics & Comparison

```python
# src/testing/prompt_analytics.py

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database.schema import (
    TestRun, LLMOutputValidationResult, PromptVersion,
    get_session
)

class PromptAnalytics:
    """Analyze accuracy across different prompt versions."""
    
    @staticmethod
    def compare_prompt_versions(
        prompt_name: str,
        company_name: Optional[str] = None,
        test_suite_name: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> List[Dict[str, Any]]:
        """
        Compare accuracy scores across different prompt versions.
        
        Can filter by:
        - Single company (company_name)
        - Test suite (test_suite_name) - aggregates across all companies in suite
        
        Returns list of dicts with:
        - prompt_version: Version string
        - average_overall_accuracy: Average accuracy across all test runs
        - average_required_fields_accuracy: Average required fields accuracy
        - average_optional_fields_accuracy: Average optional fields accuracy
        - test_run_count: Number of test runs using this version
        - company_count: Number of unique companies tested
        """
        db_session = session or get_session()
        try:
            query = (
                db_session.query(
                    PromptVersion.version,
                    func.avg(LLMOutputValidationResult.overall_accuracy).label('avg_overall'),
                    func.avg(LLMOutputValidationResult.required_fields_accuracy).label('avg_required'),
                    func.avg(LLMOutputValidationResult.optional_fields_accuracy).label('avg_optional'),
                    func.count(TestRun.id.distinct()).label('run_count'),
                    func.count(TestRun.company_name.distinct()).label('company_count'),
                )
                .join(TestRun, TestRun.prompt_version_id == PromptVersion.id)
                .join(LLMOutputValidationResult, LLMOutputValidationResult.test_run_id == TestRun.id)
                .filter(PromptVersion.prompt_name == prompt_name)
            )
            
            if company_name:
                query = query.filter(TestRun.company_name == company_name)
            
            if test_suite_name:
                query = query.filter(TestRun.test_suite_name == test_suite_name)
            
            results = (
                query
                .group_by(PromptVersion.version)
                .order_by(PromptVersion.created_at.desc())
                .all()
            )
            
            return [
                {
                    "prompt_version": r.version,
                    "average_overall_accuracy": float(r.avg_overall or 0),
                    "average_required_fields_accuracy": float(r.avg_required or 0),
                    "average_optional_fields_accuracy": float(r.avg_optional or 0),
                    "test_run_count": r.run_count,
                    "company_count": r.company_count,
                    "created_at": (
                        db_session.query(PromptVersion.created_at)
                        .filter(PromptVersion.prompt_name == prompt_name, PromptVersion.version == r.version)
                        .scalar()
                    ),
                }
                for r in results
            ]
            
        finally:
            if not session:
                db_session.close()
    
    @staticmethod
    def get_test_run_history(
        prompt_name: Optional[str] = None,
        company_name: Optional[str] = None,
        limit: int = 50,
        session: Optional[Session] = None,
    ) -> List[Dict[str, Any]]:
        """Get history of test runs with their accuracy scores."""
        db_session = session or get_session()
        try:
            query = (
                db_session.query(
                    TestRun.id,
                    TestRun.test_name,
                    TestRun.company_name,
                    TestRun.prompt_name,
                    TestRun.prompt_version,
                    TestRun.created_at,
                    func.avg(LLMOutputValidationResult.overall_accuracy).label('avg_accuracy'),
                    func.count(LLMOutputValidationResult.id).label('result_count'),
                )
                .outerjoin(LLMOutputValidationResult, LLMOutputValidationResult.test_run_id == TestRun.id)
                .group_by(TestRun.id)
            )
            
            if prompt_name:
                query = query.filter(TestRun.prompt_name == prompt_name)
            if company_name:
                query = query.filter(TestRun.company_name == company_name)
            
            results = (
                query
                .order_by(TestRun.created_at.desc())
                .limit(limit)
                .all()
            )
            
            return [
                {
                    "test_run_id": r.id,
                    "test_name": r.test_name,
                    "company_name": r.company_name,
                    "prompt_name": r.prompt_name,
                    "prompt_version": r.prompt_version,
                    "created_at": r.created_at,
                    "average_accuracy": float(r.avg_accuracy or 0),
                    "result_count": r.result_count,
                }
                for r in results
            ]
            
        finally:
            if not session:
                db_session.close()
    
    @staticmethod
    def get_cost_analysis(
        prompt_name: Optional[str] = None,
        test_suite_name: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Analyze costs across test runs.
        
        Returns:
        - Total costs (agent runs + grading)
        - Cost per company
        - Cost per prompt version
        - Token usage statistics
        """
        db_session = session or get_session()
        try:
            query = (
                db_session.query(
                    TestRun.prompt_version,
                    TestRun.company_name,
                    LLMOutputValidation.model_name,
                    func.sum(LLMOutputValidation.total_tokens).label('agent_tokens'),
                    func.sum(LLMOutputValidation.estimated_cost_usd).label('agent_cost'),
                    func.sum(LLMOutputValidationResult.grading_total_tokens).label('grading_tokens'),
                    func.sum(LLMOutputValidationResult.grading_cost_usd).label('grading_cost'),
                )
                .join(LLMOutputValidation, LLMOutputValidation.test_run_id == TestRun.id)
                .outerjoin(LLMOutputValidationResult, LLMOutputValidationResult.output_id == LLMOutputValidation.id)
            )
            
            if prompt_name:
                query = query.filter(TestRun.prompt_name == prompt_name)
            if test_suite_name:
                query = query.filter(TestRun.test_suite_name == test_suite_name)
            
            results = query.group_by(
                TestRun.prompt_version,
                TestRun.company_name,
                LLMOutputValidation.model_name,
            ).all()
            
            # Aggregate costs
            total_agent_cost = 0.0
            total_grading_cost = 0.0
            total_agent_tokens = 0
            total_grading_tokens = 0
            
            cost_by_prompt = {}
            cost_by_company = {}
            cost_by_model = {}
            
            for r in results:
                agent_cost = float(r.agent_cost or 0)
                grading_cost = float(r.grading_cost or 0)
                agent_tokens = int(r.agent_tokens or 0)
                grading_tokens = int(r.grading_tokens or 0)
                
                total_agent_cost += agent_cost
                total_grading_cost += grading_cost
                total_agent_tokens += agent_tokens
                total_grading_tokens += grading_tokens
                
                # By prompt version
                if r.prompt_version not in cost_by_prompt:
                    cost_by_prompt[r.prompt_version] = {"agent": 0.0, "grading": 0.0, "total": 0.0}
                cost_by_prompt[r.prompt_version]["agent"] += agent_cost
                cost_by_prompt[r.prompt_version]["grading"] += grading_cost
                cost_by_prompt[r.prompt_version]["total"] += agent_cost + grading_cost
                
                # By company
                if r.company_name not in cost_by_company:
                    cost_by_company[r.company_name] = {"agent": 0.0, "grading": 0.0, "total": 0.0}
                cost_by_company[r.company_name]["agent"] += agent_cost
                cost_by_company[r.company_name]["grading"] += grading_cost
                cost_by_company[r.company_name]["total"] += agent_cost + grading_cost
                
                # By model
                if r.model_name not in cost_by_model:
                    cost_by_model[r.model_name] = {"agent": 0.0, "grading": 0.0, "total": 0.0}
                cost_by_model[r.model_name]["agent"] += agent_cost
                cost_by_model[r.model_name]["grading"] += grading_cost
                cost_by_model[r.model_name]["total"] += agent_cost + grading_cost
            
            return {
                "total": {
                    "agent_cost": round(total_agent_cost, 4),
                    "grading_cost": round(total_grading_cost, 4),
                    "total_cost": round(total_agent_cost + total_grading_cost, 4),
                    "agent_tokens": total_agent_tokens,
                    "grading_tokens": total_grading_tokens,
                    "total_tokens": total_agent_tokens + total_grading_tokens,
                },
                "by_prompt_version": {
                    k: {kk: round(vv, 4) for kk, vv in v.items()}
                    for k, v in cost_by_prompt.items()
                },
                "by_company": {
                    k: {kk: round(vv, 4) for kk, vv in v.items()}
                    for k, v in cost_by_company.items()
                },
                "by_model": {
                    k: {kk: round(vv, 4) for kk, vv in v.items()}
                    for k, v in cost_by_model.items()
                },
            }
            
        finally:
            if not session:
                db_session.close()
```

### 5. Updated ResearchAgent Integration

The `ResearchAgent` class needs to support loading prompts from the database:

```python
# src/agent/research_agent.py - Updated __init__ method

def __init__(
    self,
    model_type: str = "local",
    verbose: bool = True,
    max_iterations: int = 10,
    instructions_path: Optional[str] = None,  # Legacy: still supported
    profiling_guide_path: Optional[str] = None,  # Legacy: still supported
    prompt_version_id: Optional[int] = None,  # NEW: Use specific prompt version
    prompt_name: Optional[str] = None,  # NEW: Use active version of named prompt
    prompt_version: Optional[str] = None,  # NEW: Use specific version string
    local_model: Optional[str] = None,
    model_path: Optional[str] = None,
    model_kwargs: Optional[Dict[str, Any]] = None,
    enable_diagnostics: bool = False,
) -> None:
    # ... existing initialization ...
    
    # NEW: Load prompts from database if prompt_version_id or prompt_name provided
    if prompt_version_id:
        from src.prompts.prompt_manager import PromptManager
        prompt_version = PromptManager.get_version_by_id(prompt_version_id)
        if prompt_version:
            self._instructions = prompt_version.instructions_content
            self._profiling_guide = prompt_version.classification_reference_content or ""
            self._prompt_version_id = prompt_version_id
            self._prompt_name = prompt_version.prompt_name
            self._prompt_version = prompt_version.version
        else:
            raise ValueError(f"Prompt version ID {prompt_version_id} not found")
    elif prompt_name:
        from src.prompts.prompt_manager import PromptManager
        if prompt_version:
            prompt_version_obj = PromptManager.get_version(prompt_name, prompt_version)
        else:
            prompt_version_obj = PromptManager.get_active_version(prompt_name)
        
        if prompt_version_obj:
            self._instructions = prompt_version_obj.instructions_content
            self._profiling_guide = prompt_version_obj.classification_reference_content or ""
            self._prompt_version_id = prompt_version_obj.id
            self._prompt_name = prompt_version_obj.prompt_name
            self._prompt_version = prompt_version_obj.version
        else:
            raise ValueError(f"Prompt '{prompt_name}' (version: {prompt_version or 'active'}) not found")
    else:
        # Legacy: Load from files
        self._instructions = self._load_instructions()
        self._profiling_guide = self._load_profiling_guide()
        self._prompt_version_id = None
        self._prompt_name = None
        self._prompt_version = None
    
    # ... rest of initialization ...
```

---

## Cost & Performance Considerations

### API Cost Estimation

**Per Company Test Run**:
- Gemini Pro (ground truth): ~1M tokens = ~$3.50 (cached after first run)
- Gemini Flash (grading ~20 fields): ~500K tokens = ~$0.50
- Local models (Llama): $0 (compute only)
- **Total per company (first run)**: ~$4.00
- **Total per company (cached)**: ~$0.50 (grading only)

**Test Suite (5 companies)**:
- Ground truth: $3.50 (cached for all companies with same prompt)
- Grading 3 models × 5 companies: ~$7.50
- **Total**: ~$11 per test suite (first run)
- **Total**: ~$7.50 per test suite (cached ground truth)

**Monthly Budget Estimate**:
- 4 prompt versions/month
- 5 companies per test
- 3 models to grade
- **Monthly cost**: ~$44-60

### Performance Targets

- Single company test: < 5 minutes
- Test suite (5 companies): < 15 minutes
- Grading all fields: < 30 seconds per model
- Database queries: < 100ms for comparisons

### Optimization Strategies

1. **Ground Truth Caching**: 24-hour cache reduces redundant Gemini Pro calls
2. **Batch Grading**: Consider batching multiple fields into single API call
3. **Parallel Execution**: Future - run multiple company tests simultaneously
4. **Smart Caching**: Cache by (company, agent_prompt_version, grading_prompt_version)
5. **Incremental Testing**: Only test changed prompt versions

---

## Edge Cases & Error Handling

### Model Output Issues

| Issue | Handling Strategy | Database Flag |
|-------|------------------|---------------|
| **Malformed JSON** | Parse error → 0% score | `error_message` populated |
| **Missing Fields** | 0% for missing, grade present | Track in field_accuracy_scores |
| **Timeout** | Retry once, mark failed | `success = False` |
| **Refusal** | 0% score | `error_message = "refusal"` |
| **Partial Response** | Grade what's present | Note in validation_notes |

### Grading Edge Cases

| Case | Handling | Score |
|------|----------|-------|
| **Both Empty** | Both provided nothing | 100% |
| **Ground Truth Empty** | Flag for review | N/A |
| **Very Low Confidence** | Flag for human review | Store confidence |
| **Parse Error** | Store raw response | 0% with error flag |

### Ground Truth Validation Workflow

1. Initial runs: `ground_truth_status = 'unvalidated'`
2. Manual review: Update to `'validated'` or `'disputed'`
3. If disputed: Add `validation_notes`, optionally correct
4. Periodic spot checks: Random 10% sample validation

---

## Implementation Plan

### Phase 1: Database Schema & Prompt Versioning (Week 1)

**Tasks:**
1. Add `PromptVersion` table to `src/database/schema.py`
2. Add `GradingPromptVersion` table to `src/database/schema.py` ⭐ NEW
3. Add `TestRun` table to `src/database/schema.py`
4. Add `LLMOutputValidation` table with enhanced fields ⭐ ENHANCED
   - Ground truth validation: `ground_truth_status`, `human_validated_at`, `validation_notes`
   - Token tracking: `input_tokens`, `output_tokens`, `total_tokens`, `estimated_cost_usd`
5. Add `LLMOutputValidationResult` table with enhanced fields ⭐ ENHANCED
   - Accuracy: `weighted_accuracy`, `grading_confidence`
   - Grading tracking: `grading_prompt_version_id`
   - Token tracking: `grading_input_tokens`, `grading_output_tokens`, `grading_total_tokens`, `grading_cost_usd`
   - Update `field_accuracy_scores` to store structured data (score, match_type, explanation, confidence)
6. Update `create_database()` function to create new tables
7. Create database migration script if needed

**Deliverables:**
- All database tables defined and created
- Foreign key relationships properly set up (including grading prompt versions)
- Database indexes for query performance
- Ground truth validation fields ready for manual review workflow

**Testing:**
- Verify tables are created correctly
- Test foreign key constraints
- Verify indexes are created
- Test ground truth status enum values
- Test JSON field storage for enhanced field_accuracy_scores

---

### Phase 2: Prompt Management System (Week 1-2)

**Tasks:**
1. Create `src/prompts/__init__.py`
2. Implement `PromptManager` class (`src/prompts/prompt_manager.py`)
   - Support both agent prompts and grading prompts
3. Implement `GradingPromptManager` class ⭐ NEW
   - Load/create/version grading prompts
   - Track consistency scores
4. Create `scripts/initialize_prompts.py` - Script to load prompts from files
   - Initialize both agent and grading prompts
5. Create initial grading prompt template (v1.0) ⭐ NEW
6. Test loading prompts from `prompts/research-agent-prompt.md`
7. Create initial prompt versions (agent: "1.0", grading: "1.0")

**Deliverables:**
- `PromptManager` class with all CRUD operations
- `GradingPromptManager` class for grading prompts
- CLI script to initialize both types of prompts
- At least one version of each prompt type in database
- Default grading prompt with clear scoring rubric

**Testing:**
- Test loading agent prompts from files
- Test creating grading prompts programmatically
- Test creating versions
- Test retrieving active version for both types
- Test retrieving specific version
- Test grading prompt consistency tracking

---

### Phase 3: ResearchAgent Integration (Week 2)

**Tasks:**
1. Update `ResearchAgent.__init__()` to accept prompt version parameters
2. Implement database prompt loading in `ResearchAgent`
3. Maintain backward compatibility with file-based prompts
4. Test ResearchAgent with database prompts
5. Test ResearchAgent with file-based prompts (legacy)

**Deliverables:**
- ResearchAgent supports both database and file-based prompts
- Backward compatibility maintained
- All existing code continues to work

**Testing:**
- Test agent with prompt_version_id
- Test agent with prompt_name
- Test agent with file-based prompts (legacy)
- Verify prompts are loaded correctly

---

### Phase 4: LLM Output Validation Runner (Week 2-3)

**Tasks:**
1. Create `src/testing/llm_output_validation_runner.py`
2. Implement `LLMOutputValidationRunner` class
3. Implement Gemini Pro ground truth logic (with 24hr refresh)
   - Set `ground_truth_status = 'unvalidated'` for new outputs
4. Implement model execution and storage
5. Implement Gemini Flash grading system with enhanced output ⭐ ENHANCED
   - Return structured results: score, match_type, explanation, confidence
   - Load grading prompt from database (versioned)
6. Implement field-by-field grading with weighted scoring ⭐ ENHANCED
   - Calculate overall, required, optional, AND weighted accuracy
   - Store grading confidence
7. Implement ground truth validation helpers ⭐ NEW
   - Functions to mark outputs as validated/disputed
   - Spot-check selection logic
8. Test end-to-end workflow

**Deliverables:**
- Complete test runner implementation
- Ground truth refresh logic working
- Enhanced grading system with structured output
- Weighted scoring implementation
- Ground truth validation workflow
- All outputs stored in database with proper metadata

**Testing:**
- Test with single model
- Test with multiple models
- Test 24hr refresh logic
- Test enhanced grading output structure
- Test weighted vs simple accuracy calculations
- Test ground truth validation status updates
- Verify all data stored correctly (including new fields)
- Test grading consistency (same input → similar scores)

---

### Phase 5: CLI & Scripts (Week 3)

**Tasks:**
1. Create `scripts/run_llm_output_validation.py` - Main CLI runner
2. Update `scripts/initialize_prompts.py` (if needed)
3. Create `scripts/compare_prompt_versions.py` - Analytics script
4. Add help text and error handling
5. Test all CLI commands

**Deliverables:**
- Working CLI for running tests
- Script to initialize prompts
- Script to compare prompt versions
- Good user experience with clear messages

**Testing:**
- Test CLI with all options
- Test error handling
- Test output formatting
- Verify all commands work correctly

---

### Phase 6: UI Integration (Week 3-4)

**Tasks:**
1. Create or update `src/ui/pages/5_🧪_LLM_Output_Validation.py`
2. Add prompt version selector
3. Add test run execution UI
4. Add results display with accuracy scores
5. Add prompt version comparison view
6. Add charts/graphs for accuracy over time

**Deliverables:**
- Full-featured UI page for test execution
- Visual comparison of prompt versions
- Historical accuracy charts
- Export capabilities

**Testing:**
- Test UI workflow end-to-end
- Test prompt version selection
- Test results display
- Test comparison views

---

### Phase 7: Analytics & Reporting (Week 4)

**Tasks:**
1. Implement `PromptAnalytics` class (`src/testing/prompt_analytics.py`)
2. Create comparison queries
3. Add visualization helpers
4. Test analytics functions

**Deliverables:**
- Analytics class for comparing prompt versions
- Query functions for test run history
- Helper functions for UI integration

**Testing:**
- Test comparison queries
- Test with multiple prompt versions
- Test with multiple companies
- Verify accuracy calculations

---

### Phase 8: Testing & Documentation (Week 4)

**Tasks:**
1. Write integration tests for test runner
2. Write unit tests for prompt manager
3. Test grading accuracy edge cases
4. Document usage examples
5. Create user guide

**Deliverables:**
- Comprehensive test coverage
- Usage documentation
- User guide with examples
- API documentation

**Testing:**
- Run all tests
- Test edge cases
- Verify documentation accuracy

---

## File Structure

```
src/
├── database/
│   └── schema.py              # Updated with new tables
├── prompts/
│   ├── __init__.py
│   └── prompt_manager.py      # NEW: Prompt version management
├── testing/
│   ├── llm_output_validation_runner.py  # NEW: Main test runner
│   └── prompt_analytics.py    # NEW: Analytics and comparison
├── agent/
│   └── research_agent.py      # Updated: Support database prompts

scripts/
├── run_llm_output_validation.py    # NEW: Main CLI runner
├── initialize_prompts.py           # NEW: Initialize prompts from files
└── compare_prompt_versions.py      # NEW: Compare accuracy across versions

src/ui/pages/
└── 5_🧪_LLM_Output_Validation.py   # NEW: UI page for testing
```

---

## Usage Examples

### Initializing Prompts

```bash
# Load prompt from file into database
python scripts/initialize_prompts.py \
    --prompt research-agent-prompt.md \
    --version 1.0 \
    --description "Initial version" \
    --created-by "System"

# Create new version after editing prompt file
python scripts/initialize_prompts.py \
    --prompt research-agent-prompt.md \
    --version 1.1 \
    --description "Simplified instructions section"
```

### Running Tests

```bash
# Run test for single company with active prompt version
python scripts/run_llm_output_validation.py \
    --company "BitMovin" \
    --test-run-description "Testing v1.0 prompt"

# Run test suite across multiple companies
python scripts/run_llm_output_validation.py \
    --companies "BitMovin" "Stripe" "OpenAI" "Anthropic" "Vercel" \
    --test-suite-name "prompt-v1.0-validation" \
    --test-run-description "Testing v1.0 prompt across diverse companies"

# Run test with specific prompt version
python scripts/run_llm_output_validation.py \
    --company "BitMovin" \
    --prompt-name research-agent-prompt \
    --prompt-version 1.1

# Force refresh Gemini Pro output
python scripts/run_llm_output_validation.py \
    --company "BitMovin" \
    --force-refresh

# Compare prompt versions across a test suite
python scripts/compare_prompt_versions.py \
    --prompt research-agent-prompt \
    --test-suite-name "prompt-v1.0-validation"
```

### Comparing Prompt Versions

```bash
# Compare accuracy across prompt versions
python scripts/compare_prompt_versions.py \
    --prompt research-agent-prompt \
    --company BitMovin
```

### Programmatic Usage

```python
from src.testing.llm_output_validation_runner import LLMOutputValidationRunner
from src.prompts.prompt_manager import PromptManager

# Get prompt version
prompt_version = PromptManager.get_active_version("research-agent-prompt")

# Run single company test
runner = LLMOutputValidationRunner(
    prompt_version_id=prompt_version.id,
    test_run_description="Testing improved prompt"
)

result = runner.run_test(
    company_name="BitMovin",
    max_iterations=10,
)

print(f"Test Run ID: {result['test_run_id']}")
print(f"Overall accuracy: {result['results'][0].overall_accuracy:.1f}%")

# Run test suite across multiple companies
test_suite_result = runner.run_test_suite(
    company_names=["BitMovin", "Stripe", "OpenAI", "Anthropic", "Vercel"],
    test_suite_name="prompt-v1.0-validation",
    max_iterations=10,
)

print(f"Test Suite: {test_suite_result['test_suite_name']}")
print(f"Successfully tested: {test_suite_result['successful_companies']}/{test_suite_result['total_companies']} companies")
print(f"Aggregated Overall Accuracy: {test_suite_result['aggregated_accuracy']['overall']:.1f}%")
print(f"Aggregated Required Fields: {test_suite_result['aggregated_accuracy']['required_fields']:.1f}%")

# Compare prompt versions
from src.testing.prompt_analytics import PromptAnalytics

# Compare across single company
comparison = PromptAnalytics.compare_prompt_versions(
    prompt_name="research-agent-prompt",
    company_name="BitMovin",
)

# Compare across test suite
suite_comparison = PromptAnalytics.compare_prompt_versions(
    prompt_name="research-agent-prompt",
    test_suite_name="prompt-v1.0-validation",
)

for version_data in suite_comparison:
    print(f"Version {version_data['prompt_version']}: "
          f"{version_data['average_overall_accuracy']:.1f}% accuracy "
          f"({version_data['company_count']} companies, "
          f"{version_data['test_run_count']} test runs)")

# Get cost analysis
cost_analysis = PromptAnalytics.get_cost_analysis(
    prompt_name="research-agent-prompt",
    test_suite_name="prompt-v1.0-validation",
)

print(f"\nCost Analysis:")
print(f"Total Agent Cost: ${cost_analysis['total']['agent_cost']:.2f}")
print(f"Total Grading Cost: ${cost_analysis['total']['grading_cost']:.2f}")
print(f"Total Cost: ${cost_analysis['total']['total_cost']:.2f}")
print(f"Total Tokens: {cost_analysis['total']['total_tokens']:,}")

print(f"\nCost by Prompt Version:")
for version, costs in cost_analysis['by_prompt_version'].items():
    print(f"  {version}: ${costs['total']:.2f} (agent: ${costs['agent']:.2f}, grading: ${costs['grading']:.2f})")

print(f"\nCost by Company:")
for company, costs in cost_analysis['by_company'].items():
    print(f"  {company}: ${costs['total']:.2f}")
```

---

## Grading Logic Details

### Field-Level Grading

**Process:**
1. For each field, Gemini Flash receives:
   - Field name
   - Correct value (from Gemini Pro)
   - Actual value (from model being graded)

2. Gemini Flash responds with:
   - Percentage score (0-100)
   - Brief explanation

3. Scores are interpreted as:
   - 100% = Exact match
   - 70-99% = Close/similar meaning
   - 40-69% = Related but different
   - 20-39% = Partially correct
   - 0-19% = Completely wrong or missing

### Aggregate Scores

- **Overall Accuracy**: Average of all field scores
- **Required Fields Accuracy**: Average of required fields (company_name, industry, company_size, headquarters, founded)
- **Optional Fields Accuracy**: Average of optional fields

---

## Success Metrics

1. **Prompt Versioning**: Can track multiple prompt versions (both agent and grading) and compare accuracy
2. **Grading Accuracy**: Gemini Flash produces consistent scores (within 5% variance across 3 runs)
3. **Ground Truth Quality**: >90% validation rate on manual spot checks
4. **Historical Tracking**: Can see accuracy trends over time with clear visualizations
5. **Prompt Engineering**: >10% accuracy improvement detectable when prompt genuinely improves
6. **Performance**: Single company test completes in < 5 minutes
7. **Cost Efficiency**: Test suite (5 companies) costs < $15
8. **Usability**: UI clearly shows prompt version impact on accuracy with actionable insights
9. **Weighted Scoring**: Critical fields appropriately weighted in accuracy calculations
10. **Confidence Tracking**: Low-confidence gradings flagged for human review

---

## Open Questions (Resolved)

1. ✅ **Ground Truth Source**: Gemini 2.5 Pro output is assumed correct
2. ✅ **Grading Method**: Gemini Flash grades field-by-field with percentage scores
3. ✅ **Prompt Storage**: Prompts stored in database with versioning
4. ✅ **Test Run Tracking**: Each test run links to a prompt version
5. ✅ **Refresh Logic**: Gemini Pro output refreshed if >24hrs old or if force_refresh=True

---

## Next Steps

1. **Begin Phase 1** - Set up database schema
2. **Begin Phase 2** - Implement prompt management
3. **Begin Phase 3** - Integrate with ResearchAgent
4. **Iterate** - Build incrementally, test as we go
5. **Document** - Update documentation as features are added

---

**Status**: 📋 **PLANNING ENHANCED & UPDATED - READY FOR IMPLEMENTATION**  
**Last Updated**: 2025-11-03  

**Key Enhancements**:
- ✅ Grading prompt versioning system added
- ✅ Ground truth validation workflow with status tracking (structure only, workflow deferred)
- ✅ Enhanced field grading with structured output (score, match_type, explanation, confidence)
- ✅ Weighted accuracy scoring for critical fields
- ✅ **Token usage tracking for cost analysis** (agent and grading operations)
- ✅ **Automated cost calculation** based on model pricing
- ✅ **Cost analytics** by prompt version, company, and model
- ✅ Cost & performance analysis with optimization strategies
- ✅ Comprehensive edge case handling
- ✅ Specific, measurable success metrics

**Implementation Status**:
- ⏳ Phase 1: Database Schema & Prompt Versioning - NOT STARTED
  - Includes grading prompt version table
  - Ground truth validation fields
  - Enhanced accuracy scoring fields
- ⏳ Phase 2: Prompt Management System - NOT STARTED
  - Agent prompt manager
  - Grading prompt manager (NEW)
- ⏳ Phase 3: ResearchAgent Integration - NOT STARTED
- ⏳ Phase 4: LLM Output Validation Runner - NOT STARTED
  - Enhanced grading with structured output
  - Weighted scoring
  - Ground truth validation helpers
- ⏳ Phase 5: CLI & Scripts - NOT STARTED
- ⏳ Phase 6: UI Integration - NOT STARTED
- ⏳ Phase 7: Analytics & Reporting - NOT STARTED
- ⏳ Phase 8: Testing & Documentation - NOT STARTED

**Related Files** (to be created):
- Database schema: `src/database/schema.py` (updates)
- Prompt manager: `src/prompts/prompt_manager.py`
- Grading prompt manager: `src/prompts/grading_prompt_manager.py` ⭐ NEW
- Test runner: `src/testing/llm_output_validation_runner.py`
- Ground truth validator: `src/testing/ground_truth_validator.py` ⭐ NEW
- Analytics: `src/testing/prompt_analytics.py`
- CLI runner: `scripts/run_llm_output_validation.py`
- Prompt initializer: `scripts/initialize_prompts.py`
- Ground truth review tool: `scripts/review_ground_truth.py` ⭐ NEW
- UI page: `src/ui/pages/5_🧪_LLM_Output_Validation.py`
