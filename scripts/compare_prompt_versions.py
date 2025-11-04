#!/usr/bin/env python3
"""
CLI script for comparing prompt versions and analyzing test results.

This script provides a command-line interface for comparing prompt versions,
showing accuracy differences, cost analysis, and other metrics.

Usage:
    # Compare versions for single company
    python scripts/compare_prompt_versions.py --prompt research-agent-prompt --company BitMovin
    
    # Compare versions across test suite
    python scripts/compare_prompt_versions.py --prompt research-agent-prompt --test-suite-name "test-suite-v1.0"
    
    # Show cost analysis
    python scripts/compare_prompt_versions.py --prompt research-agent-prompt --show-costs
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.testing.prompt_analytics import PromptAnalytics


def format_comparison(comparison: list, show_costs: bool = False) -> None:
    """Format and display prompt version comparison."""
    if not comparison:
        print("\n⚠️  No prompt versions found with test data.")
        return
    
    print("\n" + "=" * 80)
    print("Prompt Version Comparison")
    print("=" * 80)
    
    for version_data in comparison:
        print(f"\n📌 Version {version_data['prompt_version']}")
        print(f"   Test Runs: {version_data['test_runs_count']}")
        print(f"   Companies Tested: {', '.join(version_data['companies_tested'])}")
        
        if version_data.get('average_overall_accuracy') is not None:
            print(f"   📊 Overall Accuracy: {version_data['average_overall_accuracy']:.1f}%")
        if version_data.get('average_required_fields_accuracy') is not None:
            print(f"   ✅ Required Fields: {version_data['average_required_fields_accuracy']:.1f}%")
        if version_data.get('average_optional_fields_accuracy') is not None:
            print(f"   📋 Optional Fields: {version_data['average_optional_fields_accuracy']:.1f}%")
        if version_data.get('average_weighted_accuracy') is not None:
            print(f"   ⚖️  Weighted Accuracy: {version_data['average_weighted_accuracy']:.1f}%")
        
        print(f"   📅 First Test: {version_data['first_test_run']}")
        print(f"   📅 Latest Test: {version_data['latest_test_run']}")
    
    # Show best version
    if len(comparison) > 1:
        best = max(
            [v for v in comparison if v.get('average_overall_accuracy') is not None],
            key=lambda x: x.get('average_overall_accuracy', 0),
            default=None
        )
        if best:
            print(f"\n🏆 Best Version: {best['prompt_version']} "
                  f"({best.get('average_overall_accuracy', 0):.1f}% accuracy)")


def format_cost_analysis(cost_analysis: dict) -> None:
    """Format and display cost analysis."""
    print("\n" + "=" * 80)
    print("Cost Analysis")
    print("=" * 80)
    
    total = cost_analysis['total']
    print(f"\n💰 Total Cost: ${total['total_cost']:.6f}")
    print(f"   Agent Execution: ${total['agent_cost']:.6f}")
    print(f"   Grading: ${total['grading_cost']:.6f}")
    print(f"\n📊 Total Tokens: {total['total_tokens']:,}")
    print(f"   Agent Tokens: {total['agent_tokens']:,}")
    print(f"   Grading Tokens: {total['grading_tokens']:,}")
    print(f"\n📈 Operations:")
    print(f"   Model Outputs: {total['outputs_count']}")
    print(f"   Grading Operations: {total['grading_count']}")
    
    # By prompt version
    if cost_analysis['by_prompt_version']:
        print(f"\n📌 By Prompt Version:")
        for version, stats in sorted(cost_analysis['by_prompt_version'].items()):
            print(f"   {version}:")
            print(f"      Agent: ${stats['agent_cost']:.6f} ({stats['agent_tokens']:,} tokens)")
            print(f"      Grading: ${stats['grading_cost']:.6f} ({stats['grading_tokens']:,} tokens)")
            print(f"      Total: ${stats['agent_cost'] + stats['grading_cost']:.6f}")
    
    # By company
    if cost_analysis['by_company']:
        print(f"\n🏢 By Company:")
        for company, stats in sorted(cost_analysis['by_company'].items()):
            print(f"   {company}:")
            print(f"      Agent: ${stats['agent_cost']:.6f} ({stats['agent_tokens']:,} tokens)")
            print(f"      Grading: ${stats['grading_cost']:.6f} ({stats['grading_tokens']:,} tokens)")
            print(f"      Total: ${stats['agent_cost'] + stats['grading_cost']:.6f}")
    
    # By model
    if cost_analysis['by_model']:
        print(f"\n🤖 By Model:")
        for model, stats in sorted(cost_analysis['by_model'].items()):
            print(f"   {model}:")
            print(f"      Cost: ${stats['agent_cost']:.6f} ({stats['agent_tokens']:,} tokens)")
            print(f"      Outputs: {stats['outputs_count']}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Compare prompt versions and analyze test results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare versions for single company
  %(prog)s --prompt research-agent-prompt --company BitMovin
  
  # Compare versions across test suite
  %(prog)s --prompt research-agent-prompt --test-suite-name "test-suite-v1.0"
  
  # Show cost analysis
  %(prog)s --prompt research-agent-prompt --show-costs
  
  # Compare with cost analysis
  %(prog)s --prompt research-agent-prompt --company BitMovin --show-costs
        """
    )
    
    parser.add_argument(
        "--prompt",
        type=str,
        required=True,
        help="Prompt name (e.g., 'research-agent-prompt')"
    )
    parser.add_argument(
        "--company",
        type=str,
        help="Filter by company name"
    )
    parser.add_argument(
        "--test-suite-name",
        type=str,
        help="Filter by test suite name"
    )
    parser.add_argument(
        "--show-costs",
        action="store_true",
        help="Show cost analysis"
    )
    parser.add_argument(
        "--min-test-runs",
        type=int,
        default=1,
        help="Minimum test runs required for a version to be included (default: 1)"
    )
    
    args = parser.parse_args()
    
    try:
        # Compare prompt versions
        print("=" * 80)
        print("Comparing Prompt Versions")
        print("=" * 80)
        print(f"Prompt: {args.prompt}")
        if args.company:
            print(f"Company: {args.company}")
        if args.test_suite_name:
            print(f"Test Suite: {args.test_suite_name}")
        print("=" * 80)
        
        comparison = PromptAnalytics.compare_prompt_versions(
            prompt_name=args.prompt,
            company_name=args.company,
            min_test_runs=args.min_test_runs
        )
        
        format_comparison(comparison, show_costs=args.show_costs)
        
        # Show cost analysis if requested
        if args.show_costs:
            cost_analysis = PromptAnalytics.get_cost_analysis(
                prompt_name=args.prompt,
                company_name=args.company,
                test_suite_name=args.test_suite_name
            )
            format_cost_analysis(cost_analysis)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

