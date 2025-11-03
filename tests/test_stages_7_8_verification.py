"""
Verification scripts for Stages 7-8 of testing framework implementation.

These tests verify that:
- Stage 7: ResearchAgent can load prompts from database
- Stage 8: LLMOutputValidationRunner can generate and store ground truth
"""

import pytest
from src.agent.research_agent import ResearchAgent
from src.testing.llm_output_validation_runner import LLMOutputValidationRunner
from src.prompts.prompt_manager import PromptManager
from src.database.schema import create_database, get_session, TestRun, LLMOutputValidation


class TestStage7:
    """Test Stage 7: ResearchAgent Integration with Database Prompts."""
    
    def test_load_prompt_by_id(self):
        """Test loading prompt by version ID."""
        create_database()
        session = get_session()
        try:
            # Get a prompt version
            pv = PromptManager.get_active_version("research-agent-prompt", session=session)
            if not pv:
                pytest.skip("No prompt version found. Run initialize_prompts.py first.")
            
            # Test with prompt_version_id
            agent = ResearchAgent(
                model_type="local",
                prompt_version_id=pv.id,
                verbose=False
            )
            assert agent._instructions is not None
            assert len(agent._instructions) > 0
            assert agent._prompt_version_id == pv.id
            print("✅ Can load prompt by ID")
            
        finally:
            session.close()
    
    def test_load_prompt_by_name(self):
        """Test loading prompt by name (active version)."""
        create_database()
        session = get_session()
        try:
            # Test with prompt_name
            agent = ResearchAgent(
                model_type="local",
                prompt_name="research-agent-prompt",
                verbose=False
            )
            assert agent._instructions is not None
            assert len(agent._instructions) > 0
            print("✅ Can load prompt by name")
            
        finally:
            session.close()
    
    def test_load_prompt_by_name_and_version(self):
        """Test loading prompt by name and specific version."""
        create_database()
        session = get_session()
        try:
            # Get a prompt version
            pv = PromptManager.get_active_version("research-agent-prompt", session=session)
            if not pv:
                pytest.skip("No prompt version found. Run initialize_prompts.py first.")
            
            # Test with prompt_name + version
            agent = ResearchAgent(
                model_type="local",
                prompt_name="research-agent-prompt",
                prompt_version=pv.version,
                verbose=False
            )
            assert agent._instructions is not None
            assert agent._prompt_version == pv.version
            print("✅ Can load prompt by name and version")
            
        finally:
            session.close()
    
    def test_legacy_file_based_still_works(self):
        """Test that legacy file-based prompt loading still works."""
        # Test legacy file-based (should still work)
        agent = ResearchAgent(
            model_type="local",
            verbose=False
            # No prompt parameters = file-based
        )
        assert agent._instructions is not None
        assert len(agent._instructions) > 0
        assert agent._prompt_version_id is None  # Should be None for file-based
        print("✅ Legacy file-based loading still works")


class TestStage8:
    """Test Stage 8: LLMOutputValidationRunner Core Structure & Ground Truth."""
    
    def test_runner_initialization(self):
        """Test runner can be initialized."""
        create_database()
        
        # Test with prompt_name
        runner = LLMOutputValidationRunner(
            prompt_name="research-agent-prompt",
            test_run_description="Stage 8 test"
        )
        
        assert runner.test_name == "llm-output-validation"
        assert runner._resolved_prompt_version is not None
        print("✅ Runner initialized successfully")
    
    def test_runner_with_prompt_version_id(self):
        """Test runner with prompt version ID."""
        create_database()
        session = get_session()
        try:
            pv = PromptManager.get_active_version("research-agent-prompt", session=session)
            if not pv:
                pytest.skip("No prompt version found. Run initialize_prompts.py first.")
            
            runner = LLMOutputValidationRunner(
                prompt_version_id=pv.id,
                test_run_description="Stage 8 test"
            )
            
            assert runner._resolved_prompt_version.id == pv.id
            print("✅ Runner initialized with prompt version ID")
            
        finally:
            session.close()
    
    def test_create_test_run(self):
        """Test that runner can create test run record."""
        create_database()
        session = get_session()
        try:
            pv = PromptManager.get_active_version("research-agent-prompt", session=session)
            if not pv:
                pytest.skip("No prompt version found. Run initialize_prompts.py first.")
            
            runner = LLMOutputValidationRunner(
                prompt_version_id=pv.id,
                test_run_description="Test run creation test"
            )
            
            # Create a test run manually to verify structure
            test_run = TestRun(
                test_name=runner.test_name,
                company_name="TestCompany",
                prompt_version_id=pv.id,
                prompt_name=pv.prompt_name,
                prompt_version=pv.version,
                description="Test",
            )
            session.add(test_run)
            session.commit()
            
            assert test_run.id is not None
            assert test_run.prompt_version_obj.id == pv.id
            print("✅ Can create test run record")
            
            # Cleanup
            session.delete(test_run)
            session.commit()
            
        finally:
            session.close()
    
    def test_cost_calculation(self):
        """Test cost calculation function."""
        create_database()
        
        runner = LLMOutputValidationRunner(
            prompt_name="research-agent-prompt"
        )
        
        # Test cost calculation
        cost = runner._calculate_cost(
            model_provider="gemini",
            model_name="gemini-flash-latest",
            input_tokens=1000000,
            output_tokens=500000,
        )
        
        # Expected: (1M * 0.075/1M) + (0.5M * 0.30/1M) = 0.075 + 0.15 = 0.225
        assert cost > 0
        assert cost < 1.0  # Should be reasonable
        print(f"✅ Cost calculation works: ${cost:.6f}")
    
    def test_ground_truth_structure(self):
        """Test ground truth output storage structure."""
        create_database()
        session = get_session()
        try:
            pv = PromptManager.get_active_version("research-agent-prompt", session=session)
            if not pv:
                pytest.skip("No prompt version found. Run initialize_prompts.py first.")
            
            runner = LLMOutputValidationRunner(
                prompt_version_id=pv.id
            )
            
            # Verify runner has all required methods
            assert hasattr(runner, '_ensure_gemini_pro_output')
            assert hasattr(runner, '_run_gemini_pro_and_store')
            assert hasattr(runner, '_store_output')
            assert hasattr(runner, '_calculate_cost')
            assert hasattr(runner, '_copy_output_to_test_run')
            print("✅ Runner has all required methods")
            
        finally:
            session.close()


if __name__ == "__main__":
    """Run verification tests directly."""
    print("=" * 60)
    print("Testing Stage 7: ResearchAgent Integration")
    print("=" * 60)
    
    test7 = TestStage7()
    test7.test_load_prompt_by_id()
    test7.test_load_prompt_by_name()
    test7.test_load_prompt_by_name_and_version()
    test7.test_legacy_file_based_still_works()
    
    print("\n" + "=" * 60)
    print("Testing Stage 8: LLMOutputValidationRunner")
    print("=" * 60)
    
    test8 = TestStage8()
    test8.test_runner_initialization()
    test8.test_runner_with_prompt_version_id()
    test8.test_create_test_run()
    test8.test_cost_calculation()
    test8.test_ground_truth_structure()
    
    print("\n" + "=" * 60)
    print("✅ All stages 7-8 verification tests passed!")
    print("=" * 60)
    print("\nNote: Ground truth generation requires API keys and will make actual API calls.")
    print("      Run with caution in production environments.")

