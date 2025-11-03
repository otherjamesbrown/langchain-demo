"""
Database schema for storing company research results.

This module defines the SQLAlchemy models and database schema for
storing company information, search history, and execution metadata.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, Float, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

Base = declarative_base()


class Company(Base):
    """
    SQLAlchemy model for company information.
    
    Stores structured company data extracted by the research agent.
    """
    
    __tablename__ = "companies"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Company identification
    company_name = Column(String(255), nullable=False, unique=True, index=True)
    website = Column(String(512), nullable=True)
    
    # Company details
    industry = Column(String(255), nullable=True)
    company_size = Column(String(100), nullable=True)
    company_size_reason = Column(Text, nullable=True)
    headquarters = Column(String(255), nullable=True)
    founded = Column(Integer, nullable=True)

    # GTM and profiling classifications
    growth_stage = Column(String(100), nullable=True)
    growth_stage_reason = Column(Text, nullable=True)
    industry_vertical = Column(String(255), nullable=True)
    industry_vertical_reason = Column(Text, nullable=True)
    sub_industry_vertical = Column(String(255), nullable=True)
    sub_industry_vertical_reason = Column(Text, nullable=True)
    financial_health = Column(String(100), nullable=True)
    financial_health_reason = Column(Text, nullable=True)
    business_and_technology_adoption = Column(String(255), nullable=True)
    business_and_technology_adoption_reason = Column(Text, nullable=True)
    primary_workload_philosophy = Column(String(255), nullable=True)
    primary_workload_philosophy_reason = Column(Text, nullable=True)
    buyer_journey = Column(String(100), nullable=True)
    buyer_journey_reason = Column(Text, nullable=True)
    budget_maturity = Column(String(100), nullable=True)
    budget_maturity_reason = Column(Text, nullable=True)
    cloud_spend_capacity = Column(String(100), nullable=True)
    cloud_spend_capacity_reason = Column(Text, nullable=True)
    procurement_process = Column(String(100), nullable=True)
    procurement_process_reason = Column(Text, nullable=True)
    
    # Financial information
    revenue = Column(String(100), nullable=True)
    funding_stage = Column(String(100), nullable=True)
    
    # Products and market
    products = Column(JSON, nullable=True)  # List of products
    competitors = Column(JSON, nullable=True)  # List of competitors
    key_personas = Column(JSON, nullable=True)
    key_personas_reason = Column(Text, nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Company(id={self.id}, name='{self.company_name}')>"


class SearchHistory(Base):
    """
    SQLAlchemy model for tracking search operations.
    
    Stores information about web searches performed by the agent,
    useful for debugging and analyzing agent behavior.
    """
    
    __tablename__ = "search_history"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Search details
    query = Column(String(512), nullable=False)
    company_name = Column(String(255), nullable=True, index=True)
    search_provider = Column(String(50), nullable=True)  # 'tavily' or 'serper'
    
    # Results
    num_results = Column(Integer, nullable=True)
    results_summary = Column(Text, nullable=True)
    raw_results = Column(JSON, nullable=True)  # Full structured search results
    
    # Execution metadata
    execution_time_ms = Column(Float, nullable=True)
    success = Column(Integer, default=1, nullable=False)  # 1 = success, 0 = failure
    error_message = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<SearchHistory(id={self.id}, query='{self.query}')>"


class ResearchQuery(Base):
    """
    SQLAlchemy model for structured research queries.
    
    Tracks individual search queries that need to be executed for each company,
    enabling structured query generation and tracking.
    """
    
    __tablename__ = "research_queries"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Query details
    company_name = Column(String(255), nullable=False, index=True)
    query_text = Column(String(512), nullable=False)
    query_type = Column(String(100), nullable=True)  # e.g., "company_size", "revenue", "general"
    
    # Status tracking
    status = Column(String(50), default="pending", nullable=False)  # pending, completed, failed
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<ResearchQuery(id={self.id}, company='{self.company_name}', query='{self.query_text[:50]}...')>"


class ProcessingRun(Base):
    """
    SQLAlchemy model for LLM processing runs.
    
    Tracks each time search results are processed through an LLM,
    enabling model comparison and prompt versioning.
    """
    
    __tablename__ = "processing_runs"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Company and context
    company_name = Column(String(255), nullable=False, index=True)
    
    # Prompt information
    prompt_version = Column(String(100), nullable=True)  # Version hash or identifier
    prompt_template = Column(Text, nullable=True)  # The actual prompt used
    instructions_source = Column(String(255), nullable=True)  # Path to instruction file
    
    # LLM configuration
    llm_model = Column(String(100), nullable=True)  # e.g., "gpt-4", "claude-3-opus"
    llm_provider = Column(String(50), nullable=True)  # e.g., "openai", "anthropic", "local"
    temperature = Column(Float, nullable=True)
    
    # Input/Output
    search_result_ids = Column(JSON, nullable=True)  # Array of SearchHistory IDs used
    input_context = Column(JSON, nullable=True)  # Combined search results
    output = Column(JSON, nullable=True)  # Structured CompanyInfo
    raw_output = Column(Text, nullable=True)  # Unparsed LLM response
    
    # Execution metadata
    execution_time_seconds = Column(Float, nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<ProcessingRun(id={self.id}, company='{self.company_name}', model='{self.llm_model}')>"


class ValidationResult(Base):
    """
    SQLAlchemy model for validation scores and metrics.
    
    Tracks validation results for processing runs, enabling quality metrics
    and regression testing.
    """
    
    __tablename__ = "validation_results"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Link to processing run
    processing_run_id = Column(Integer, ForeignKey("processing_runs.id"), nullable=False, index=True)
    
    # Validation details
    validation_type = Column(String(100), nullable=False)  # e.g., "completeness", "accuracy", "consistency"
    score = Column(Float, nullable=True)  # Score between 0-1 or custom scale
    details = Column(JSON, nullable=True)  # Detailed validation results
    
    # Validation metadata
    validated_by = Column(String(100), nullable=True)  # e.g., "human", "automated", "rule-based"
    validator_config = Column(JSON, nullable=True)  # Configuration used for validation
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<ValidationResult(id={self.id}, run_id={self.processing_run_id}, type='{self.validation_type}')>"


class LLMCallLog(Base):
    """
    SQLAlchemy model for tracking individual LLM API calls.
    
    Stores detailed information about each LLM invocation including
    token usage, timing, prompts, and responses. This is separate from
    AgentExecution which tracks high-level agent runs.
    """
    
    __tablename__ = "llm_call_logs"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Model information
    model_type = Column(String(100), nullable=False, index=True)  # local, openai, anthropic, gemini
    model_name = Column(String(255), nullable=False)  # Actual model identifier

    # Call metadata
    call_type = Column(String(100), nullable=True)  # e.g., 'invoke', 'stream', 'batch'
    
    # Token usage
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    
    # Timing metrics
    generation_time_seconds = Column(Float, nullable=False)
    tokens_per_second = Column(Float, nullable=True)
    
    # Input/Output
    prompt = Column(Text, nullable=True)  # Full prompt (may be large)
    prompt_length = Column(Integer, nullable=True)  # Character length
    response = Column(Text, nullable=True)  # Full response (may be large)
    response_length = Column(Integer, nullable=True)  # Character length
    
    # Status
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Additional metadata
    extra_metadata = Column(JSON, nullable=True)  # Extra information (model config, etc.) - renamed from 'metadata' as it's reserved in SQLAlchemy
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f"<LLMCallLog(id={self.id}, model='{self.model_name}', tokens={self.total_tokens})>"


class ModelConfiguration(Base):
    """Persisted model configuration entries for local and remote providers."""

    __tablename__ = "model_configurations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    provider = Column(String(50), nullable=False)  # local, openai, anthropic, gemini, etc.
    model_key = Column(String(255), nullable=True, unique=True)
    model_path = Column(String(512), nullable=True)
    api_identifier = Column(String(255), nullable=True)  # Remote model identifier (e.g., gpt-4)
    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - repr for debugging only
        return f"<ModelConfiguration(id={self.id}, name='{self.name}', provider='{self.provider}')>"


class TestExecution(Base):
    """Stores results from automated tests like BitMovin research test."""

    __tablename__ = "test_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_name = Column(String(255), nullable=False, index=True)  # e.g., "bitmovin_research"
    test_company = Column(String(255), nullable=False)  # e.g., "BitMovin"
    model_configuration_id = Column(Integer, ForeignKey("model_configurations.id"), nullable=True, index=True)
    model_name = Column(String(255), nullable=False)  # Name of the model used
    model_provider = Column(String(50), nullable=False)  # local, openai, anthropic, gemini
    
    # Test execution metadata
    success = Column(Boolean, nullable=False)  # Whether test passed
    execution_time_seconds = Column(Float, nullable=True)
    iterations = Column(Integer, nullable=True)
    
    # Validation results
    required_fields_valid = Column(Boolean, nullable=False)
    required_fields_errors = Column(JSON, nullable=True)  # List of validation errors
    required_fields_warnings = Column(JSON, nullable=True)  # List of validation warnings
    
    optional_fields_count = Column(Integer, nullable=True)  # Number of optional fields found
    optional_fields_coverage = Column(Float, nullable=True)  # Percentage coverage (0-1)
    optional_fields_present = Column(JSON, nullable=True)  # List of optional field names found
    
    # Extracted company info (as JSON)
    extracted_company_info = Column(JSON, nullable=True)
    
    # Raw output and error info
    raw_output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self) -> str:
        return f"<TestExecution(id={self.id}, test='{self.test_name}', model='{self.model_name}', success={self.success})>"


class APICredential(Base):
    """Store API credentials for remote model providers."""

    __tablename__ = "api_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(50), nullable=False, unique=True, index=True)
    api_key = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - repr for debugging only
        return f"<APICredential(provider='{self.provider}')>"


class AppSetting(Base):
    """Key-value storage for global application preferences."""

    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - repr for debugging only
        return f"<AppSetting(key='{self.key}')>"


# ============================================================================
# Testing Framework Tables - Stages 1-3
# ============================================================================

class PromptVersion(Base):
    """
    Stores versioned prompts for research agent.
    
    Educational: This enables prompt versioning for A/B testing and tracking
    prompt engineering experiments. Each prompt can have multiple versions,
    allowing comparison of accuracy across different prompt iterations.
    """
    
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
    """
    Stores versioned grading prompts for LLM output validation.
    
    Educational: Similar to agent prompts, grading prompts also evolve over time.
    This table tracks different versions of grading prompts to ensure consistency
    in how we evaluate model outputs across different test runs.
    """
    
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
    """
    Represents a single test run with a specific prompt version.
    
    Educational: This links together all components of a test run - the prompt version,
    company being tested, and all outputs/validation results. Test runs can be grouped
    into test suites for multi-company testing.
    """
    
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


class LLMOutputValidation(Base):
    """
    Stores LLM outputs for validation testing.
    
    Educational: This table stores the actual outputs from each model being tested,
    including all CompanyInfo fields. It tracks token usage and costs for cost analysis,
    and includes ground truth validation fields for quality assurance.
    """
    
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


class LLMOutputValidationResult(Base):
    """
    Stores accuracy scores from Gemini Flash grading.
    
    Educational: This table stores the results of grading each model's output against
    the ground truth (Gemini Pro output). It includes field-level accuracy scores,
    aggregate metrics, and grading metadata. This enables systematic comparison
    of prompt versions and model performance.
    """
    
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


def get_database_url() -> str:
    """
    Get database connection URL from environment or default.
    
    Returns:
        SQLite database URL
    """
    db_path = os.getenv("DATABASE_PATH", "./data/research_agent.db")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    return f"sqlite:///{db_path}"


def create_database():
    """
    Create database tables if they don't exist.
    
    This function creates all tables defined in the schema
    using SQLAlchemy's declarative base.
    """
    engine = create_engine(get_database_url())
    Base.metadata.create_all(engine)
    print(f"Database created/verified at: {get_database_url()}")


def get_engine():
    """
    Get SQLAlchemy engine instance.
    
    Returns:
        SQLAlchemy Engine object
    """
    return create_engine(get_database_url())


def get_session():
    """
    Get SQLAlchemy session for database operations.
    
    Returns:
        SQLAlchemy Session object
    """
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

