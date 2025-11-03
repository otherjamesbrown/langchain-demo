#!/usr/bin/env python3
"""
Quick test script to verify all UI imports work correctly.
Run this before testing the Streamlit UI to catch import errors early.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Change to project directory
import os
os.chdir(project_root)

print("Testing UI imports...")

try:
    print("  ✓ Testing database imports...")
    from src.database.schema import get_session, create_database
    from src.database.operations import (
        ensure_default_configuration,
        get_model_configurations,
        get_api_key,
        save_test_execution,
        get_test_executions,
    )
    
    print("  ✓ Testing Streamlit...")
    import streamlit as st
    import pandas as pd
    import json
    
    print("  ✓ Testing testing framework imports...")
    from src.testing.test_runner import TestRunner, ModelTestResult, TestExecutionResult
    from src.testing.baselines import get_baseline
    from src.testing.matchers import FieldMatcher
    
    print("  ✓ Testing baseline loading...")
    baseline = get_baseline("bitmovin")
    print(f"    Loaded: {baseline.test_name} - {baseline.company_name}")
    
    print("\n✅ All imports successful! UI should work correctly.")
    print("\nTo test the UI:")
    print("  1. Start Streamlit: streamlit run src/ui/pages/4_🧪_Test_BitMovin.py")
    print("  2. Navigate to the Test_BitMovin page")
    print("  3. Select models and run a test")

except ImportError as e:
    print(f"\n❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

