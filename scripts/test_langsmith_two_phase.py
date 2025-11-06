#!/usr/bin/env python3
"""
Test script for LangSmith two-phase integration.

This script demonstrates LangSmith tracing integration in Phase 1 (Search Collection)
and Phase 2 (LLM Processing) workflows:

1. Phase 1: Query generation and search execution tracing
2. Phase 2: Prompt building and LLM processing tracing
3. Full pipeline: End-to-end trace linking

Run this script to verify LangSmith tracing is working correctly in both phases.

Requirements:
- LANGCHAIN_API_KEY must be set in .env file
- LangSmith account at https://smith.langchain.com
- Database initialized (run from project root)
- Example files: examples/companies/sample_companies.csv, examples/instructions/research_instructions.md

Usage:
    python scripts/test_langsmith_two_phase.py
"""

import os
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.utils.monitoring import (
    configure_langsmith_tracing,
    langsmith_phase_trace
)
from src.database.schema import init_database
from src.research.query_generator import generate_queries, generate_queries_for_companies
from src.research.search_executor import execute_search, execute_all_pending_queries
from src.research.prompt_builder import build_prompt_from_files
from src.research.llm_processor import process_with_llm
from src.research.workflows import phase1_collect_searches, phase2_process_with_llm
from src.tools.data_loaders import load_csv_data


def test_configuration():
    """Test 1: Verify LangSmith configuration."""
    print("\n" + "="*70)
    print("TEST 1: LangSmith Configuration")
    print("="*70)
    
    # Check if API key is set
    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        print("❌ LANGCHAIN_API_KEY not set in environment")
        print("   Please add it to your .env file:")
        print("   LANGCHAIN_API_KEY=ls__your_api_key_here")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    # Configure tracing
    success = configure_langsmith_tracing(
        project_name="langsmith-test-two-phase",
        tags=["test", "two-phase"],
        metadata={"test_type": "two-phase-integration", "version": "2.0"},
        verbose=True
    )
    
    if success:
        print("✅ LangSmith configuration successful")
    else:
        print("❌ LangSmith configuration failed")
    
    return success


def test_phase1_query_generation():
    """Test 2: Phase 1 - Query generation tracing."""
    print("\n" + "="*70)
    print("TEST 2: Phase 1 - Query Generation Tracing")
    print("="*70)
    
    try:
        # Initialize database
        init_database()
        
        # Generate queries for a test company
        test_company = "TestCompany"
        print(f"Generating queries for: {test_company}")
        
        queries = generate_queries(test_company)
        
        print(f"✅ Generated {len(queries)} queries")
        print(f"   Query types: {[q.query_type for q in queries]}")
        print("✅ Query generation traced with phase:search-collection")
        
        return True
    except Exception as e:
        print(f"❌ Query generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_phase1_search_execution():
    """Test 3: Phase 1 - Search execution tracing."""
    print("\n" + "="*70)
    print("TEST 3: Phase 1 - Search Execution Tracing")
    print("="*70)
    
    try:
        from src.database.schema import ResearchQuery
        from src.utils.database import get_db_session
        
        # Get a pending query
        with get_db_session() as session:
            pending_query = session.query(ResearchQuery).filter_by(status="pending").first()
            
            if not pending_query:
                print("⚠️  No pending queries found. Creating one...")
                queries = generate_queries("TestCompany")
                pending_query = queries[0] if queries else None
            
            if not pending_query:
                print("❌ Could not create or find a query to test")
                return False
            
            print(f"Executing search for query: {pending_query.query_text[:60]}...")
            
            # Execute search (this will be traced)
            search_history = execute_search(pending_query)
            
            print(f"✅ Search executed successfully")
            print(f"   Provider: {search_history.search_provider}")
            print(f"   Results: {search_history.num_results}")
            print(f"   Execution time: {search_history.execution_time_ms:.2f}ms")
            print("✅ Search execution traced with phase:search-collection")
            
            return True
    except Exception as e:
        print(f"❌ Search execution test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_phase2_prompt_building():
    """Test 4: Phase 2 - Prompt building tracing."""
    print("\n" + "="*70)
    print("TEST 4: Phase 2 - Prompt Building Tracing")
    print("="*70)
    
    try:
        from src.research.search_executor import get_search_results_for_company
        from src.database.schema import SearchHistory
        from src.utils.database import get_db_session
        
        # Get search results for a company
        with get_db_session() as session:
            # Find a company with search results
            search_result = session.query(SearchHistory).filter_by(success=1).first()
            
            if not search_result:
                print("⚠️  No search results found. Run Phase 1 tests first.")
                return True  # Skip, not a failure
            
            company_name = search_result.company_name
            print(f"Building prompt for: {company_name}")
            
            search_results = get_search_results_for_company(company_name)
            
            if not search_results:
                print("⚠️  No search results found for company")
                return True  # Skip
            
            # Build prompt (this will be traced)
            instructions_path = "examples/instructions/research_instructions.md"
            if not Path(instructions_path).exists():
                print(f"⚠️  Instructions file not found: {instructions_path}")
                return True  # Skip
            
            prompt, prompt_version = build_prompt_from_files(
                instructions_path=instructions_path,
                company_name=company_name,
                search_results=search_results
            )
            
            print(f"✅ Prompt built successfully")
            print(f"   Prompt version: {prompt_version}")
            print(f"   Prompt length: {len(prompt)} characters")
            print("✅ Prompt building traced with phase:llm-processing")
            
            return True
    except Exception as e:
        print(f"❌ Prompt building test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_phase2_llm_processing():
    """Test 5: Phase 2 - LLM processing tracing."""
    print("\n" + "="*70)
    print("TEST 5: Phase 2 - LLM Processing Tracing")
    print("="*70)
    
    try:
        from src.research.search_executor import get_search_results_for_company
        from src.database.schema import SearchHistory
        from src.utils.database import get_db_session
        
        # Get search results
        with get_db_session() as session:
            search_result = session.query(SearchHistory).filter_by(success=1).first()
            
            if not search_result:
                print("⚠️  No search results found. Run Phase 1 tests first.")
                return True  # Skip
            
            company_name = search_result.company_name
            search_results = get_search_results_for_company(company_name)
            
            if not search_results:
                print("⚠️  No search results found for company")
                return True  # Skip
            
            # Build prompt
            instructions_path = "examples/instructions/research_instructions.md"
            if not Path(instructions_path).exists():
                print(f"⚠️  Instructions file not found: {instructions_path}")
                return True  # Skip
            
            prompt, prompt_version = build_prompt_from_files(
                instructions_path=instructions_path,
                company_name=company_name,
                search_results=search_results
            )
            
            # Process with LLM (use local model to avoid API costs)
            print(f"Processing {company_name} with local LLM...")
            print("   (This may take a while with local models)")
            
            search_result_ids = [r.id for r in search_results]
            
            processing_run = process_with_llm(
                prompt=prompt,
                company_name=company_name,
                search_result_ids=search_result_ids,
                llm_model="llama-2-7b",
                llm_provider="local",
                prompt_version=prompt_version,
                instructions_source=instructions_path,
                temperature=0.7
            )
            
            print(f"✅ LLM processing completed")
            print(f"   Processing run ID: {processing_run.id}")
            print(f"   Execution time: {processing_run.execution_time_seconds:.2f}s")
            print(f"   Success: {processing_run.success}")
            print("✅ LLM processing traced with phase:llm-processing")
            
            return True
    except Exception as e:
        print(f"❌ LLM processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_workflow_phase1():
    """Test 6: Phase 1 workflow tracing."""
    print("\n" + "="*70)
    print("TEST 6: Phase 1 Workflow Tracing")
    print("="*70)
    
    try:
        csv_path = "examples/companies/sample_companies.csv"
        if not Path(csv_path).exists():
            print(f"⚠️  CSV file not found: {csv_path}")
            return True  # Skip
        
        print(f"Running Phase 1 workflow with: {csv_path}")
        
        # Run Phase 1 workflow (this will be traced)
        summary = phase1_collect_searches(csv_path, provider=None)
        
        print(f"✅ Phase 1 workflow completed")
        print(f"   Companies: {summary['companies']}")
        print(f"   Queries generated: {summary['queries_generated']}")
        print(f"   Search results: {summary['search_results']}")
        print("✅ Phase 1 workflow traced with phase:search-collection")
        
        return True
    except Exception as e:
        print(f"❌ Phase 1 workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_workflow_phase2():
    """Test 7: Phase 2 workflow tracing."""
    print("\n" + "="*70)
    print("TEST 7: Phase 2 Workflow Tracing")
    print("="*70)
    
    try:
        from src.database.schema import SearchHistory
        from src.utils.database import get_db_session
        
        # Find a company with search results
        with get_db_session() as session:
            search_result = session.query(SearchHistory).filter_by(success=1).first()
            
            if not search_result:
                print("⚠️  No search results found. Run Phase 1 workflow first.")
                return True  # Skip
            
            company_name = search_result.company_name
            instructions_path = "examples/instructions/research_instructions.md"
            
            if not Path(instructions_path).exists():
                print(f"⚠️  Instructions file not found: {instructions_path}")
                return True  # Skip
            
            print(f"Running Phase 2 workflow for: {company_name}")
            
            # Run Phase 2 workflow (this will be traced)
            processing_run = phase2_process_with_llm(
                company_name=company_name,
                instructions_path=instructions_path,
                llm_provider="local",
                llm_model="llama-2-7b",
                temperature=0.7
            )
            
            print(f"✅ Phase 2 workflow completed")
            print(f"   Processing run ID: {processing_run.id}")
            print(f"   Execution time: {processing_run.execution_time_seconds:.2f}s")
            print("✅ Phase 2 workflow traced with phase:llm-processing")
            
            return True
    except Exception as e:
        print(f"❌ Phase 2 workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("LangSmith Two-Phase Integration Test Suite")
    print("="*70)
    print("\nThis script tests LangSmith tracing in both Phase 1 and Phase 2")
    print("of the research workflow. Check your LangSmith dashboard to see traces.")
    
    results = []
    
    # Run tests
    results.append(("Configuration", test_configuration()))
    results.append(("Phase 1 - Query Generation", test_phase1_query_generation()))
    results.append(("Phase 1 - Search Execution", test_phase1_search_execution()))
    results.append(("Phase 2 - Prompt Building", test_phase2_prompt_building()))
    results.append(("Phase 2 - LLM Processing", test_phase2_llm_processing()))
    results.append(("Phase 1 Workflow", test_workflow_phase1()))
    results.append(("Phase 2 Workflow", test_workflow_phase2()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Check your LangSmith dashboard for traces.")
        print("   Look for traces tagged with:")
        print("   - phase:search-collection (Phase 1)")
        print("   - phase:llm-processing (Phase 2)")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed or were skipped")
        return 1


if __name__ == "__main__":
    sys.exit(main())

