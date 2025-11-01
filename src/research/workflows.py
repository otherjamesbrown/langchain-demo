"""
Workflow scripts for Phase 1 and Phase 2.

This module provides high-level workflows that combine the individual
components into complete research pipelines.
"""

from typing import List, Optional
from pathlib import Path
from src.database.schema import init_database
from src.research.query_generator import generate_queries_for_companies
from src.research.search_executor import execute_all_pending_queries, get_search_results_for_company
from src.research.prompt_builder import build_prompt_from_files
from src.research.llm_processor import process_with_llm, process_company_with_multiple_models
from src.tools.data_loaders import load_csv_data


def phase1_collect_searches(
    csv_path: str,
    provider: Optional[str] = None,
    templates: Optional[list] = None
) -> dict:
    """
    Phase 1: Collect all searches for companies.
    
    This workflow:
    1. Loads companies from CSV
    2. Generates research queries for each company
    3. Executes all searches
    4. Stores raw results in database
    
    Args:
        csv_path: Path to CSV file with companies
        provider: Search provider ('tavily' or 'serper'). Auto-detects if None
        templates: Optional query templates. Uses defaults if None
        
    Returns:
        Dictionary with summary statistics
    """
    print("\n" + "="*70)
    print("PHASE 1: SEARCH COLLECTION")
    print("="*70)
    
    # Initialize database
    init_database()
    
    # Load companies
    print(f"\nLoading companies from: {csv_path}")
    csv_data = load_csv_data(csv_path)
    company_names = [row.get("company_name", "").strip() for row in csv_data if row.get("company_name")]
    print(f"Found {len(company_names)} companies: {', '.join(company_names)}")
    
    # Generate queries
    print(f"\nGenerating research queries...")
    queries_by_company = generate_queries_for_companies(company_names, templates)
    
    total_queries = sum(len(queries) for queries in queries_by_company.values())
    print(f"Generated {total_queries} queries across {len(company_names)} companies")
    
    # Execute searches
    print(f"\nExecuting searches...")
    search_results = execute_all_pending_queries(provider=provider)
    
    # Summary
    print("\n" + "="*70)
    print("PHASE 1 SUMMARY")
    print("="*70)
    print(f"Companies processed: {len(company_names)}")
    print(f"Queries generated: {total_queries}")
    print(f"Search results stored: {len(search_results)}")
    
    return {
        "companies": len(company_names),
        "queries_generated": total_queries,
        "search_results": len(search_results)
    }


def phase2_process_with_llm(
    company_name: str,
    instructions_path: str,
    llm_provider: str,
    llm_model: str,
    temperature: float = 0.7
) -> dict:
    """
    Phase 2: Process search results through LLM.
    
    This workflow:
    1. Loads search results for a company
    2. Builds prompt from instructions + search results
    3. Processes through LLM
    4. Stores processing run with full metadata
    
    Args:
        company_name: Company to process
        instructions_path: Path to instructions markdown file
        llm_provider: LLM provider ('openai', 'anthropic', 'local', 'gemini')
        llm_model: Model name (e.g., 'gpt-4', 'claude-3-opus')
        temperature: LLM temperature
        
    Returns:
        ProcessingRun record
    """
    print("\n" + "="*70)
    print("PHASE 2: LLM PROCESSING")
    print("="*70)
    print(f"\nProcessing: {company_name}")
    print(f"LLM: {llm_provider}/{llm_model}")
    
    # Get search results
    search_results = get_search_results_for_company(company_name)
    
    if not search_results:
        raise ValueError(f"No search results found for {company_name}. Run Phase 1 first.")
    
    print(f"Using {len(search_results)} search results")
    
    # Build prompt
    prompt, prompt_version = build_prompt_from_files(
        instructions_path=instructions_path,
        company_name=company_name,
        search_results=search_results
    )
    
    print(f"Prompt version: {prompt_version}")
    print(f"Prompt length: {len(prompt)} characters")
    
    # Extract search result IDs
    search_result_ids = [result.id for result in search_results]
    
    # Process with LLM
    processing_run = process_with_llm(
        prompt=prompt,
        company_name=company_name,
        search_result_ids=search_result_ids,
        llm_model=llm_model,
        llm_provider=llm_provider,
        prompt_version=prompt_version,
        instructions_source=instructions_path,
        temperature=temperature
    )
    
    print("\n" + "="*70)
    print("PHASE 2 COMPLETE")
    print("="*70)
    print(f"Processing run ID: {processing_run.id}")
    print(f"Execution time: {processing_run.execution_time_seconds:.2f}s")
    print(f"Success: {processing_run.success}")
    
    return processing_run


def phase2_process_multiple_models(
    company_name: str,
    instructions_path: str,
    models: List[dict],
    temperature: float = 0.7
) -> List:
    """
    Phase 2: Process same company with multiple LLM models for comparison.
    
    Args:
        company_name: Company to process
        instructions_path: Path to instructions file
        models: List of model configs, e.g., [
            {"provider": "openai", "model": "gpt-4"},
            {"provider": "anthropic", "model": "claude-3-opus"}
        ]
        temperature: Temperature for all models
        
    Returns:
        List of ProcessingRun records
    """
    print("\n" + "="*70)
    print("PHASE 2: MULTI-MODEL PROCESSING")
    print("="*70)
    print(f"\nProcessing: {company_name}")
    print(f"Models: {len(models)}")
    
    # Get search results
    search_results = get_search_results_for_company(company_name)
    
    if not search_results:
        raise ValueError(f"No search results found for {company_name}. Run Phase 1 first.")
    
    # Build prompt (same for all models)
    prompt, prompt_version = build_prompt_from_files(
        instructions_path=instructions_path,
        company_name=company_name,
        search_results=search_results
    )
    
    # Extract search result IDs
    search_result_ids = [result.id for result in search_results]
    
    # Add temperature to each model config
    for model_config in models:
        model_config.setdefault("temperature", temperature)
    
    # Process with all models
    results = process_company_with_multiple_models(
        company_name=company_name,
        prompt=prompt,
        search_result_ids=search_result_ids,
        models=models,
        prompt_version=prompt_version,
        instructions_source=instructions_path
    )
    
    print("\n" + "="*70)
    print("MULTI-MODEL PROCESSING COMPLETE")
    print("="*70)
    print(f"Successfully processed with {len(results)} models")
    
    return results


def full_research_pipeline(
    csv_path: str,
    instructions_path: str,
    llm_provider: str = "local",
    llm_model: str = "llama-2-7b",
    search_provider: Optional[str] = None,
    temperature: float = 0.7
) -> dict:
    """
    Complete research pipeline: Phase 1 + Phase 2.
    
    Args:
        csv_path: Path to companies CSV
        instructions_path: Path to instructions markdown
        llm_provider: LLM provider
        llm_model: LLM model name
        search_provider: Search provider (auto-detects if None)
        temperature: LLM temperature
        
    Returns:
        Summary dictionary
    """
    # Phase 1: Collect searches
    phase1_summary = phase1_collect_searches(csv_path, provider=search_provider)
    
    # Phase 2: Process each company
    csv_data = load_csv_data(csv_path)
    company_names = [row.get("company_name", "").strip() for row in csv_data if row.get("company_name")]
    
    processing_results = []
    for company_name in company_names:
        try:
            result = phase2_process_with_llm(
                company_name=company_name,
                instructions_path=instructions_path,
                llm_provider=llm_provider,
                llm_model=llm_model,
                temperature=temperature
            )
            processing_results.append(result)
        except Exception as e:
            print(f"Failed to process {company_name}: {e}")
            continue
    
    return {
        "phase1": phase1_summary,
        "phase2": {
            "companies_processed": len(processing_results),
            "companies_total": len(company_names),
            "processing_runs": [r.id for r in processing_results]
        }
    }

