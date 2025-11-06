#!/usr/bin/env python3
"""
Test script for basic LangSmith integration.

This script demonstrates the enhanced LangSmith monitoring capabilities:
1. Configuration and setup
2. EnhancedLangSmithCallback usage
3. Context managers for tracing
4. Token usage and cost tracking

Run this script to verify LangSmith is working correctly.

Requirements:
- LANGCHAIN_API_KEY must be set in .env file
- LangSmith account at https://smith.langchain.com

Usage:
    python scripts/test_langsmith_basic.py
"""

import os
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.utils.monitoring import (
    EnhancedLangSmithCallback,
    configure_langsmith_tracing,
    langsmith_trace,
    langsmith_phase_trace
)


def test_configuration():
    """Test 1: Verify LangSmith configuration."""
    print("\n" + "="*60)
    print("TEST 1: LangSmith Configuration")
    print("="*60)
    
    # Check if API key is set
    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        print("❌ LANGCHAIN_API_KEY not set in environment")
        print("   Please add it to your .env file:")
        print("   LANGCHAIN_API_KEY=ls__your_api_key_here")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    # Configure tracing
    success = configure_langsmith_tracing(
        project_name="langsmith-test-basic",
        tags=["test", "phase1"],
        metadata={"test_type": "basic", "version": "1.0"},
        verbose=True
    )
    
    if success:
        print("✅ LangSmith configuration successful")
    else:
        print("❌ LangSmith configuration failed")
    
    return success


def test_callback_with_openai():
    """Test 2: Test callback with OpenAI (if API key available)."""
    print("\n" + "="*60)
    print("TEST 2: EnhancedLangSmithCallback with OpenAI")
    print("="*60)
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("⚠️  OPENAI_API_KEY not set, skipping OpenAI test")
        return True  # Skip, not a failure
    
    try:
        from langchain_openai import ChatOpenAI
        
        # Create callback
        callback = EnhancedLangSmithCallback(
            metadata={"company": "Test Company", "phase": "llm-processing"},
            track_costs=True,
            verbose=True
        )
        
        # Create LLM
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
            max_tokens=100
        )
        
        # Make a simple call
        print("\n📞 Making test call to OpenAI...")
        response = llm.invoke(
            "Say 'Hello from LangSmith testing!' in exactly 5 words.",
            config={"callbacks": [callback]}
        )
        
        print(f"\n✅ Response: {response.content}")
        
        # Print callback summary
        callback.print_summary()
        
        return True
        
    except Exception as e:
        print(f"❌ Error in OpenAI test: {e}")
        return False


def test_callback_with_local_llm():
    """Test 3: Test callback with local LLM (if available)."""
    print("\n" + "="*60)
    print("TEST 3: EnhancedLangSmithCallback with Local LLM")
    print("="*60)
    
    model_path = os.getenv("MODEL_PATH")
    if not model_path or not os.path.exists(model_path):
        print("⚠️  Local model not available, skipping local LLM test")
        return True  # Skip, not a failure
    
    try:
        from langchain_community.llms import LlamaCpp
        
        # Create callback
        callback = EnhancedLangSmithCallback(
            metadata={"model_type": "local", "model": "llama"},
            track_costs=False,  # No cost for local models
            verbose=True
        )
        
        # Create LLM
        llm = LlamaCpp(
            model_path=model_path,
            temperature=0.7,
            max_tokens=50,
            n_ctx=2048,
            verbose=False
        )
        
        # Make a simple call
        print("\n📞 Making test call to local LLM...")
        response = llm.invoke(
            "Say hello in 5 words.",
            config={"callbacks": [callback]}
        )
        
        print(f"\n✅ Response: {response}")
        
        # Print callback summary
        callback.print_summary()
        
        return True
        
    except Exception as e:
        print(f"❌ Error in local LLM test: {e}")
        return False


def test_context_manager():
    """Test 4: Test langsmith_trace context manager."""
    print("\n" + "="*60)
    print("TEST 4: langsmith_trace Context Manager")
    print("="*60)
    
    try:
        with langsmith_trace(
            name="test_trace",
            tags=["test", "context-manager"],
            metadata={"test_type": "context_manager"}
        ) as trace:
            print(f"✅ Trace started: {trace['name']}")
            print(f"   Tags: {trace['tags']}")
            print(f"   Metadata: {trace['metadata']}")
            print(f"   Enabled: {trace['enabled']}")
            
            # Simulate some work
            import time
            time.sleep(0.5)
            
            print("✅ Work completed successfully")
        
        print(f"✅ Trace duration: {trace['duration']:.2f}s")
        print(f"✅ Trace success: {trace['success']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in context manager test: {e}")
        return False


def test_phase_context_manager():
    """Test 5: Test langsmith_phase_trace context manager."""
    print("\n" + "="*60)
    print("TEST 5: langsmith_phase_trace Context Manager")
    print("="*60)
    
    try:
        # Test Phase 1
        print("\n📊 Testing Phase 1 trace...")
        with langsmith_phase_trace(
            phase="phase1",
            company_name="Test Company"
        ) as trace:
            print(f"✅ Phase 1 trace started")
            print(f"   Name: {trace['name']}")
            print(f"   Tags: {trace['tags']}")
            print(f"   Metadata: {trace['metadata']}")
            
            import time
            time.sleep(0.3)
        
        print(f"✅ Phase 1 trace completed ({trace['duration']:.2f}s)")
        
        # Test Phase 2
        print("\n📊 Testing Phase 2 trace...")
        with langsmith_phase_trace(
            phase="phase2",
            company_name="Test Company",
            model_name="gpt-4"
        ) as trace:
            print(f"✅ Phase 2 trace started")
            print(f"   Name: {trace['name']}")
            print(f"   Tags: {trace['tags']}")
            print(f"   Metadata: {trace['metadata']}")
            
            import time
            time.sleep(0.3)
        
        print(f"✅ Phase 2 trace completed ({trace['duration']:.2f}s)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in phase context manager test: {e}")
        return False


def test_error_handling():
    """Test 6: Test error handling in callbacks."""
    print("\n" + "="*60)
    print("TEST 6: Error Handling")
    print("="*60)
    
    try:
        with langsmith_trace(
            name="test_error_trace",
            tags=["test", "error-handling"]
        ) as trace:
            print("✅ Starting trace that will error...")
            
            # Intentionally cause an error
            raise ValueError("This is a test error")
        
    except ValueError as e:
        print(f"✅ Error caught: {e}")
        print(f"✅ Trace error recorded: {trace.get('error')}")
        print(f"✅ Trace success: {trace.get('success')}")
        return True
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("LANGSMITH BASIC INTEGRATION TESTS")
    print("="*80)
    print("\nTesting enhanced LangSmith monitoring capabilities...")
    print("Traces will appear at: https://smith.langchain.com")
    
    results = {
        "Configuration": test_configuration(),
        "OpenAI Callback": test_callback_with_openai(),
        "Local LLM Callback": test_callback_with_local_llm(),
        "Context Manager": test_context_manager(),
        "Phase Context Manager": test_phase_context_manager(),
        "Error Handling": test_error_handling()
    }
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for p in results.values() if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        print("\n📊 Next steps:")
        print("1. Visit https://smith.langchain.com")
        print("2. Navigate to the 'langsmith-test-basic' project")
        print("3. Explore the traces from these tests")
        print("4. Check token usage, costs, and execution times")
    else:
        print("\n⚠️  Some tests failed. Please check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

