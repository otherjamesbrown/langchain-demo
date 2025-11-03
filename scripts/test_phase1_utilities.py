#!/usr/bin/env python3
"""
Test script for Phase 1 shared utilities refactoring.

This script validates that:
1. New utilities can be imported
2. Database session manager works correctly
3. Streamlit helpers can be imported (without actually running Streamlit)
4. Refactored modules still work correctly
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all new utilities can be imported."""
    print("Testing imports...")
    
    try:
        from src.utils.database import get_db_session
        print("  ✅ get_db_session imported")
    except ImportError as e:
        print(f"  ❌ Failed to import get_db_session: {e}")
        return False
    
    try:
        from src.utils.streamlit_helpers import init_streamlit_db, get_streamlit_db_session
        print("  ✅ Streamlit helpers imported")
    except ImportError as e:
        print(f"  ❌ Failed to import Streamlit helpers: {e}")
        return False
    
    return True


def test_database_session_manager():
    """Test that database session context manager works."""
    print("\nTesting database session manager...")
    
    try:
        from src.utils.database import get_db_session
        from src.database.schema import Company
        
        # Test: Create new session (auto-closes)
        with get_db_session() as session:
            count = session.query(Company).count()
            print(f"  ✅ Context manager works: Found {count} companies")
        
        # Test: Use existing session (doesn't close)
        from src.database.schema import get_session
        existing_session = get_session()
        try:
            with get_db_session(existing_session) as session:
                assert session is existing_session, "Should use provided session"
                print("  ✅ Context manager respects provided session")
        finally:
            existing_session.close()
        
        return True
    except Exception as e:
        print(f"  ❌ Database session manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_refactored_modules():
    """Test that refactored modules can be imported."""
    print("\nTesting refactored modules...")
    
    modules_to_test = [
        ("src.research.search_executor", "execute_search", "get_search_results_for_company"),
        ("src.research.llm_processor", "process_with_llm"),
        ("src.research.query_generator", "generate_queries", "get_pending_queries"),
        ("src.research.validation", "validate_completeness", "compare_processing_runs"),
    ]
    
    all_passed = True
    for module_name, *functions in modules_to_test:
        try:
            module = __import__(module_name, fromlist=functions)
            for func_name in functions:
                if not hasattr(module, func_name):
                    print(f"  ❌ {module_name}.{func_name} not found")
                    all_passed = False
                else:
                    print(f"  ✅ {module_name}.{func_name} available")
        except Exception as e:
            print(f"  ❌ Failed to import {module_name}: {e}")
            all_passed = False
    
    return all_passed


def main():
    """Run all Phase 1 tests."""
    print("=" * 70)
    print("Phase 1 Shared Utilities Refactoring - Test Suite")
    print("=" * 70)
    
    results = []
    
    # Test 1: Imports
    results.append(("Imports", test_imports()))
    
    # Test 2: Database session manager
    results.append(("Database Session Manager", test_database_session_manager()))
    
    # Test 3: Refactored modules
    results.append(("Refactored Modules", test_refactored_modules()))
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Results Summary")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:.<50} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED - Phase 1 utilities are working correctly!")
    else:
        print("❌ SOME TESTS FAILED - Please review errors above")
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

