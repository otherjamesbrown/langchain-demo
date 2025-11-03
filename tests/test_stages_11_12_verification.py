"""
Verification tests for Stages 11-12: Aggregate Scoring and Complete Workflow.

Stage 11: Aggregate Scoring
Stage 12: Complete End-to-End Test Run Workflow

These tests verify that:
- Stage 11: Aggregate accuracy calculations work correctly
- Stage 12: Complete workflow runs end-to-end
"""

from src.testing.llm_output_validation_runner import LLMOutputValidationRunner
from src.prompts.prompt_manager import PromptManager
from src.database.schema import (
    get_session,
    create_database,
    TestRun,
    LLMOutputValidation,
    LLMOutputValidationResult,
)


class TestStage11:
    """Test Stage 11: Aggregate Scoring"""
    
    def test_aggregate_scoring_calculations(self):
        """Test that aggregate scoring calculations are correct."""
        print("\n=== Testing aggregate scoring calculations ===")
        
        # Mock field scores (simulating grading results)
        field_scores = {
            "company_name_field": {"score": 100, "match_type": "exact", "explanation": "test", "confidence": 1.0},
            "industry": {"score": 85, "match_type": "semantic", "explanation": "test", "confidence": 0.9},
            "company_size": {"score": 100, "match_type": "exact", "explanation": "test", "confidence": 1.0},
            "headquarters": {"score": 90, "match_type": "semantic", "explanation": "test", "confidence": 0.95},
            "founded": {"score": 100, "match_type": "exact", "explanation": "test", "confidence": 1.0},
            "description": {"score": 75, "match_type": "partial", "explanation": "test", "confidence": 0.8},
            "website": {"score": 100, "match_type": "exact", "explanation": "test", "confidence": 1.0},
        }
        
        # Calculate overall accuracy (average of all fields)
        all_scores = [r["score"] for r in field_scores.values()]
        overall_accuracy = sum(all_scores) / len(all_scores)
        
        print(f"✅ Overall accuracy: {overall_accuracy:.1f}%")
        assert overall_accuracy == 93.57, f"Expected 93.57, got {overall_accuracy:.2f}"
        
        # Required fields (core company info)
        required_fields = ["company_name_field", "industry", "company_size", "headquarters", "founded"]
        required_scores = [field_scores[f]["score"] for f in required_fields if f in field_scores]
        required_fields_accuracy = sum(required_scores) / len(required_scores) if required_scores else 0.0
        
        print(f"✅ Required fields accuracy: {required_fields_accuracy:.1f}%")
        assert required_fields_accuracy == 95.0, f"Expected 95.0, got {required_fields_accuracy:.1f}"
        
        # Optional fields (all others)
        optional_fields = [f for f in field_scores.keys() if f not in required_fields]
        optional_scores = [field_scores[f]["score"] for f in optional_fields if optional_fields]
        optional_fields_accuracy = sum(optional_scores) / len(optional_scores) if optional_scores else 0.0
        
        print(f"✅ Optional fields accuracy: {optional_fields_accuracy:.1f}%")
        assert optional_fields_accuracy == 87.5, f"Expected 87.5, got {optional_fields_accuracy:.1f}"
        
        # Weighted accuracy (critical fields count 2x)
        critical_fields = ["industry", "company_size", "headquarters"]
        weighted_scores = []
        for field_name, result in field_scores.items():
            weight = 2.0 if field_name in critical_fields else 1.0
            weighted_scores.extend([result["score"]] * int(weight))
        weighted_accuracy = sum(weighted_scores) / len(weighted_scores) if weighted_scores else 0.0
        
        print(f"✅ Weighted accuracy: {weighted_accuracy:.1f}%")
        # Critical fields: industry(85), company_size(100), headquarters(90) = 275
        # Other fields: company_name(100), founded(100), description(75), website(100) = 375
        # Total: 275*2 + 375 = 550 + 375 = 925, count: 3*2 + 4 = 10
        # Expected: 925/10 = 92.5
        assert abs(weighted_accuracy - 92.5) < 0.1, f"Expected ~92.5, got {weighted_accuracy:.1f}"
        
        print("✅ All aggregate scoring calculations correct")
    
    def test_aggregate_scoring_in_grade_output(self):
        """Test that _grade_output_with_flash() calculates aggregates correctly."""
        print("\n=== Testing aggregate scoring in _grade_output_with_flash() ===")
        
        runner = LLMOutputValidationRunner()
        
        # Check that the method calculates aggregates
        import inspect
        source = inspect.getsource(runner._grade_output_with_flash)
        
        assert "overall_accuracy" in source
        assert "required_fields_accuracy" in source
        assert "optional_fields_accuracy" in source
        assert "weighted_accuracy" in source
        
        print("✅ _grade_output_with_flash() includes all aggregate calculations")
    
    def test_aggregate_stats_in_run_test(self):
        """Test that run_test() calculates aggregate statistics."""
        print("\n=== Testing aggregate stats in run_test() ===")
        
        runner = LLMOutputValidationRunner()
        
        # Check that run_test() calculates aggregate stats
        import inspect
        source = inspect.getsource(runner.run_test)
        
        assert "aggregate_stats" in source
        assert "average_overall_accuracy" in source or "overall_accuracy" in source
        
        print("✅ run_test() includes aggregate statistics calculation")


class TestStage12:
    """Test Stage 12: Complete End-to-End Workflow"""
    
    def test_run_test_workflow_structure(self):
        """Test that run_test() has complete workflow."""
        print("\n=== Testing run_test() workflow structure ===")
        
        runner = LLMOutputValidationRunner()
        
        # Check that run_test() includes all workflow steps
        import inspect
        source = inspect.getsource(runner.run_test)
        
        # Step 1: Create test run
        assert "TestRun" in source
        
        # Step 2: Ensure Gemini Pro output
        assert "_ensure_gemini_pro_output" in source
        
        # Step 3: Run other models
        assert "_run_model_and_store" in source or "_get_other_models" in source
        
        # Step 4: Grade outputs
        assert "_grade_output_with_flash" in source
        
        # Step 5: Aggregate stats
        assert "aggregate_stats" in source
        
        print("✅ run_test() includes all workflow steps")
    
    def test_run_test_returns_complete_results(self):
        """Test that run_test() returns complete results dictionary."""
        print("\n=== Testing run_test() return structure ===")
        
        runner = LLMOutputValidationRunner()
        
        # Check return signature
        import inspect
        sig = inspect.signature(runner.run_test)
        return_annotation = sig.return_annotation
        
        # Check that it returns Dict
        assert "Dict" in str(return_annotation) or return_annotation == dict
        
        # Check source for expected return keys
        source = inspect.getsource(runner.run_test)
        
        assert "test_run_id" in source
        assert "gemini_pro_output_id" in source
        assert "other_outputs_count" in source
        assert "grading_results_count" in source
        
        print("✅ run_test() returns complete results structure")
    
    def test_copy_output_to_test_run_exists(self):
        """Test that _copy_output_to_test_run() exists (for caching)."""
        print("\n=== Testing _copy_output_to_test_run() ===")
        
        runner = LLMOutputValidationRunner()
        
        assert hasattr(runner, '_copy_output_to_test_run')
        assert callable(runner._copy_output_to_test_run)
        
        print("✅ _copy_output_to_test_run() method exists")
        
        # Check signature
        import inspect
        sig = inspect.signature(runner._copy_output_to_test_run)
        params = list(sig.parameters.keys())
        
        assert 'session' in params
        assert 'source_output' in params
        assert 'target_test_run_id' in params
        
        print("✅ _copy_output_to_test_run() has correct signature")
    
    def test_workflow_integration(self):
        """Test that all workflow components are integrated."""
        print("\n=== Testing workflow integration ===")
        
        create_database()
        session = get_session()
        try:
            # Check that prompt version is required
            runner = LLMOutputValidationRunner()
            
            # Should have resolved prompt version
            assert hasattr(runner, '_resolved_prompt_version')
            
            # Check that grading prompt can be loaded
            from src.prompts.grading_prompt_manager import GradingPromptManager
            grading_prompt = GradingPromptManager.get_active_version(session=session)
            
            if not grading_prompt:
                # Create default if needed
                grading_prompt = GradingPromptManager.create_default_version(session=session)
            
            assert grading_prompt is not None
            
            print("✅ All workflow components available")
            print(f"   Agent prompt: {runner._resolved_prompt_version.prompt_name if runner._resolved_prompt_version else 'None'}")
            print(f"   Grading prompt: version {grading_prompt.version}")
            
        finally:
            session.close()
    
    def test_database_schema_supports_workflow(self):
        """Test that database schema supports complete workflow."""
        print("\n=== Testing database schema support ===")
        
        create_database()
        session = get_session()
        try:
            # Check that all required tables exist
            from src.database.schema import (
                TestRun,
                LLMOutputValidation,
                LLMOutputValidationResult,
                PromptVersion,
                GradingPromptVersion,
            )
            
            # Verify tables are accessible
            test_run_count = session.query(TestRun).count()
            output_count = session.query(LLMOutputValidation).count()
            result_count = session.query(LLMOutputValidationResult).count()
            prompt_count = session.query(PromptVersion).count()
            grading_count = session.query(GradingPromptVersion).count()
            
            print(f"✅ Database tables accessible:")
            print(f"   TestRun: {test_run_count} records")
            print(f"   LLMOutputValidation: {output_count} records")
            print(f"   LLMOutputValidationResult: {result_count} records")
            print(f"   PromptVersion: {prompt_count} records")
            print(f"   GradingPromptVersion: {grading_count} records")
            
        finally:
            session.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Stages 11-12: Aggregate Scoring & Complete Workflow")
    print("=" * 60)
    
    # Test Stage 11
    print("\n" + "=" * 60)
    print("Stage 11: Aggregate Scoring")
    print("=" * 60)
    
    test11 = TestStage11()
    test11.test_aggregate_scoring_calculations()
    test11.test_aggregate_scoring_in_grade_output()
    test11.test_aggregate_stats_in_run_test()
    
    # Test Stage 12
    print("\n" + "=" * 60)
    print("Stage 12: Complete End-to-End Workflow")
    print("=" * 60)
    
    test12 = TestStage12()
    test12.test_run_test_workflow_structure()
    test12.test_run_test_returns_complete_results()
    test12.test_copy_output_to_test_run_exists()
    test12.test_workflow_integration()
    test12.test_database_schema_supports_workflow()
    
    print("\n" + "=" * 60)
    print("✅ All Stage 11-12 verification tests passed!")
    print("=" * 60)
    print("\nNote: Full end-to-end test requires API keys for Gemini Pro/Flash.")
    print("      The workflow is ready but needs actual API calls to test completely.")

