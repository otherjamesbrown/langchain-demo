#!/usr/bin/env python3
"""
Review Latest LLM Output Validation Test Results

This script queries the database to show the latest test run results,
including accuracy scores, model outputs, and grading information.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.schema import get_session
from src.testing.prompt_analytics import PromptAnalytics
from sqlalchemy import desc
from src.database.schema import TestRun, LLMOutputValidation, LLMOutputValidationResult


def format_accuracy(score):
    """Format accuracy score with emoji indicator."""
    if score is None:
        return "N/A"
    if score >= 80:
        return f"✅ {score:.1f}%"
    elif score >= 50:
        return f"⚠️  {score:.1f}%"
    else:
        return f"❌ {score:.1f}%"


def main():
    """Main function to display latest test results."""
    session = get_session()
    
    try:
        print("=" * 80)
        print("Latest LLM Output Validation Test Results")
        print("=" * 80)
        print()
        
        # Get latest 5 test runs
        history = PromptAnalytics.get_test_run_history(limit=5)
        
        if not history:
            print("❌ No test results found in database.")
            return
        
        print(f"Found {len(history)} recent test run(s):\n")
        
        for i, test_run in enumerate(history, 1):
            print("=" * 80)
            print(f"Test Run #{i}: ID {test_run['test_run_id']}")
            print("=" * 80)
            print(f"Company: {test_run['company_name']}")
            print(f"Prompt: {test_run['prompt_name']}@{test_run['prompt_version']}")
            if test_run.get('test_suite_name'):
                print(f"Test Suite: {test_run['test_suite_name']}")
            if test_run.get('description'):
                print(f"Description: {test_run['description']}")
            print(f"Created: {test_run['created_at']}")
            print(f"Outputs: {test_run['outputs_count']}")
            print(f"Grading Results: {test_run['grading_results_count']}")
            
            if test_run.get('average_overall_accuracy') is not None:
                print()
                print("📊 Accuracy Scores:")
                print(f"  Overall: {format_accuracy(test_run['average_overall_accuracy'])}")
                if test_run.get('average_required_fields_accuracy') is not None:
                    print(f"  Required Fields: {format_accuracy(test_run['average_required_fields_accuracy'])}")
                if test_run.get('average_weighted_accuracy') is not None:
                    print(f"  Weighted: {format_accuracy(test_run['average_weighted_accuracy'])}")
            else:
                print()
                print("⚠️  No grading results available yet")
            
            # Get detailed model results for this test run
            test_run_id = test_run['test_run_id']
            results = session.query(LLMOutputValidationResult).filter(
                LLMOutputValidationResult.test_run_id == test_run_id
            ).order_by(desc(LLMOutputValidationResult.overall_accuracy)).all()
            
            if results:
                print()
                print("📋 Model Results:")
                for result in results:
                    print(f"  {result.model_name} ({result.model_provider}): "
                          f"{format_accuracy(result.overall_accuracy)}")
                    if result.required_fields_accuracy is not None:
                        print(f"    Required Fields: {format_accuracy(result.required_fields_accuracy)}")
                    if result.weighted_accuracy is not None:
                        print(f"    Weighted: {format_accuracy(result.weighted_accuracy)}")
            
            print()
        
        # Show summary statistics
        print("=" * 80)
        print("Summary Statistics")
        print("=" * 80)
        
        all_results = session.query(LLMOutputValidationResult).join(
            TestRun, LLMOutputValidationResult.test_run_id == TestRun.id
        ).order_by(desc(TestRun.created_at)).limit(50).all()
        
        if all_results:
            overall_scores = [r.overall_accuracy for r in all_results if r.overall_accuracy is not None]
            required_scores = [r.required_fields_accuracy for r in all_results if r.required_fields_accuracy is not None]
            weighted_scores = [r.weighted_accuracy for r in all_results if r.weighted_accuracy is not None]
            
            if overall_scores:
                avg_overall = sum(overall_scores) / len(overall_scores)
                print(f"Average Overall Accuracy (last 50 results): {format_accuracy(avg_overall)}")
            
            if required_scores:
                avg_required = sum(required_scores) / len(required_scores)
                print(f"Average Required Fields Accuracy: {format_accuracy(avg_required)}")
            
            if weighted_scores:
                avg_weighted = sum(weighted_scores) / len(weighted_scores)
                print(f"Average Weighted Accuracy: {format_accuracy(avg_weighted)}")
        
        print()
        
    finally:
        session.close()


if __name__ == "__main__":
    main()

