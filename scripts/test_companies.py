#!/usr/bin/env python3
"""
Test script for researching multiple companies using the ResearchAgent.

This script demonstrates how to use the ResearchAgent to research
multiple companies in batch mode.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agent.research_agent import ResearchAgent
from src.database.operations import init_database
from src.utils.logging import setup_logging
from src.tools.data_loaders import load_csv_data


def test_companies_research(
    company_names: list[str] = None,
    model_type: str = None,
    verbose: bool = True,
    use_database: bool = True
):
    """
    Test researching companies using the ResearchAgent.
    
    Args:
        company_names: List of company names to research. If None, loads from CSV
        model_type: Model type to use ('local', 'openai', 'anthropic', 'gemini')
        verbose: Whether to show agent reasoning steps
        use_database: Whether to save results to database
    """
    # Set up logging
    logger = setup_logging()
    logger.info("Starting company research test")
    
    # Initialize database if using it
    if use_database:
        try:
            init_database()
            logger.info("Database initialized")
        except Exception as e:
            logger.warning(f"Database initialization failed: {e}")
    
    # Load companies from CSV if not provided
    if company_names is None:
        csv_path = project_root / "examples" / "companies" / "sample_companies.csv"
        if csv_path.exists():
            logger.info(f"Loading companies from {csv_path}")
            csv_data = load_csv_data(str(csv_path))
            company_names = [row.get("company_name", "").strip() for row in csv_data if row.get("company_name")]
            logger.info(f"Loaded {len(company_names)} companies from CSV")
        else:
            logger.error(f"CSV file not found: {csv_path}")
            return
    
    # Get model type from env if not provided
    if model_type is None:
        model_type = os.getenv("MODEL_TYPE", "local").lower()
    
    logger.info(f"Using model type: {model_type}")
    logger.info(f"Companies to research: {company_names}")
    
    # Create agent
    try:
        agent = ResearchAgent(
            model_type=model_type,
            temperature=0.7,
            max_iterations=10,
            verbose=verbose,
            use_database=use_database
        )
        logger.info("ResearchAgent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize ResearchAgent: {e}")
        return
    
    # Research companies
    print("\n" + "="*70)
    print("Company Research Test")
    print("="*70)
    print(f"\nResearching {len(company_names)} companies...")
    print(f"Model type: {model_type}")
    print(f"Companies: {', '.join(company_names)}\n")
    
    results = []
    for i, company_name in enumerate(company_names, 1):
        print(f"\n[{i}/{len(company_names)}] Researching: {company_name}")
        print("-" * 70)
        
        try:
            result = agent.research_company(company_name)
            results.append(result)
            
            # Display summary
            print(f"\n✅ Completed: {company_name}")
            print(f"   Execution time: {result.execution_time:.2f}s")
            print(f"   Industry: {result.final_answer.industry}")
            print(f"   Company Size: {result.final_answer.company_size}")
            print(f"   Headquarters: {result.final_answer.headquarters}")
            
            if result.final_answer.founded:
                print(f"   Founded: {result.final_answer.founded}")
            
        except Exception as e:
            logger.error(f"Failed to research {company_name}: {e}")
            print(f"\n❌ Failed: {company_name}")
            print(f"   Error: {str(e)}")
            continue
    
    # Summary
    print("\n" + "="*70)
    print("Research Summary")
    print("="*70)
    print(f"\nTotal companies: {len(company_names)}")
    print(f"Successfully researched: {len(results)}")
    print(f"Failed: {len(company_names) - len(results)}")
    
    if results:
        total_time = sum(r.execution_time for r in results if r.execution_time)
        avg_time = total_time / len(results) if results else 0
        print(f"\nTotal execution time: {total_time:.2f}s")
        print(f"Average time per company: {avg_time:.2f}s")
        
        print("\nDetailed Results:")
        print("-" * 70)
        for result in results:
            print(f"\n{result.company_name}:")
            print(result.final_answer.model_dump_json(indent=2))
    
    return results


def main():
    """Main entry point for the test script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test company research with ResearchAgent"
    )
    parser.add_argument(
        "--companies",
        nargs="+",
        help="List of company names to research (default: loads from CSV)"
    )
    parser.add_argument(
        "--model-type",
        choices=["local", "openai", "anthropic", "gemini"],
        default=None,
        help="Model type to use (default: from MODEL_TYPE env var or 'local')"
    )
    parser.add_argument(
        "--no-verbose",
        action="store_true",
        help="Disable verbose agent output"
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Don't save results to database"
    )
    
    args = parser.parse_args()
    
    # Run test
    test_companies_research(
        company_names=args.companies,
        model_type=args.model_type,
        verbose=not args.no_verbose,
        use_database=not args.no_db
    )


if __name__ == "__main__":
    main()

