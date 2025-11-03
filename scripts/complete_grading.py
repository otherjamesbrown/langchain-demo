#!/usr/bin/env python3
"""
Complete grading for an existing test run.

This script can be used to finish grading if a test run was interrupted.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.testing.llm_output_validation_runner import LLMOutputValidationRunner
from src.database.schema import get_session, TestRun, LLMOutputValidation, LLMOutputValidationResult


def complete_grading(test_run_id: int):
    """Complete grading for a specific test run."""
    session = get_session()
    try:
        # Get test run
        test_run = session.query(TestRun).filter(TestRun.id == test_run_id).first()
        if not test_run:
            print(f"❌ Test run {test_run_id} not found")
            return 1
        
        print(f"📋 Test Run {test_run_id}: {test_run.company_name}")
        print(f"   Prompt: {test_run.prompt_name}@{test_run.prompt_version}")
        
        # Get all outputs
        all_outputs = session.query(LLMOutputValidation).filter(
            LLMOutputValidation.test_run_id == test_run_id
        ).all()
        
        # Find Gemini Pro output (ground truth)
        gemini_pro_output = None
        other_outputs = []
        
        for output in all_outputs:
            if output.model_name == "gemini-2.0-flash-exp" and output.model_provider == "gemini":
                gemini_pro_output = output
            else:
                other_outputs.append(output)
        
        if not gemini_pro_output:
            print("❌ No Gemini Pro ground truth found")
            return 1
        
        print(f"✅ Ground truth: {gemini_pro_output.model_name}")
        print(f"✅ Other outputs to grade: {len(other_outputs)}")
        
        # Check which ones already have grading results
        existing_results = session.query(LLMOutputValidationResult).filter(
            LLMOutputValidationResult.test_run_id == test_run_id
        ).all()
        
        graded_output_ids = {r.output_id for r in existing_results}
        outputs_to_grade = [o for o in other_outputs if o.id not in graded_output_ids]
        
        if not outputs_to_grade:
            print("✅ All outputs already graded!")
            return 0
        
        print(f"📝 Grading {len(outputs_to_grade)} output(s)...")
        
        # Initialize runner
        runner = LLMOutputValidationRunner(
            prompt_version_id=test_run.prompt_version_id,
        )
        
        # Grade each output
        grading_results = []
        for i, other_output in enumerate(outputs_to_grade, 1):
            print(f"\n[{i}/{len(outputs_to_grade)}] Grading {other_output.model_name}...")
            
            grading_result = runner._grade_output_with_flash(
                session=session,
                gemini_pro_output=gemini_pro_output,
                other_output=other_output,
                company_name=test_run.company_name,
                test_run_id=test_run_id,
            )
            
            if grading_result:
                grading_results.append(grading_result)
                print(f"   ✅ Graded: {grading_result.overall_accuracy:.1f}% overall accuracy")
            else:
                print(f"   ❌ Grading failed")
        
        session.commit()
        
        print(f"\n{'='*70}")
        print("✅ Grading Complete!")
        print(f"{'='*70}")
        print(f"\n📊 Results:")
        for r in grading_results:
            print(f"   - {r.model_name}: {r.overall_accuracy:.1f}% overall")
            if r.required_fields_accuracy:
                print(f"     Required fields: {r.required_fields_accuracy:.1f}%")
            if r.weighted_accuracy:
                print(f"     Weighted: {r.weighted_accuracy:.1f}%")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        session.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/complete_grading.py <test_run_id>")
        sys.exit(1)
    
    test_run_id = int(sys.argv[1])
    sys.exit(complete_grading(test_run_id))

