"""
Query generator for structured research queries.

This module generates search queries for companies based on templates,
enabling systematic and reproducible research.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from src.database.schema import ResearchQuery
from src.utils.database import get_db_session
from sqlalchemy.orm import Session


@dataclass
class QueryTemplate:
    """Template for generating search queries."""
    query_type: str
    template: str
    description: str


# Default query templates for company research
DEFAULT_QUERY_TEMPLATES = [
    QueryTemplate(
        query_type="general",
        template="{company} company information",
        description="General company overview"
    ),
    QueryTemplate(
        query_type="company_size",
        template="{company} number of employees company size",
        description="Company size and employee count"
    ),
    QueryTemplate(
        query_type="revenue",
        template="{company} revenue annual revenue funding",
        description="Revenue and financial information"
    ),
    QueryTemplate(
        query_type="founded",
        template="{company} founded year when was company founded",
        description="Company founding date"
    ),
    QueryTemplate(
        query_type="headquarters",
        template="{company} headquarters location office location",
        description="Company headquarters location"
    ),
    QueryTemplate(
        query_type="funding",
        template="{company} funding stage investors venture capital",
        description="Funding stage and investors"
    ),
]


def generate_queries(
    company_name: str,
    templates: Optional[List[QueryTemplate]] = None,
    session: Optional[Session] = None
) -> List[ResearchQuery]:
    """
    Generate research queries for a company based on templates.
    
    Args:
        company_name: Name of the company to research
        templates: List of QueryTemplate objects. If None, uses DEFAULT_QUERY_TEMPLATES
        session: Optional database session
        
    Returns:
        List of ResearchQuery objects (not yet committed to database)
    """
    if templates is None:
        templates = DEFAULT_QUERY_TEMPLATES
    
    with get_db_session(session) as db_session:
        try:
            queries = []
            for template in templates:
                query_text = template.template.format(company=company_name)
                
                query = ResearchQuery(
                    company_name=company_name,
                    query_text=query_text,
                    query_type=template.query_type,
                    status="pending"
                )
                queries.append(query)
                db_session.add(query)
            
            db_session.commit()
            return queries
        except Exception as e:
            db_session.rollback()
            raise Exception(f"Failed to generate queries: {str(e)}")


def generate_queries_for_companies(
    company_names: List[str],
    templates: Optional[List[QueryTemplate]] = None
) -> Dict[str, List[ResearchQuery]]:
    """
    Generate queries for multiple companies.
    
    Args:
        company_names: List of company names
        templates: Optional query templates
        
    Returns:
        Dictionary mapping company names to their ResearchQuery lists
    """
    with get_db_session() as session:
        results = {}
        for company_name in company_names:
            queries = generate_queries(company_name, templates, session)
            results[company_name] = queries
        return results


def get_pending_queries(
    company_name: Optional[str] = None,
    session: Optional[Session] = None
) -> List[ResearchQuery]:
    """
    Get all pending research queries.
    
    Args:
        company_name: Optional company name filter
        session: Optional database session
        
    Returns:
        List of pending ResearchQuery objects
    """
    with get_db_session(session) as db_session:
        query = db_session.query(ResearchQuery).filter_by(status="pending")
        if company_name:
            query = query.filter_by(company_name=company_name)
        return query.all()


def load_custom_templates(file_path: str) -> List[QueryTemplate]:
    """
    Load query templates from a JSON or YAML file.
    
    Expected format:
    [
        {
            "query_type": "company_size",
            "template": "{company} number of employees",
            "description": "Employee count"
        },
        ...
    ]
    
    Args:
        file_path: Path to template file
        
    Returns:
        List of QueryTemplate objects
    """
    import json
    from pathlib import Path
    
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Template file not found: {file_path}")
    
    with open(path, 'r') as f:
        if path.suffix == '.json':
            data = json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
    
    return [QueryTemplate(**item) for item in data]

