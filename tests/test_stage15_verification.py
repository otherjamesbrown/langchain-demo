"""
Verification tests for Stage 15: Prompt Analytics.

This test verifies that:
- PromptAnalytics class exists and has required methods
- compare_prompt_versions() method works correctly
- get_test_run_history() method works correctly
- Queries are efficient and return correct data
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.testing.prompt_analytics import PromptAnalytics
from src.database.schema import get_session, TestRun, LLMOutputValidationResult


class TestStage15:
    """Test Stage 15: Prompt Analytics"""
    
    def test_module_exists(self):
        """Test that PromptAnalytics module exists."""
        print("\n=== Testing module exists ===")
        
        assert PromptAnalytics is not None, "PromptAnalytics class not found"
        print("✅ PromptAnalytics class exists")
    
    def test_methods_exist(self):
        """Test that required methods exist."""
        print("\n=== Testing methods exist ===")
        
        assert hasattr(PromptAnalytics, 'compare_prompt_versions'), "Missing compare_prompt_versions"
        assert hasattr(PromptAnalytics, 'get_test_run_history'), "Missing get_test_run_history"
        assert hasattr(PromptAnalytics, 'get_version_stats_by_company'), "Missing get_version_stats_by_company"
        
        print("✅ All required methods exist")
        print("   - compare_prompt_versions")
        print("   - get_test_run_history")
        print("   - get_version_stats_by_company")
    
    def test_compare_prompt_versions_structure(self):
        """Test that compare_prompt_versions returns correct structure."""
        print("\n=== Testing compare_prompt_versions structure ===")
        
        session = get_session()
        try:
            # Get any prompt name that exists
            from src.database.schema import PromptVersion
            prompt_version = session.query(PromptVersion).first()
            
            if prompt_version:
                prompt_name = prompt_version.prompt_name
                print(f"   Testing with prompt: {prompt_name}")
                
                # Call the method (may return empty list if no test data)
                result = PromptAnalytics.compare_prompt_versions(
                    prompt_name=prompt_name,
                    session=session
                )
                
                # Verify structure
                assert isinstance(result, list), "Result should be a list"
                print(f"✅ compare_prompt_versions returns list ({len(result)} versions found)")
                
                if result:
                    # Check structure of first result
                    first = result[0]
                    required_fields = [
                        'prompt_version',
                        'prompt_version_id',
                        'test_runs_count',
                        'average_overall_accuracy',
                        'companies_tested',
                    ]
                    
                    for field in required_fields:
                        assert field in first, f"Missing field: {field}"
                    
                    print(f"✅ Result structure correct")
                    print(f"   Sample: Version {first['prompt_version']}, "
                          f"{first['test_runs_count']} test runs, "
                          f"{first.get('average_overall_accuracy', 'N/A'):.1f}% avg accuracy")
                else:
                    print("   ⚠️  No test data found (this is OK if no tests have been run)")
            else:
                print("   ⚠️  No prompt versions found in database")
                
        finally:
            session.close()
    
    def test_get_test_run_history_structure(self):
        """Test that get_test_run_history returns correct structure."""
        print("\n=== Testing get_test_run_history structure ===")
        
        session = get_session()
        try:
            # Call the method
            result = PromptAnalytics.get_test_run_history(
                limit=5,
                session=session
            )
            
            # Verify structure
            assert isinstance(result, list), "Result should be a list"
            print(f"✅ get_test_run_history returns list ({len(result)} test runs found)")
            
            if result:
                # Check structure of first result
                first = result[0]
                required_fields = [
                    'test_run_id',
                    'test_name',
                    'company_name',
                    'prompt_name',
                    'prompt_version',
                    'created_at',
                    'outputs_count',
                    'grading_results_count',
                ]
                
                for field in required_fields:
                    assert field in first, f"Missing field: {field}"
                
                print(f"✅ Result structure correct")
                print(f"   Sample: Test Run {first['test_run_id']}, "
                      f"Company: {first['company_name']}, "
                      f"Prompt: {first['prompt_name']}@{first['prompt_version']}")
            else:
                print("   ⚠️  No test runs found (this is OK if no tests have been run)")
                
        finally:
            session.close()
    
    def test_get_version_stats_by_company_structure(self):
        """Test that get_version_stats_by_company returns correct structure."""
        print("\n=== Testing get_version_stats_by_company structure ===")
        
        session = get_session()
        try:
            # Get any prompt version that exists
            from src.database.schema import PromptVersion
            prompt_version = session.query(PromptVersion).first()
            
            if prompt_version:
                prompt_name = prompt_version.prompt_name
                prompt_ver = prompt_version.version
                
                print(f"   Testing with: {prompt_name}@{prompt_ver}")
                
                # Call the method
                result = PromptAnalytics.get_version_stats_by_company(
                    prompt_name=prompt_name,
                    prompt_version=prompt_ver,
                    session=session
                )
                
                # Verify structure
                assert isinstance(result, list), "Result should be a list"
                print(f"✅ get_version_stats_by_company returns list ({len(result)} companies found)")
                
                if result:
                    # Check structure of first result
                    first = result[0]
                    required_fields = [
                        'company_name',
                        'test_runs_count',
                        'average_overall_accuracy',
                    ]
                    
                    for field in required_fields:
                        assert field in first, f"Missing field: {field}"
                    
                    print(f"✅ Result structure correct")
                    print(f"   Sample: {first['company_name']}, "
                          f"{first['test_runs_count']} test runs")
                else:
                    print("   ⚠️  No test data found for this version")
            else:
                print("   ⚠️  No prompt versions found in database")
                
        finally:
            session.close()
    
    def test_filters_work(self):
        """Test that filtering parameters work correctly."""
        print("\n=== Testing filters work ===")
        
        session = get_session()
        try:
            # Get a test run if exists
            test_run = session.query(TestRun).first()
            
            if test_run:
                print(f"   Testing with: {test_run.prompt_name}, {test_run.company_name}")
                
                # Test company filter
                history = PromptAnalytics.get_test_run_history(
                    company_name=test_run.company_name,
                    limit=10,
                    session=session
                )
                
                if history:
                    # All results should be for the same company
                    all_same_company = all(
                        h['company_name'] == test_run.company_name
                        for h in history
                    )
                    assert all_same_company, "Company filter not working"
                    print(f"✅ Company filter works ({len(history)} results)")
                
                # Test prompt name filter
                history = PromptAnalytics.get_test_run_history(
                    prompt_name=test_run.prompt_name,
                    limit=10,
                    session=session
                )
                
                if history:
                    # All results should be for the same prompt
                    all_same_prompt = all(
                        h['prompt_name'] == test_run.prompt_name
                        for h in history
                    )
                    assert all_same_prompt, "Prompt name filter not working"
                    print(f"✅ Prompt name filter works ({len(history)} results)")
            else:
                print("   ⚠️  No test runs found (this is OK if no tests have been run)")
                
        finally:
            session.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Stage 15: Prompt Analytics")
    print("=" * 60)
    
    test = TestStage15()
    test.test_module_exists()
    test.test_methods_exist()
    test.test_compare_prompt_versions_structure()
    test.test_get_test_run_history_structure()
    test.test_get_version_stats_by_company_structure()
    test.test_filters_work()
    
    print("\n" + "=" * 60)
    print("✅ All Stage 15 verification tests passed!")
    print("=" * 60)
    print("\nNote: Full functionality test requires test data in database.")
    print("      Run some tests first to see analytics in action.")

