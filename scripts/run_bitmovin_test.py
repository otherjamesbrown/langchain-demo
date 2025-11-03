#!/usr/bin/env python3
"""
Run end-to-end LLM output validation test for BitMovin.

This script demonstrates the complete testing framework workflow:
1. Gets available models from database (using model_availability utilities)
2. Runs complete test workflow (ground truth + model execution + grading)
3. Displays results

Educational: This shows how to use the testing framework in practice.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.testing.llm_output_validation_runner import LLMOutputValidationRunner
from src.prompts.prompt_manager import PromptManager
from src.utils.model_availability import get_available_models
from src.database.schema import get_session, ModelConfiguration


def convert_model_dict_to_config(session, model_dict: dict) -> ModelConfiguration:
    """
    Convert model dict from get_available_models() to ModelConfiguration object.
    
    Educational: The runner expects ModelConfiguration ORM objects, but
    get_available_models() returns dicts. This function bridges the gap.
    """
    return session.query(ModelConfiguration).filter(
        ModelConfiguration.id == model_dict["config_id"]
    ).first()


def main():
    """Run end-to-end test for BitMovin."""
    print("=" * 70)
    print("LLM Output Validation Test - BitMovin")
    print("=" * 70)
    print("\nThis test will:")
    print("  1. Get Gemini Pro ground truth (with 24-hour caching)")
    print("  2. Run other available models")
    print("  3. Grade all outputs using Gemini Flash")
    print("  4. Calculate aggregate accuracy scores")
    print("=" * 70)
    
    # Get active prompt version
    session = get_session()
    try:
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
            test_run_description="BitMovin end-to-end test via script",
        )
        
        # Get available models
        print("\n📋 Checking available models...")
        available_models = get_available_models(session=session, include_reasons=False)
        
        if not available_models:
            print("\n❌ No available models found!")
            print("   Please configure models in the database.")
            return 1
        
        print(f"\n✅ Found {len(available_models)} available model(s):")
        for model in available_models:
            print(f"   - {model['name']} ({model['provider']})")
        
        # Convert to ModelConfiguration objects (excluding Gemini Pro)
        gemini_pro_model_name = runner.gemini_pro_model_name
        other_models = []
        
        for model_dict in available_models:
            # Skip Gemini Pro (it's ground truth)
            if (model_dict['provider'] == 'gemini' and 
                model_dict.get('api_identifier') == gemini_pro_model_name):
                print(f"\n⏭️  Skipping {model_dict['name']} (used as ground truth)")
                continue
            
            config = convert_model_dict_to_config(session, model_dict)
            if config:
                other_models.append(config)
        
        if not other_models:
            print("\n⚠️  No other models to test (only Gemini Pro available)")
            print("   The test will still generate ground truth, but won't test other models.")
        
        # Run the test
        print("\n" + "=" * 70)
        print("🚀 Running Test...")
        print("=" * 70)
        
        result = runner.run_test(
            company_name="BitMovin",
            other_models=other_models if other_models else None,  # None = use all active models
            force_refresh=False,  # Use cached ground truth if available
            max_iterations=10,
            test_suite_name="bitmovin-test-suite",
        )
        
        if not result.get("success"):
            print(f"\n❌ Test failed: {result.get('error', 'Unknown error')}")
            return 1
        
        # Display results
        print("\n" + "=" * 70)
        print("✅ Test Completed Successfully!")
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
        
        print("\n" + "=" * 70)
        print("✅ Test complete! Check database for detailed results.")
        print("=" * 70)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error running test: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())

