"""
Search executor for Phase 1: Search collection.

This module executes research queries and stores raw results in the database,
enabling the two-phase architecture where search is separated from LLM processing.
"""

import time
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from src.database.schema import ResearchQuery, SearchHistory
from src.tools.web_search import get_search_api_provider, TavilySearchAPI
from src.tools.web_search import SerperSearchAPI
from src.tools.models import SearchResult
from src.utils.database import get_db_session
import os


def execute_search(
    research_query: ResearchQuery,
    provider: Optional[str] = None,
    session: Optional[Session] = None
) -> SearchHistory:
    """
    Execute a single research query and store results.
    
    Args:
        research_query: ResearchQuery object to execute
        provider: Search provider ('tavily' or 'serper'). If None, auto-detects
        session: Optional database session
        
    Returns:
        SearchHistory record with raw results
    """
    start_time = time.time()
    
    try:
        with get_db_session(session) as db_session:
            # Determine provider
            if provider is None:
                provider = get_search_api_provider()
            
            # Execute search
            if provider == "tavily":
                client = TavilySearchAPI()
                results = client.search(query=research_query.query_text, max_results=5)
            elif provider == "serper":
                client = SerperSearchAPI()
                results = client.search(query=research_query.query_text, num=10)
            else:
                raise ValueError(f"Unknown search provider: {provider}")
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Convert to dict for JSON storage
            raw_results = [{
                "title": r.title,
                "url": r.url,
                "content": r.content,
                "relevance_score": r.relevance_score
            } for r in results]
            
            # Format results summary
            results_summary = "\n---\n".join([
                f"Result {i+1}:\nTitle: {r.title}\nURL: {r.url}\nContent: {r.content[:200]}..."
                for i, r in enumerate(results)
            ])
            
            # Create search history record
            search_history = SearchHistory(
                query=research_query.query_text,
                company_name=research_query.company_name,
                search_provider=provider,
                num_results=len(results),
                results_summary=results_summary,
                raw_results=raw_results,  # Store full JSON results
                execution_time_ms=execution_time_ms,
                success=1
            )
            
            db_session.add(search_history)
            
            # Update research query status
            research_query.status = "completed"
            research_query.completed_at = datetime.utcnow()
            
            db_session.commit()
            
            return search_history
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Record failed search in a new session if original failed
        with get_db_session() as db_session:
            search_history = SearchHistory(
                query=research_query.query_text,
                company_name=research_query.company_name,
                search_provider=provider or "unknown",
                execution_time_ms=execution_time_ms,
                success=0,
                error_message=str(e)
            )
            
            db_session.add(search_history)
            
            # Update research query status
            research_query.status = "failed"
            
            db_session.commit()
        
        raise Exception(f"Search failed: {str(e)}")


def execute_all_pending_queries(
    company_name: Optional[str] = None,
    provider: Optional[str] = None,
    batch_size: int = 10
) -> List[SearchHistory]:
    """
    Execute all pending research queries.
    
    Args:
        company_name: Optional filter for specific company
        provider: Search provider to use
        batch_size: Number of queries to process before committing
        
    Returns:
        List of SearchHistory records
    """
    with get_db_session() as session:
        pending_queries = session.query(ResearchQuery).filter_by(status="pending").all()
        
        if company_name:
            pending_queries = [q for q in pending_queries if q.company_name == company_name]
        
        print(f"Found {len(pending_queries)} pending queries")
        
        results = []
        for i, query in enumerate(pending_queries, 1):
            try:
                print(f"[{i}/{len(pending_queries)}] Executing: {query.query_text[:60]}...")
                result = execute_search(query, provider, session)
                results.append(result)
                
                # Commit in batches
                if i % batch_size == 0:
                    session.commit()
                    print(f"  Committed batch of {batch_size} queries")
            except Exception as e:
                print(f"  Failed: {str(e)}")
                continue
        
        return results


def get_search_results_for_company(
    company_name: str,
    session: Optional[Session] = None
) -> List[SearchHistory]:
    """
    Get all search results for a company.
    
    Args:
        company_name: Company name
        session: Optional database session
        
    Returns:
        List of SearchHistory records with raw results
    """
    with get_db_session(session) as db_session:
        return db_session.query(SearchHistory).filter_by(
            company_name=company_name,
            success=1
        ).order_by(SearchHistory.created_at.desc()).all()

