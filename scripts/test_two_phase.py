#!/usr/bin/env python3
"""
Test script for the two-phase research architecture.

This script demonstrates the improved architecture where search
collection (Phase 1) is separated from LLM processing (Phase 2).
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.schema import init_database
from src.research.workflows import (
    phase1_collect_searches,
    phase2_process_with_llm,
    phase2_process_multiple_models,
    full_research_pipeline
)
from src.research.validation import (
    validate_processing_run,
    compare_processing_runs,
    get_validation_summary
)
from src.database.schema import ProcessingRun, get_session


def test_phase1():
    """Test Phase 1: Search collection."""
    print("\n" + "="*70)
    print("TESTING PHASE 1: SEARCH COLLECTION")
    print("="*70)
    
    csv_path = project_root / "examples" / "companies" / "sample_companies.csv"
    
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        return None
    
    summary = phase1_collect_searches(str(csv_path))
    
    print("\nPhase 1 Summary:")
    print(f"  Companies: {summary['companies']}")
    print(f"  Queries: {summary['queries_generated']}")
    print(f"  Results: {summary['search_results']}")
    
    return summary


def test_phase2_single():
    """Test Phase 2: Single model processing."""
    print("\n" + "="*70)
    print("TESTING PHASE 2: SINGLE MODEL PROCESSING")
    print("="*70)
    
    instructions_path = project_root / "examples" / "instructions" / "research_instructions.md"
    company_name = "BitMovin"  # Test with first company
    
    # Get model from env or use default
    llm_provider = os.getenv("MODEL_TYPE", "local")
    llm_model = os.getenv("MODEL_NAME", "llama-2-7b")
    
    if llm_provider == "local":
        # For local models, use a generic name
        llm_model = "local-llm"
    
    try:
        result = phase2_process_with_llm(
            company_name=company_name,
            instructions_path=str(instructions_path),
            llm_provider=llm_provider,
            llm_model=llm_model,
            temperature=0.7
        )
        
        print(f"\n✓ Processing complete!")
        print(f"  Run ID: {result.id}")
        print(f"  Success: {result.success}")
        print(f"  Execution time: {result.execution_time_seconds:.2f}s")
        
        # Validate the run
        print("\nRunning validations...")
        validations = validate_processing_run(result.id)
        for validation in validations:
            print(f"  {validation.validation_type}: {validation.score:.2f}")
        
        return result
    except Exception as e:
        print(f"Error: {e}")
        return None


def test_phase2_multiple():
    """Test Phase 2: Multiple model processing (if you have multiple API keys)."""
    print("\n" + "="*70)
    print("TESTING PHASE 2: MULTI-MODEL PROCESSING")
    print("="*70)
    
    instructions_path = project_root / "examples" / "instructions" / "research_instructions.md"
    company_name = "BitMovin"
    
    # Define models to test (only include ones you have API keys for)
    models = []
    
    if os.getenv("OPENAI_API_KEY"):
        models.append({"provider": "openai", "model": "gpt-4"})
    
    if os.getenv("ANTHROPIC_API_KEY"):
        models.append({"provider": "anthropic", "model": "claude-3-opus-20240229"})
    
    if os.getenv("GOOGLE_API_KEY"):
        models.append({"provider": "gemini", "model": "gemini-flash-latest"})
    
    # Always include local if available
    models.append({"provider": "local", "model": "local-llm"})
    
    if len(models) < 2:
        print("Need at least 2 models configured to test comparison")
        print(f"Found {len(models)} model(s)")
        return None
    
    try:
        results = phase2_process_multiple_models(
            company_name=company_name,
            instructions_path=str(instructions_path),
            models=models,
            temperature=0.7
        )
        
        print(f"\n✓ Processed with {len(results)} models")
        
        # Compare results
        comparison = compare_processing_runs(results)
        print("\nComparison:")
        print(f"  Consensus rate: {comparison.get('consensus_rate', 0):.2%}")
        if comparison.get('consensus'):
            print("  Consensus fields:", list(comparison['consensus'].keys()))
        
        return results
    except Exception as e:
        print(f"Error: {e}")
        return None


def main():
    """Main test function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test two-phase research architecture")
    parser.add_argument("--phase", choices=["1", "2", "both", "multi"], default="both",
                       help="Which phase to test")
    parser.add_argument("--company", help="Specific company to test (for Phase 2)")
    
    args = parser.parse_args()
    
    # Initialize database
    print("Initializing database...")
    init_database()
    
    if args.phase == "1" or args.phase == "both":
        test_phase1()
    
    if args.phase == "2" or args.phase == "both":
        if args.company:
            # Process specific company
            instructions_path = project_root / "examples" / "instructions" / "research_instructions.md"
            llm_provider = os.getenv("MODEL_TYPE", "local")
            llm_model = os.getenv("MODEL_NAME", "local-llm")
            
            phase2_process_with_llm(
                company_name=args.company,
                instructions_path=str(instructions_path),
                llm_provider=llm_provider,
                llm_model=llm_model
            )
        else:
            test_phase2_single()
    
    if args.phase == "multi":
        test_phase2_multiple()
    
    print("\n" + "="*70)
    print("TESTING COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()

