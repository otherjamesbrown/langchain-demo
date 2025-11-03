#!/usr/bin/env python3
"""
Run BitMovin test via UI using Playwright and validate results from database.

This script:
1. Uses Playwright MCP to navigate to the test page
2. Triggers test execution via UI
3. Waits for tests to complete
4. Queries database remotely to validate results
"""

import sys
from pathlib import Path
import time
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.operations import get_test_executions
from src.database.schema import get_session


def query_database_remotely(test_name: str = "bitmovin_research", test_company: str = "BitMovin"):
    """Query database on server to get test results."""
    
    # This function will be called after SSH'ing to server
    # For now, we'll use a Python script that can be executed via SSH
    
    script = f"""
import sys
from pathlib import Path
project_root = Path.home() / "langchain-demo"
sys.path.insert(0, str(project_root))

from src.database.operations import get_test_executions
from src.database.schema import get_session, create_database

create_database()
session = get_session()

# Get recent test executions
tests = get_test_executions(
    test_name="{test_name}",
    test_company="{test_company}",
    limit=50,
    session=session
)

print(f"Found {{len(tests)}} test execution(s)")

for test in tests:
    print(f"\\nTest ID: {{test.id}}")
    print(f"  Model: {{test.model_name}} ({{test.model_provider}})")
    print(f"  Success: {{test.success}}")
    print(f"  Required Fields Valid: {{test.required_fields_valid}}")
    print(f"  Optional Fields: {{test.optional_fields_count}}/10")
    print(f"  Execution Time: {{test.execution_time_seconds:.2f}}s" if test.execution_time_seconds else "  Execution Time: N/A")
    print(f"  Date: {{test.created_at}}")
    
    if test.required_fields_errors:
        print(f"  Errors:")
        for error in test.required_fields_errors:
            print(f"    - {{error}}")
    
    if test.required_fields_warnings:
        print(f"  Warnings:")
        for warning in test.required_fields_warnings:
            print(f"    - {{warning}}")
    
    if test.extracted_company_info:
        ci = test.extracted_company_info
        print(f"  Extracted Info:")
        print(f"    company_name: {{ci.get('company_name', 'N/A')}}")
        print(f"    industry: {{ci.get('industry', 'N/A')}}")
        print(f"    company_size: {{ci.get('company_size', 'N/A')}}")
        print(f"    headquarters: {{ci.get('headquarters', 'N/A')}}")
        print(f"    founded: {{ci.get('founded', 'N/A')}}")

session.close()
"""
    
    return script


def validate_test_results():
    """Validate test results from database."""
    
    print("="*70)
    print("Querying database for test results...")
    print("="*70)
    
    create_database()
    session = get_session()
    
    try:
        # Get recent test executions
        tests = get_test_executions(
            test_name="bitmovin_research",
            test_company="BitMovin",
            limit=50,
            session=session
        )
        
        if not tests:
            print("❌ No test results found in database")
            return False
        
        print(f"\n✅ Found {len(tests)} test execution(s)\n")
        
        # Validate each test
        passed = 0
        failed = 0
        
        for test in tests:
            print(f"{'='*70}")
            print(f"Test: {test.model_name} ({test.model_provider})")
            print(f"{'='*70}")
            
            if test.success and test.required_fields_valid:
                print("✅ PASSED")
                passed += 1
            else:
                print("❌ FAILED")
                failed += 1
                if test.error_message:
                    print(f"   Error: {test.error_message}")
            
            print(f"  Required Fields Valid: {test.required_fields_valid}")
            print(f"  Optional Fields: {test.optional_fields_count or 0}/10")
            if test.execution_time_seconds:
                print(f"  Execution Time: {test.execution_time_seconds:.2f}s")
            
            if test.required_fields_errors:
                print(f"  Errors:")
                for error in test.required_fields_errors:
                    print(f"    - {error}")
            
            if test.required_fields_warnings:
                print(f"  Warnings:")
                for warning in test.required_fields_warnings:
                    print(f"    - {warning}")
            
            if test.extracted_company_info:
                ci = test.extracted_company_info
                print(f"\n  Extracted Company Info:")
                print(f"    company_name: {ci.get('company_name', 'N/A')}")
                print(f"    industry: {ci.get('industry', 'N/A')}")
                print(f"    company_size: {ci.get('company_size', 'N/A')}")
                print(f"    headquarters: {ci.get('headquarters', 'N/A')}")
                print(f"    founded: {ci.get('founded', 'N/A')}")
            
            print()
        
        print(f"\n{'='*70}")
        print(f"SUMMARY: {passed} passed, {failed} failed")
        print(f"{'='*70}")
        
        return failed == 0
        
    finally:
        session.close()


if __name__ == "__main__":
    # For local execution, just validate results
    success = validate_test_results()
    sys.exit(0 if success else 1)

