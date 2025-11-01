"""
Database operations for company research data.

This module provides high-level functions for storing and retrieving
company information, search history, and agent execution records.
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.orm import Session
from src.database.schema import (
    Company,
    SearchHistory,
    get_session,
    create_database
)

if TYPE_CHECKING:
    from src.tools.models import CompanyInfo


def init_database():
    """Initialize database by creating all tables."""
    create_database()


def save_company_info(company_info: "CompanyInfo", session: Optional[Session] = None) -> Company:
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
                if key in ["products", "competitors", "key_personas"]:
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
            company_dict["key_personas"] = company_dict.get("key_personas", [])
            
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
    raw_results: Optional[List[dict]] = None,
    results_summary: Optional[str] = None,
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
        raw_results: Optional list of raw search result payloads
        results_summary: Optional human-readable summary of results
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
            error_message=error_message,
            raw_results=raw_results,
            results_summary=results_summary
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



