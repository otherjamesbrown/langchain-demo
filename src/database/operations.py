"""
Database operations for company research data.

This module provides high-level functions for storing and retrieving
company information, search history, and agent execution records.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from src.database.schema import (
    Company,
    SearchHistory,
    AgentExecution,
    get_session,
    create_database
)
from src.tools.models import CompanyInfo


def init_database():
    """Initialize database by creating all tables."""
    create_database()


def save_company_info(company_info: CompanyInfo, session: Optional[Session] = None) -> Company:
    """
    Save company information to the database.
    
    Args:
        company_info: CompanyInfo Pydantic model with company data
        session: Optional existing database session
        
    Returns:
        Company database record
    """
    if session is None:
        session = get_session()
        should_close = True
    else:
        should_close = False
    
    try:
        # Check if company already exists
        existing = session.query(Company).filter_by(
            company_name=company_info.company_name
        ).first()
        
        if existing:
            # Update existing record
            for key, value in company_info.model_dump().items():
                if key in ["products", "competitors"]:
                    setattr(existing, key, value if value else [])
                else:
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            result = existing
        else:
            # Create new record
            company_dict = company_info.model_dump()
            # Handle list fields
            company_dict["products"] = company_dict.get("products", [])
            company_dict["competitors"] = company_dict.get("competitors", [])
            
            new_company = Company(**company_dict)
            session.add(new_company)
            result = new_company
        
        session.commit()
        return result
        
    except Exception as e:
        session.rollback()
        raise Exception(f"Failed to save company info: {str(e)}")
    finally:
        if should_close:
            session.close()


def get_company(name: str, session: Optional[Session] = None) -> Optional[Company]:
    """
    Retrieve company information from database.
    
    Args:
        name: Company name
        session: Optional existing database session
        
    Returns:
        Company record if found, None otherwise
    """
    if session is None:
        session = get_session()
        should_close = True
    else:
        should_close = False
    
    try:
        return session.query(Company).filter_by(company_name=name).first()
    finally:
        if should_close:
            session.close()


def list_companies(session: Optional[Session] = None) -> List[Company]:
    """
    List all companies in the database.
    
    Args:
        session: Optional existing database session
        
    Returns:
        List of Company records
    """
    if session is None:
        session = get_session()
        should_close = True
    else:
        should_close = False
    
    try:
        return session.query(Company).order_by(Company.company_name).all()
    finally:
        if should_close:
            session.close()


def save_search_history(
    query: str,
    company_name: Optional[str] = None,
    search_provider: Optional[str] = None,
    num_results: Optional[int] = None,
    execution_time_ms: Optional[float] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    session: Optional[Session] = None
) -> SearchHistory:
    """
    Save search operation to history.
    
    Args:
        query: Search query string
        company_name: Related company name if applicable
        search_provider: Search provider used ('tavily' or 'serper')
        num_results: Number of results returned
        execution_time_ms: Execution time in milliseconds
        success: Whether search was successful
        error_message: Error message if failed
        session: Optional existing database session
        
    Returns:
        SearchHistory database record
    """
    if session is None:
        session = get_session()
        should_close = True
    else:
        should_close = False
    
    try:
        search_record = SearchHistory(
            query=query,
            company_name=company_name,
            search_provider=search_provider,
            num_results=num_results,
            execution_time_ms=execution_time_ms,
            success=1 if success else 0,
            error_message=error_message
        )
        session.add(search_record)
        session.commit()
        return search_record
    except Exception as e:
        session.rollback()
        raise Exception(f"Failed to save search history: {str(e)}")
    finally:
        if should_close:
            session.close()


def save_agent_execution(
    company_name: str,
    agent_type: str,
    model_type: str,
    success: bool,
    execution_time_seconds: Optional[float] = None,
    num_tool_calls: Optional[int] = None,
    final_answer: Optional[dict] = None,
    intermediate_steps: Optional[List[dict]] = None,
    error_message: Optional[str] = None,
    session: Optional[Session] = None
) -> AgentExecution:
    """
    Save agent execution record to database.
    
    Args:
        company_name: Company being researched
        agent_type: Type of agent used (e.g., 'react_agent')
        model_type: Model type used (e.g., 'local', 'openai')
        success: Whether execution was successful
        execution_time_seconds: Total execution time
        num_tool_calls: Number of tool calls made
        final_answer: Final structured output from agent
        intermediate_steps: Agent reasoning steps
        error_message: Error message if failed
        session: Optional existing database session
        
    Returns:
        AgentExecution database record
    """
    if session is None:
        session = get_session()
        should_close = True
    else:
        should_close = False
    
    try:
        execution_record = AgentExecution(
            company_name=company_name,
            agent_type=agent_type,
            model_type=model_type,
            success=1 if success else 0,
            execution_time_seconds=execution_time_seconds,
            num_tool_calls=num_tool_calls,
            final_answer=final_answer,
            intermediate_steps=intermediate_steps,
            error_message=error_message
        )
        session.add(execution_record)
        session.commit()
        return execution_record
    except Exception as e:
        session.rollback()
        raise Exception(f"Failed to save agent execution: {str(e)}")
    finally:
        if should_close:
            session.close()


def get_recent_executions(
    limit: int = 10,
    session: Optional[Session] = None
) -> List[AgentExecution]:
    """
    Get recent agent executions.
    
    Args:
        limit: Maximum number of records to return
        session: Optional existing database session
        
    Returns:
        List of recent AgentExecution records
    """
    if session is None:
        session = get_session()
        should_close = True
    else:
        should_close = False
    
    try:
        return session.query(AgentExecution).order_by(
            AgentExecution.created_at.desc()
        ).limit(limit).all()
    finally:
        if should_close:
            session.close()

