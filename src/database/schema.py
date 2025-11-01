"""
Database schema for storing company research results.

This module defines the SQLAlchemy models and database schema for
storing company information, search history, and execution metadata.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, Float, ForeignKey, Boolean
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
    headquarters = Column(String(255), nullable=True)
    founded = Column(Integer, nullable=True)
    
    # Financial information
    revenue = Column(String(100), nullable=True)
    funding_stage = Column(String(100), nullable=True)
    
    # Products and market
    products = Column(JSON, nullable=True)  # List of products
    competitors = Column(JSON, nullable=True)  # List of competitors
    
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


class AgentExecution(Base):
    """
    SQLAlchemy model for tracking agent execution runs.
    
    Stores high-level information about agent runs including
    execution time, success status, and result summaries.
    """
    
    __tablename__ = "agent_executions"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Execution details
    company_name = Column(String(255), nullable=False, index=True)
    agent_type = Column(String(100), nullable=True)  # e.g., 'react_agent'
    model_type = Column(String(100), nullable=True)  # e.g., 'local', 'openai'
    
    # Execution results
    success = Column(Integer, default=1, nullable=False)  # 1 = success, 0 = failure
    execution_time_seconds = Column(Float, nullable=True)
    num_tool_calls = Column(Integer, nullable=True)
    
    # Agent output
    final_answer = Column(JSON, nullable=True)  # Structured company info
    intermediate_steps = Column(JSON, nullable=True)  # Agent reasoning steps
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<AgentExecution(id={self.id}, company='{self.company_name}')>"


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
    agent_execution_id = Column(Integer, ForeignKey('agent_executions.id'), nullable=True, index=True)
    
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

