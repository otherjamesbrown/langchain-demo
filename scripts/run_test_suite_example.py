#!/usr/bin/env python3
"""
Example script demonstrating how to use run_test_suite().

This shows how to run tests across multiple companies and get aggregated results.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.testing.llm_output_validation_runner import LLMOutputValidationRunner
from src.prompts.prompt_manager import PromptManager
from src.database.schema import get_session


def main():
    """Run a test suite example."""
    print("=" * 70)
    print("Test Suite Example - Multi-Company Testing")
    print("=" * 70)
    print("\nThis demonstrates running tests across multiple companies")
    print("and getting aggregated accuracy metrics.")
    print("=" * 70)
    
    session = get_session()
    try:
        # Get active prompt version
        prompt_version = PromptManager.get_active_version("research-agent-prompt", session=session)
        
        if not prompt_version:
            print("\n❌ No active prompt version found!")
            print("   Please initialize prompts first:")
            print("   python scripts/initialize_prompts.py --agent-prompt <path>")
            return 1
        
        print(f"\n✅ Using prompt: {prompt_version.prompt_name}@{prompt_version.version}")
        
        # Initialize runner
        runner = LLMOutputValidationRunner(
            prompt_version_id=prompt_version.id,
            test_run_description="Test suite example via script",
        )
        
        # Example: Run test suite with 2 companies
        # Note: Using cached ground truth from previous runs
        company_names = ["BitMovin"]  # Start with one company for demo
        
        print(f"\n📋 Running test suite for: {', '.join(company_names)}")
        print(f"   (Using cached ground truth if available)")
        
        suite_result = runner.run_test_suite(
            company_names=company_names,
            test_suite_name="example-test-suite",
            force_refresh=False,  # Use cached ground truth
            max_iterations=10,
        )
        
        # Display results
        print("\n" + "=" * 70)
        print("✅ Test Suite Results")
        print("=" * 70)
        
        print(f"\nTest Suite: {suite_result['test_suite_name']}")
        print(f"Total Companies: {suite_result['total_companies']}")
        print(f"Successful: {suite_result['successful_companies']}/{suite_result['total_companies']}")
        
        if suite_result['failed_companies']:
            print(f"\n⚠️  Failed Companies:")
            for failed in suite_result['failed_companies']:
                print(f"   - {failed['company']}: {failed['error']}")
        
        if suite_result['aggregated_accuracy']:
            acc = suite_result['aggregated_accuracy']
            print(f"\n📈 Aggregated Accuracy (across all companies):")
            if acc.get('overall') is not None:
                print(f"   Overall: {acc['overall']:.1f}%")
            if acc.get('required_fields') is not None:
                print(f"   Required Fields: {acc['required_fields']:.1f}%")
            if acc.get('optional_fields') is not None:
                print(f"   Optional Fields: {acc['optional_fields']:.1f}%")
            if acc.get('weighted') is not None:
                print(f"   Weighted: {acc['weighted']:.1f}%")
            if acc.get('total_grading_cost') is not None:
                print(f"   Total Grading Cost: ${acc['total_grading_cost']:.6f}")
        
        print(f"\n📊 Per-Company Results:")
        for company, result in suite_result['results_by_company'].items():
            print(f"\n   {company}:")
            print(f"      Test Run ID: {result['test_run_id']}")
            print(f"      Models Tested: {result['other_outputs_count']}")
            print(f"      Outputs Graded: {result['grading_results_count']}")
            if result.get('aggregate_stats'):
                stats = result['aggregate_stats']
                if stats.get('average_overall_accuracy'):
                    print(f"      Average Accuracy: {stats['average_overall_accuracy']:.1f}%")
        
        print("\n" + "=" * 70)
        print("✅ Test suite complete!")
        print("=" * 70)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())

