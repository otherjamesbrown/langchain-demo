#!/usr/bin/env python3
"""
CLI script for running LLM output validation tests.

This script provides a command-line interface for running tests and test suites,
making it easy to run tests from the command line or in automation scripts.

Usage:
    # Run single company test
    python scripts/run_llm_output_validation.py --company "BitMovin"
    
    # Run test suite (multiple companies)
    python scripts/run_llm_output_validation.py --companies "BitMovin" "Stripe" --test-suite-name "benchmark"
    
    # Run with specific prompt version
    python scripts/run_llm_output_validation.py --company "BitMovin" --prompt-name research-agent-prompt --prompt-version 1.0
    
    # Force refresh ground truth
    python scripts/run_llm_output_validation.py --company "BitMovin" --force-refresh
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.testing.llm_output_validation_runner import LLMOutputValidationRunner
from src.prompts.prompt_manager import PromptManager
from src.utils.model_availability import get_available_models
from src.database.schema import get_session, ModelConfiguration


def convert_model_dict_to_config(session, model_dict: dict) -> Optional[ModelConfiguration]:
    """Convert model dict from get_available_models() to ModelConfiguration object."""
    return session.query(ModelConfiguration).filter(
        ModelConfiguration.id == model_dict["config_id"]
    ).first()


def format_results(result: dict, is_suite: bool = False) -> None:
    """Format and display test results."""
    if is_suite:
        print("\n" + "=" * 70)
        print("✅ Test Suite Results")
        print("=" * 70)
        
        print(f"\nTest Suite: {result['test_suite_name']}")
        print(f"Total Companies: {result['total_companies']}")
        print(f"Successful: {result['successful_companies']}/{result['total_companies']}")
        
        if result['failed_companies']:
            print(f"\n⚠️  Failed Companies:")
            for failed in result['failed_companies']:
                print(f"   - {failed['company']}: {failed['error']}")
        
        if result['aggregated_accuracy']:
            acc = result['aggregated_accuracy']
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
        for company, company_result in result['results_by_company'].items():
            print(f"\n   {company}:")
            print(f"      Test Run ID: {company_result['test_run_id']}")
            print(f"      Models Tested: {company_result['other_outputs_count']}")
            print(f"      Outputs Graded: {company_result['grading_results_count']}")
            if company_result.get('aggregate_stats'):
                stats = company_result['aggregate_stats']
                if stats.get('average_overall_accuracy'):
                    print(f"      Average Accuracy: {stats['average_overall_accuracy']:.1f}%")
    else:
        print("\n" + "=" * 70)
        print("✅ Test Results")
        print("=" * 70)
        
        print(f"\n📊 Test Results:")
        print(f"   Test Run ID: {result['test_run_id']}")
        print(f"   Company: {result['company_name']}")
        print(f"   Prompt Version: {result['prompt_version']}")
        print(f"   Ground Truth ID: {result['gemini_pro_output_id']}")
        print(f"   Ground Truth Status: {result['ground_truth_status']}")
        print(f"   Other Models Tested: {result['other_outputs_count']}")
        print(f"   Outputs Graded: {result['grading_results_count']}")
        
        if result.get('aggregate_stats'):
            stats = result['aggregate_stats']
            print(f"\n📈 Aggregate Statistics:")
            if stats.get('average_overall_accuracy') is not None:
                print(f"   Average Overall Accuracy: {stats['average_overall_accuracy']:.1f}%")
            if stats.get('average_required_fields_accuracy') is not None:
                print(f"   Average Required Fields Accuracy: {stats['average_required_fields_accuracy']:.1f}%")
            if stats.get('average_weighted_accuracy') is not None:
                print(f"   Average Weighted Accuracy: {stats['average_weighted_accuracy']:.1f}%")
            if stats.get('total_grading_cost') is not None:
                print(f"   Total Grading Cost: ${stats['total_grading_cost']:.6f}")
        
        print(f"\n💾 Results stored in database:")
        print(f"   - TestRun: ID {result['test_run_id']}")
        print(f"   - LLMOutputValidation: {result['other_outputs_count'] + 1} outputs")
        print(f"   - LLMOutputValidationResult: {result['grading_results_count']} grading results")


def run_single_test(
    company_name: str,
    prompt_name: Optional[str],
    prompt_version: Optional[str],
    prompt_version_id: Optional[int],
    test_run_description: Optional[str],
    test_suite_name: Optional[str],
    force_refresh: bool,
    max_iterations: int,
) -> dict:
    """Run a single company test."""
    session = get_session()
    try:
        # Resolve prompt version
        if prompt_version_id:
            prompt_version_obj = PromptManager.get_version_by_id(prompt_version_id)
        elif prompt_name:
            if prompt_version:
                prompt_version_obj = PromptManager.get_version(prompt_name, prompt_version)
            else:
                prompt_version_obj = PromptManager.get_active_version(prompt_name)
        else:
            prompt_version_obj = PromptManager.get_active_version("research-agent-prompt")
        
        if not prompt_version_obj:
            raise ValueError("No prompt version found. Please initialize prompts first.")
        
        # Initialize runner
        runner_kwargs = {
            "test_run_description": test_run_description,
        }
        if prompt_version_id:
            runner_kwargs["prompt_version_id"] = prompt_version_id
        elif prompt_name:
            runner_kwargs["prompt_name"] = prompt_name
            if prompt_version:
                runner_kwargs["prompt_version"] = prompt_version
        
        runner = LLMOutputValidationRunner(**runner_kwargs)
        
        # Get available models and convert to ModelConfiguration objects
        available_models = get_available_models(session=session, include_reasons=False)
        
        # Exclude Gemini Pro from other models
        gemini_pro_model_name = runner.gemini_pro_model_name
        other_models = []
        
        for model_dict in available_models:
            if (model_dict['provider'] == 'gemini' and 
                model_dict.get('api_identifier') == gemini_pro_model_name):
                continue
            
            config = convert_model_dict_to_config(session, model_dict)
            if config:
                other_models.append(config)
        
        # Run test
        result = runner.run_test(
            company_name=company_name,
            other_models=other_models if other_models else None,
            force_refresh=force_refresh,
            max_iterations=max_iterations,
            test_suite_name=test_suite_name,
        )
        
        return result
        
    finally:
        session.close()


def run_test_suite(
    company_names: List[str],
    test_suite_name: str,
    prompt_name: Optional[str],
    prompt_version: Optional[str],
    prompt_version_id: Optional[int],
    test_run_description: Optional[str],
    force_refresh: bool,
    max_iterations: int,
) -> dict:
    """Run a test suite (multiple companies)."""
    session = get_session()
    try:
        # Resolve prompt version
        if prompt_version_id:
            prompt_version_obj = PromptManager.get_version_by_id(prompt_version_id)
        elif prompt_name:
            if prompt_version:
                prompt_version_obj = PromptManager.get_version(prompt_name, prompt_version)
            else:
                prompt_version_obj = PromptManager.get_active_version(prompt_name)
        else:
            prompt_version_obj = PromptManager.get_active_version("research-agent-prompt")
        
        if not prompt_version_obj:
            raise ValueError("No prompt version found. Please initialize prompts first.")
        
        # Initialize runner
        runner_kwargs = {
            "test_run_description": test_run_description,
        }
        if prompt_version_id:
            runner_kwargs["prompt_version_id"] = prompt_version_id
        elif prompt_name:
            runner_kwargs["prompt_name"] = prompt_name
            if prompt_version:
                runner_kwargs["prompt_version"] = prompt_version
        
        runner = LLMOutputValidationRunner(**runner_kwargs)
        
        # Get available models and convert to ModelConfiguration objects
        available_models = get_available_models(session=session, include_reasons=False)
        
        # Exclude Gemini Pro from other models
        gemini_pro_model_name = runner.gemini_pro_model_name
        other_models = []
        
        for model_dict in available_models:
            if (model_dict['provider'] == 'gemini' and 
                model_dict.get('api_identifier') == gemini_pro_model_name):
                continue
            
            config = convert_model_dict_to_config(session, model_dict)
            if config:
                other_models.append(config)
        
        # Run test suite
        result = runner.run_test_suite(
            company_names=company_names,
            test_suite_name=test_suite_name,
            other_models=other_models if other_models else None,
            force_refresh=force_refresh,
            max_iterations=max_iterations,
        )
        
        return result
        
    finally:
        session.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run LLM output validation tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run single company test
  %(prog)s --company "BitMovin"
  
  # Run test suite (multiple companies)
  %(prog)s --companies "BitMovin" "Stripe" --test-suite-name "benchmark"
  
  # Run with specific prompt version
  %(prog)s --company "BitMovin" --prompt-name research-agent-prompt --prompt-version 1.0
  
  # Force refresh ground truth
  %(prog)s --company "BitMovin" --force-refresh
  
  # Run with custom max iterations
  %(prog)s --company "BitMovin" --max-iterations 5
        """
    )
    
    # Company selection (mutually exclusive)
    company_group = parser.add_mutually_exclusive_group(required=True)
    company_group.add_argument(
        "--company",
        type=str,
        help="Single company name to test"
    )
    company_group.add_argument(
        "--companies",
        nargs="+",
        help="Multiple company names for test suite"
    )
    
    # Prompt selection
    prompt_group = parser.add_argument_group("Prompt Selection")
    prompt_group.add_argument(
        "--prompt-name",
        type=str,
        help="Prompt name (e.g., 'research-agent-prompt')"
    )
    prompt_group.add_argument(
        "--prompt-version",
        type=str,
        help="Specific prompt version (requires --prompt-name)"
    )
    prompt_group.add_argument(
        "--prompt-version-id",
        type=int,
        help="Prompt version ID (alternative to --prompt-name/--prompt-version)"
    )
    
    # Test configuration
    config_group = parser.add_argument_group("Test Configuration")
    config_group.add_argument(
        "--test-suite-name",
        type=str,
        help="Test suite name (for grouping multiple test runs)"
    )
    config_group.add_argument(
        "--test-run-description",
        type=str,
        help="Description for this test run"
    )
    config_group.add_argument(
        "--force-refresh",
        action="store_true",
        help="Force refresh ground truth even if cached (<24hrs)"
    )
    config_group.add_argument(
        "--max-iterations",
        type=int,
        default=10,
        help="Maximum agent iterations (default: 10)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.prompt_version and not args.prompt_name:
        parser.error("--prompt-version requires --prompt-name")
    
    try:
        if args.companies:
            # Run test suite
            if not args.test_suite_name:
                parser.error("--test-suite-name is required when using --companies")
            
            print("=" * 70)
            print("Running Test Suite")
            print("=" * 70)
            print(f"Companies: {', '.join(args.companies)}")
            print(f"Test Suite Name: {args.test_suite_name}")
            print(f"Max Iterations: {args.max_iterations}")
            if args.force_refresh:
                print("⚠️  Force refresh enabled (will regenerate ground truth)")
            print("=" * 70)
            
            result = run_test_suite(
                company_names=args.companies,
                test_suite_name=args.test_suite_name,
                prompt_name=args.prompt_name,
                prompt_version=args.prompt_version,
                prompt_version_id=args.prompt_version_id,
                test_run_description=args.test_run_description,
                force_refresh=args.force_refresh,
                max_iterations=args.max_iterations,
            )
            
            format_results(result, is_suite=True)
            
            if result['successful_companies'] < result['total_companies']:
                return 1  # Some companies failed
            return 0
            
        else:
            # Run single test
            print("=" * 70)
            print("Running Single Company Test")
            print("=" * 70)
            print(f"Company: {args.company}")
            print(f"Max Iterations: {args.max_iterations}")
            if args.force_refresh:
                print("⚠️  Force refresh enabled (will regenerate ground truth)")
            print("=" * 70)
            
            result = run_single_test(
                company_name=args.company,
                prompt_name=args.prompt_name,
                prompt_version=args.prompt_version,
                prompt_version_id=args.prompt_version_id,
                test_run_description=args.test_run_description,
                test_suite_name=args.test_suite_name,
                force_refresh=args.force_refresh,
                max_iterations=args.max_iterations,
            )
            
            if not result.get("success"):
                print(f"\n❌ Test failed: {result.get('error', 'Unknown error')}")
                return 1
            
            format_results(result, is_suite=False)
            return 0
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

