"""
Verification tests for Stages 16-18.

This test verifies that:
- Stage 16: Cost analysis functions work correctly
- Stage 17: CLI script for comparing versions exists and works
- Stage 18: UI page exists and has correct structure
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestStages16_18:
    """Test Stages 16-18"""
    
    def test_stage16_cost_analysis_exists(self):
        """Test that cost analysis method exists."""
        print("\n=== Testing Stage 16: Cost Analysis ===")
        
        from src.testing.prompt_analytics import PromptAnalytics
        
        assert hasattr(PromptAnalytics, 'get_cost_analysis'), "Missing get_cost_analysis method"
        print("✅ get_cost_analysis method exists")
        
        # Test that it can be called (may return empty data)
        from src.database.schema import get_session
        session = get_session()
        try:
            result = PromptAnalytics.get_cost_analysis(session=session)
            assert isinstance(result, dict), "Result should be a dict"
            assert 'total' in result, "Result should have 'total' key"
            assert 'by_prompt_version' in result, "Result should have 'by_prompt_version' key"
            assert 'by_company' in result, "Result should have 'by_company' key"
            assert 'by_model' in result, "Result should have 'by_model' key"
            print("✅ get_cost_analysis returns correct structure")
        finally:
            session.close()
    
    def test_stage17_cli_script_exists(self):
        """Test that CLI script exists."""
        print("\n=== Testing Stage 17: CLI Script ===")
        
        script_path = project_root / "scripts" / "compare_prompt_versions.py"
        assert script_path.exists(), f"Script not found at {script_path}"
        print(f"✅ Script exists: {script_path}")
        
        # Check it's executable
        assert os.access(script_path, os.X_OK), "Script is not executable"
        print("✅ Script is executable")
        
        # Check structure
        content = script_path.read_text()
        assert "argparse" in content, "Missing argparse"
        assert "PromptAnalytics" in content, "Missing PromptAnalytics import"
        assert "compare_prompt_versions" in content, "Missing compare_prompt_versions call"
        assert "get_cost_analysis" in content, "Missing get_cost_analysis call"
        print("✅ Script structure correct")
        
        # Test help
        import subprocess
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Script should show help without errors"
        assert "prompt" in result.stdout.lower(), "Help should mention prompt"
        print("✅ Script help works")
    
    def test_stage18_ui_page_exists(self):
        """Test that UI page exists."""
        print("\n=== Testing Stage 18: UI Integration ===")
        
        ui_path = project_root / "src" / "ui" / "pages" / "5_🧪_LLM_Output_Validation.py"
        assert ui_path.exists(), f"UI page not found at {ui_path}"
        print(f"✅ UI page exists: {ui_path}")
        
        # Check structure
        content = ui_path.read_text()
        assert "streamlit" in content, "Missing streamlit import"
        assert "LLMOutputValidationRunner" in content, "Missing LLMOutputValidationRunner import"
        assert "PromptAnalytics" in content, "Missing PromptAnalytics import"
        assert "st.tabs" in content, "Missing tabs"
        assert "Run Test" in content, "Missing Run Test tab"
        assert "Compare Versions" in content, "Missing Compare Versions tab"
        assert "Cost Analysis" in content, "Missing Cost Analysis tab"
        print("✅ UI page structure correct")
        
        # Check for required functions
        assert "display_test_results" in content, "Missing display_test_results"
        assert "display_comparison" in content, "Missing display_comparison"
        assert "display_cost_analysis" in content, "Missing display_cost_analysis"
        print("✅ UI display functions present")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Stages 16-18")
    print("=" * 60)
    
    test = TestStages16_18()
    test.test_stage16_cost_analysis_exists()
    test.test_stage17_cli_script_exists()
    test.test_stage18_ui_page_exists()
    
    print("\n" + "=" * 60)
    print("✅ All Stages 16-18 verification tests passed!")
    print("=" * 60)

