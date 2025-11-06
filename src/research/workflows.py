"""
Workflow scripts for Phase 1 and Phase 2.

This module provides high-level workflows that combine the individual
components into complete research pipelines.

LangSmith Integration:
- Workflow functions use tracing context managers to link Phase 1 and Phase 2
- Full pipeline traces connect search collection to LLM processing
- Enables end-to-end trace visualization in LangSmith
"""

from typing import List, Optional
from pathlib import Path
from src.database.schema import init_database
from src.research.query_generator import generate_queries_for_companies
from src.research.search_executor import execute_all_pending_queries, get_search_results_for_company
from src.research.prompt_builder import build_prompt_from_files
from src.research.llm_processor import process_with_llm, process_company_with_multiple_models
from src.tools.data_loaders import load_csv_data
from src.utils.monitoring import langsmith_phase_trace, langsmith_trace


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
    
    This function is traced with LangSmith using phase:search-collection tags.
    
    Args:
        csv_path: Path to CSV file with companies
        provider: Search provider ('tavily' or 'serper'). Auto-detects if None
        templates: Optional query templates. Uses defaults if None
        
    Returns:
        Dictionary with summary statistics
    """
    # Trace entire Phase 1 workflow
    with langsmith_phase_trace(
        phase="search-collection",
        company_name="batch_workflow"
    ) as workflow_trace:
        workflow_trace["metadata"]["csv_path"] = csv_path
        workflow_trace["metadata"]["provider"] = provider or "auto"
        
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
        
        workflow_trace["metadata"]["num_companies"] = len(company_names)
        workflow_trace["metadata"]["companies"] = company_names
        
        # Generate queries
        print(f"\nGenerating research queries...")
        queries_by_company = generate_queries_for_companies(company_names, templates)
        
        total_queries = sum(len(queries) for queries in queries_by_company.values())
        print(f"Generated {total_queries} queries across {len(company_names)} companies")
        
        workflow_trace["metadata"]["total_queries"] = total_queries
        
        # Execute searches
        print(f"\nExecuting searches...")
        search_results = execute_all_pending_queries(provider=provider)
        
        workflow_trace["metadata"]["search_results_count"] = len(search_results)
        
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
    
    This function is traced with LangSmith using phase:llm-processing tags.
    Links to Phase 1 traces via company name and search result IDs.
    
    Args:
        company_name: Company to process
        instructions_path: Path to instructions markdown file
        llm_provider: LLM provider ('openai', 'anthropic', 'local', 'gemini')
        llm_model: Model name (e.g., 'gpt-4', 'claude-3-opus')
        temperature: LLM temperature
        
    Returns:
        ProcessingRun record
    """
    # Trace entire Phase 2 workflow
    with langsmith_phase_trace(
        phase="llm-processing",
        company_name=company_name,
        model_name=llm_model
    ) as workflow_trace:
        workflow_trace["metadata"]["instructions_path"] = instructions_path
        workflow_trace["metadata"]["llm_provider"] = llm_provider
        workflow_trace["metadata"]["llm_model"] = llm_model
        workflow_trace["metadata"]["temperature"] = temperature
        
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
        
        workflow_trace["metadata"]["num_search_results"] = len(search_results)
        workflow_trace["metadata"]["search_result_ids"] = [r.id for r in search_results]
        
        # Build prompt
        prompt, prompt_version = build_prompt_from_files(
            instructions_path=instructions_path,
            company_name=company_name,
            search_results=search_results
        )
        
        print(f"Prompt version: {prompt_version}")
        print(f"Prompt length: {len(prompt)} characters")
        
        workflow_trace["metadata"]["prompt_version"] = prompt_version
        workflow_trace["metadata"]["prompt_length"] = len(prompt)
        
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
        
        workflow_trace["metadata"]["processing_run_id"] = processing_run.id
        
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
    
    This function is traced with LangSmith to link Phase 1 and Phase 2 workflows.
    Creates a parent trace that encompasses both phases for end-to-end visibility.
    
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
    # Trace full pipeline to link Phase 1 and Phase 2
    with langsmith_trace(
        name="full_research_pipeline",
        tags=["pipeline:full", "phase:both"],
        metadata={
            "csv_path": csv_path,
            "instructions_path": instructions_path,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "search_provider": search_provider or "auto",
            "temperature": temperature
        },
        project_name="research-agent-pipeline"
    ) as pipeline_trace:
        # Phase 1: Collect searches
        phase1_summary = phase1_collect_searches(csv_path, provider=search_provider)
        
        pipeline_trace["metadata"]["phase1_companies"] = phase1_summary["companies"]
        pipeline_trace["metadata"]["phase1_queries"] = phase1_summary["queries_generated"]
        pipeline_trace["metadata"]["phase1_search_results"] = phase1_summary["search_results"]
        
        # Phase 2: Process each company
        csv_data = load_csv_data(csv_path)
        company_names = [row.get("company_name", "").strip() for row in csv_data if row.get("company_name")]
        
        processing_results = []
        successful = 0
        failed = 0
        
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
                successful += 1
            except Exception as e:
                print(f"Failed to process {company_name}: {e}")
                failed += 1
                continue
        
        pipeline_trace["metadata"]["phase2_companies_processed"] = successful
        pipeline_trace["metadata"]["phase2_companies_failed"] = failed
        pipeline_trace["metadata"]["phase2_companies_total"] = len(company_names)
        pipeline_trace["metadata"]["phase2_processing_run_ids"] = [r.id for r in processing_results]
        
        return {
            "phase1": phase1_summary,
            "phase2": {
                "companies_processed": len(processing_results),
                "companies_total": len(company_names),
                "processing_runs": [r.id for r in processing_results]
            }
        }

