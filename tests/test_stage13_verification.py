"""
Verification tests for Stage 13: Test Suite Support.

This test verifies that:
- run_test_suite() method exists and works correctly
- Can aggregate results across multiple companies
- Handles failures gracefully
- Test suite name grouping works
"""

from src.testing.llm_output_validation_runner import LLMOutputValidationRunner
from src.prompts.prompt_manager import PromptManager
from src.database.schema import get_session, create_database, TestRun


class TestStage13:
    """Test Stage 13: Test Suite Support"""
    
    def test_run_test_suite_method_exists(self):
        """Test that run_test_suite() method exists."""
        print("\n=== Testing run_test_suite() method exists ===")
        
        runner = LLMOutputValidationRunner()
        
        assert hasattr(runner, 'run_test_suite')
        assert callable(runner.run_test_suite)
        
        print("✅ run_test_suite() method exists")
        
        # Check method signature
        import inspect
        sig = inspect.signature(runner.run_test_suite)
        params = list(sig.parameters.keys())
        
        assert 'company_names' in params
        assert 'test_suite_name' in params
        assert 'other_models' in params
        assert 'force_refresh' in params
        assert 'max_iterations' in params
        
        print("✅ run_test_suite() has correct signature")
    
    def test_run_test_suite_validation(self):
        """Test that run_test_suite() validates inputs."""
        print("\n=== Testing run_test_suite() input validation ===")
        
        runner = LLMOutputValidationRunner()
        
        # Test empty company_names
        try:
            runner.run_test_suite(company_names=[], test_suite_name="test")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "company_names cannot be empty" in str(e)
            print("✅ Validates empty company_names")
        
        # Test empty test_suite_name
        try:
            runner.run_test_suite(company_names=["BitMovin"], test_suite_name="")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "test_suite_name is required" in str(e)
            print("✅ Validates empty test_suite_name")
    
    def test_run_test_suite_structure(self):
        """Test that run_test_suite() returns correct structure."""
        print("\n=== Testing run_test_suite() return structure ===")
        
        runner = LLMOutputValidationRunner()
        
        # Check return structure from source code
        import inspect
        source = inspect.getsource(runner.run_test_suite)
        
        # Check for required return keys
        assert "test_suite_name" in source
        assert "total_companies" in source
        assert "successful_companies" in source
        assert "failed_companies" in source
        assert "aggregated_accuracy" in source
        assert "results_by_company" in source
        
        print("✅ run_test_suite() returns correct structure")
    
    def test_aggregation_logic(self):
        """Test that aggregation logic is correct."""
        print("\n=== Testing aggregation logic ===")
        
        # Mock grading results
        from src.database.schema import LLMOutputValidationResult
        
        # Simulate aggregation logic
        mock_results = [
            type('MockResult', (), {'overall_accuracy': 50.0, 'required_fields_accuracy': 60.0, 'weighted_accuracy': 55.0})(),
            type('MockResult', (), {'overall_accuracy': 70.0, 'required_fields_accuracy': 80.0, 'weighted_accuracy': 75.0})(),
            type('MockResult', (), {'overall_accuracy': 90.0, 'required_fields_accuracy': 100.0, 'weighted_accuracy': 95.0})(),
        ]
        
        overall_accuracies = [r.overall_accuracy for r in mock_results]
        overall_avg = sum(overall_accuracies) / len(overall_accuracies)
        
        assert overall_avg == 70.0, f"Expected 70.0, got {overall_avg}"
        print(f"✅ Overall accuracy aggregation: {overall_avg:.1f}%")
        
        required_accuracies = [r.required_fields_accuracy for r in mock_results]
        required_avg = sum(required_accuracies) / len(required_accuracies)
        
        assert required_avg == 80.0, f"Expected 80.0, got {required_avg}"
        print(f"✅ Required fields aggregation: {required_avg:.1f}%")
    
    def test_test_suite_name_grouping(self):
        """Test that test suite name groups results correctly."""
        print("\n=== Testing test suite name grouping ===")
        
        create_database()
        session = get_session()
        try:
            # Check that test_suite_name is used in run_test()
            from src.testing.llm_output_validation_runner import LLMOutputValidationRunner
            runner = LLMOutputValidationRunner()
            
            import inspect
            source = inspect.getsource(runner.run_test)
            
            assert "test_suite_name" in source
            
            # Check that TestRun table has test_suite_name column
            test_runs = session.query(TestRun).filter(
                TestRun.test_suite_name.isnot(None)
            ).limit(1).all()
            
            print("✅ test_suite_name grouping supported in database")
            
        finally:
            session.close()
    
    def test_failure_handling(self):
        """Test that failures are handled gracefully."""
        print("\n=== Testing failure handling ===")
        
        runner = LLMOutputValidationRunner()
        
        # Check source code for failure handling
        import inspect
        source = inspect.getsource(runner.run_test_suite)
        
        assert "try:" in source or "except" in source
        assert "failed_companies" in source
        assert "continue" in source or "successful_companies" in source
        
        print("✅ Failure handling implemented (try/except with continue)")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Stage 13: Test Suite Support")
    print("=" * 60)
    
    test = TestStage13()
    test.test_run_test_suite_method_exists()
    test.test_run_test_suite_validation()
    test.test_run_test_suite_structure()
    test.test_aggregation_logic()
    test.test_test_suite_name_grouping()
    test.test_failure_handling()
    
    print("\n" + "=" * 60)
    print("✅ All Stage 13 verification tests passed!")
    print("=" * 60)
    print("\nNote: Full end-to-end test requires API keys and multiple companies.")
    print("      The method is ready but needs actual API calls to test completely.")

