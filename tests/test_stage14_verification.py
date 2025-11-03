"""
Verification tests for Stage 14: CLI Script.

This test verifies that:
- CLI script exists and has correct structure
- Command-line arguments are properly defined
- Help text is present
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestStage14:
    """Test Stage 14: CLI Script"""
    
    def test_script_exists(self):
        """Test that the CLI script exists."""
        print("\n=== Testing script exists ===")
        
        script_path = project_root / "scripts" / "run_llm_output_validation.py"
        assert script_path.exists(), f"Script not found at {script_path}"
        
        print(f"✅ Script exists: {script_path}")
        
        # Check it's executable
        assert os.access(script_path, os.X_OK), "Script is not executable"
        print("✅ Script is executable")
    
    def test_script_structure(self):
        """Test that script has correct structure."""
        print("\n=== Testing script structure ===")
        
        script_path = project_root / "scripts" / "run_llm_output_validation.py"
        content = script_path.read_text()
        
        # Check for required imports
        assert "argparse" in content, "Missing argparse import"
        assert "LLMOutputValidationRunner" in content, "Missing LLMOutputValidationRunner import"
        
        print("✅ Required imports present")
        
        # Check for main function
        assert "def main():" in content, "Missing main() function"
        print("✅ Main function present")
        
        # Check for argument parser
        assert "ArgumentParser" in content, "Missing ArgumentParser"
        print("✅ Argument parser present")
    
    def test_cli_arguments(self):
        """Test that CLI arguments are defined."""
        print("\n=== Testing CLI arguments ===")
        
        script_path = project_root / "scripts" / "run_llm_output_validation.py"
        content = script_path.read_text()
        
        # Required arguments
        required_args = [
            "--company",
            "--companies",
        ]
        
        # Optional arguments
        optional_args = [
            "--prompt-name",
            "--prompt-version",
            "--prompt-version-id",
            "--test-suite-name",
            "--test-run-description",
            "--force-refresh",
            "--max-iterations",
        ]
        
        for arg in required_args + optional_args:
            assert arg in content, f"Missing argument: {arg}"
        
        print(f"✅ All required arguments present: {', '.join(required_args)}")
        print(f"✅ All optional arguments present: {', '.join(optional_args)}")
        
        # Check for mutually exclusive group
        assert "add_mutually_exclusive_group" in content, "Missing mutually exclusive group for company selection"
        print("✅ Mutually exclusive group for company selection")
    
    def test_help_text(self):
        """Test that help text is present."""
        print("\n=== Testing help text ===")
        
        script_path = project_root / "scripts" / "run_llm_output_validation.py"
        content = script_path.read_text()
        
        # Check for description
        assert "description=" in content, "Missing description in ArgumentParser"
        print("✅ Description present")
        
        # Check for examples
        assert "Examples:" in content or "epilog=" in content, "Missing examples/epilog"
        print("✅ Examples/epilog present")
        
        # Check for help text on arguments
        assert "help=" in content, "Missing help text on arguments"
        print("✅ Help text on arguments")
    
    def test_error_handling(self):
        """Test that error handling is present."""
        print("\n=== Testing error handling ===")
        
        script_path = project_root / "scripts" / "run_llm_output_validation.py"
        content = script_path.read_text()
        
        # Check for try/except
        assert "try:" in content or "except" in content, "Missing error handling"
        print("✅ Error handling present (try/except)")
        
        # Check for error messages
        assert "❌" in content or "Error:" in content, "Missing error message formatting"
        print("✅ Error message formatting present")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Stage 14: CLI Script")
    print("=" * 60)
    
    test = TestStage14()
    test.test_script_exists()
    test.test_script_structure()
    test.test_cli_arguments()
    test.test_help_text()
    test.test_error_handling()
    
    print("\n" + "=" * 60)
    print("✅ All Stage 14 verification tests passed!")
    print("=" * 60)
    print("\nNote: Full CLI test requires running on remote server with dependencies.")
    print("      The script structure is correct and ready to use.")

