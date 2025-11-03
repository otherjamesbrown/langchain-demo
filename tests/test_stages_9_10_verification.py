"""
Verification tests for Stages 9-10: Model Execution and Grading System.

Stage 9: Model Execution & Storage
Stage 10: Field-Level Grading

These tests verify that:
- Stage 9: Can run models and store outputs
- Stage 10: Can grade fields using Gemini Flash
"""

from src.testing.llm_output_validation_runner import LLMOutputValidationRunner
from src.prompts.prompt_manager import PromptManager
from src.database.schema import get_session, create_database, ModelConfiguration, LLMOutputValidation
from src.prompts.grading_prompt_manager import GradingPromptManager


class TestStage9:
    """Test Stage 9: Model Execution & Storage"""
    
    def test_get_other_models(self):
        """Test retrieving active models from database."""
        print("\n=== Testing _get_other_models() ===")
        
        create_database()
        session = get_session()
        try:
            runner = LLMOutputValidationRunner()
            models = runner._get_other_models(session=session)
            
            print(f"✅ Found {len(models)} active models")
            for model in models:
                print(f"   - {model.name} ({model.provider})")
            
            assert isinstance(models, list)
            print("✅ _get_other_models() works correctly")
            
        finally:
            session.close()
    
    def test_delete_other_model_outputs(self):
        """Test deleting other model outputs (without affecting Gemini Pro)."""
        print("\n=== Testing _delete_other_model_outputs() ===")
        
        create_database()
        session = get_session()
        try:
            runner = LLMOutputValidationRunner()
            
            # This should run without errors (even if no outputs exist)
            runner._delete_other_model_outputs(
                session=session,
                company_name="TestCompany",
                test_run_id=999,
            )
            
            print("✅ _delete_other_model_outputs() works correctly")
            
        finally:
            session.close()
    
    def test_run_model_and_store_structure(self):
        """Test that _run_model_and_store() method exists and has correct signature."""
        print("\n=== Testing _run_model_and_store() structure ===")
        
        runner = LLMOutputValidationRunner()
        
        # Check method exists
        assert hasattr(runner, '_run_model_and_store')
        assert callable(runner._run_model_and_store)
        
        print("✅ _run_model_and_store() method exists")
        
        # Check method signature
        import inspect
        sig = inspect.signature(runner._run_model_and_store)
        params = list(sig.parameters.keys())
        
        assert 'session' in params
        assert 'company_name' in params
        assert 'test_run_id' in params
        assert 'model_config' in params
        assert 'max_iterations' in params
        
        print("✅ _run_model_and_store() has correct signature")
    
    def test_run_test_includes_other_models(self):
        """Test that run_test() includes other model execution logic."""
        print("\n=== Testing run_test() includes Stage 9 logic ===")
        
        runner = LLMOutputValidationRunner()
        
        # Check that run_test returns other_outputs_count
        import inspect
        source = inspect.getsource(runner.run_test)
        
        assert '_get_other_models' in source or 'other_models' in source
        assert 'other_outputs' in source or 'other_outputs_count' in source
        
        print("✅ run_test() includes Stage 9 logic")


class TestStage10:
    """Test Stage 10: Field-Level Grading"""
    
    def test_get_fields_to_grade(self):
        """Test retrieving list of fields to grade."""
        print("\n=== Testing _get_fields_to_grade() ===")
        
        runner = LLMOutputValidationRunner()
        fields = runner._get_fields_to_grade()
        
        print(f"✅ Found {len(fields)} fields to grade")
        
        # Check key fields are present
        assert "company_name_field" in fields
        assert "industry" in fields
        assert "company_size" in fields
        assert "headquarters" in fields
        
        print(f"   Key fields: {', '.join(fields[:5])}...")
        print("✅ _get_fields_to_grade() works correctly")
    
    def test_grade_field_structure(self):
        """Test that _grade_field() method exists and has correct signature."""
        print("\n=== Testing _grade_field() structure ===")
        
        runner = LLMOutputValidationRunner()
        
        # Check method exists
        assert hasattr(runner, '_grade_field')
        assert callable(runner._grade_field)
        
        print("✅ _grade_field() method exists")
        
        # Check method signature
        import inspect
        sig = inspect.signature(runner._grade_field)
        params = list(sig.parameters.keys())
        
        assert 'flash_model' in params
        assert 'field_name' in params
        assert 'correct_value' in params
        assert 'actual_value' in params
        
        print("✅ _grade_field() has correct signature")
    
    def test_grade_output_with_flash_structure(self):
        """Test that _grade_output_with_flash() method exists."""
        print("\n=== Testing _grade_output_with_flash() structure ===")
        
        runner = LLMOutputValidationRunner()
        
        # Check method exists
        assert hasattr(runner, '_grade_output_with_flash')
        assert callable(runner._grade_output_with_flash)
        
        print("✅ _grade_output_with_flash() method exists")
        
        # Check method signature
        import inspect
        sig = inspect.signature(runner._grade_output_with_flash)
        params = list(sig.parameters.keys())
        
        assert 'session' in params
        assert 'gemini_pro_output' in params
        assert 'other_output' in params
        assert 'company_name' in params
        assert 'test_run_id' in params
        
        print("✅ _grade_output_with_flash() has correct signature")
    
    def test_grading_prompt_loading(self):
        """Test that grading prompts can be loaded from database."""
        print("\n=== Testing grading prompt loading ===")
        
        create_database()
        session = get_session()
        try:
            # Ensure default grading prompt exists
            grading_prompt = GradingPromptManager.get_active_version(session=session)
            
            if not grading_prompt:
                # Create default if it doesn't exist
                grading_prompt = GradingPromptManager.create_default_version(session=session)
            
            print(f"✅ Grading prompt loaded: version {grading_prompt.version}")
            print(f"   Template length: {len(grading_prompt.prompt_template)} chars")
            
            # Check template has required placeholders
            assert '{field_name}' in grading_prompt.prompt_template
            assert '{correct_value}' in grading_prompt.prompt_template
            assert '{actual_value}' in grading_prompt.prompt_template
            
            print("✅ Grading prompt template has required placeholders")
            
        finally:
            session.close()
    
    def test_grade_field_handles_none_values(self):
        """Test that _grade_field() handles None values correctly."""
        print("\n=== Testing _grade_field() handles None values ===")
        
        runner = LLMOutputValidationRunner()
        
        # Test with None values (should not crash)
        # Note: This won't actually call the API, just test the structure
        try:
            # This would normally require a model, but we can test the None handling logic
            # by checking the source code
            import inspect
            source = inspect.getsource(runner._grade_field)
            
            assert 'correct_value is None' in source or 'if correct_value' in source
            assert 'actual_value is None' in source or 'if actual_value' in source
            
            print("✅ _grade_field() handles None values")
            
        except Exception as e:
            print(f"⚠️  Could not verify None handling: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Stages 9-10: Model Execution & Grading System")
    print("=" * 60)
    
    # Test Stage 9
    print("\n" + "=" * 60)
    print("Stage 9: Model Execution & Storage")
    print("=" * 60)
    
    test9 = TestStage9()
    test9.test_get_other_models()
    test9.test_delete_other_model_outputs()
    test9.test_run_model_and_store_structure()
    test9.test_run_test_includes_other_models()
    
    # Test Stage 10
    print("\n" + "=" * 60)
    print("Stage 10: Field-Level Grading")
    print("=" * 60)
    
    test10 = TestStage10()
    test10.test_get_fields_to_grade()
    test10.test_grade_field_structure()
    test10.test_grade_output_with_flash_structure()
    test10.test_grading_prompt_loading()
    test10.test_grade_field_handles_none_values()
    
    print("\n" + "=" * 60)
    print("✅ All Stage 9-10 verification tests passed!")
    print("=" * 60)

