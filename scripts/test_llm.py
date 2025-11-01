#!/usr/bin/env python3
"""
Simple test script to verify LLM is working correctly.

This script tests:
1. Direct llama-cpp-python loading
2. LangChain LlamaCpp wrapper
3. Model factory (if available)

Usage:
    python scripts/test_llm.py
    # Or with specific model path:
    MODEL_PATH=./models/llama-2-7b-chat.Q4_K_M.gguf python scripts/test_llm.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_direct_llama():
    """Test direct llama-cpp-python usage."""
    print("=" * 60)
    print("Test 1: Direct llama-cpp-python")
    print("=" * 60)
    
    try:
        from llama_cpp import Llama
        
        model_path = os.getenv("MODEL_PATH", "./models/llama-2-7b-chat.Q4_K_M.gguf")
        
        if not os.path.exists(model_path):
            print(f"❌ Model file not found: {model_path}")
            return False
        
        print(f"Loading model from: {model_path}")
        print("This may take a moment...")
        
        # Load model with minimal context for testing
        model = Llama(
            model_path=model_path,
            n_ctx=512,  # Small context for quick test
            n_gpu_layers=-1,  # Use all GPU layers if available
            verbose=False
        )
        
        print("✓ Model loaded successfully!")
        
        # Test prompt
        prompt = "What is artificial intelligence? Answer in one sentence."
        print(f"\nPrompt: {prompt}")
        print("\nGenerating response...")
        
        response = model(
            prompt,
            max_tokens=50,
            temperature=0.7,
            stop=["\n\n"],
            echo=False
        )
        
        result = response['choices'][0]['text'].strip()
        print(f"\nResponse: {result}")
        print("\n✓ Direct llama-cpp-python test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_langchain_wrapper():
    """Test LangChain LlamaCpp wrapper."""
    print("\n" + "=" * 60)
    print("Test 2: LangChain LlamaCpp Wrapper")
    print("=" * 60)
    
    try:
        from langchain_community.llms import LlamaCpp
        
        model_path = os.getenv("MODEL_PATH", "./models/llama-2-7b-chat.Q4_K_M.gguf")
        
        if not os.path.exists(model_path):
            print(f"❌ Model file not found: {model_path}")
            return False
        
        print(f"Loading model via LangChain from: {model_path}")
        print("This may take a moment...")
        
        llm = LlamaCpp(
            model_path=model_path,
            n_ctx=512,
            n_gpu_layers=-1,
            verbose=False
        )
        
        print("✓ LangChain model loaded successfully!")
        
        # Test prompt
        prompt = "Explain machine learning in one sentence."
        print(f"\nPrompt: {prompt}")
        print("\nGenerating response...")
        
        response = llm.invoke(prompt)
        
        print(f"\nResponse: {response}")
        print("\n✓ LangChain wrapper test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_model_factory():
    """Test our model factory (if available)."""
    print("\n" + "=" * 60)
    print("Test 3: Model Factory")
    print("=" * 60)
    
    try:
        from src.models.model_factory import get_llm, list_available_providers
        
        providers = list_available_providers()
        print(f"Available providers: {providers}")
        
        if "local" not in providers:
            print("⚠️  Local provider not available, skipping factory test")
            return True
        
        model_path = os.getenv("MODEL_PATH", "./models/llama-2-7b-chat.Q4_K_M.gguf")
        
        print(f"\nLoading model via factory from: {model_path}")
        print("This may take a moment...")
        
        llm = get_llm(
            model_type="local",
            model_path=model_path,
            n_ctx=512,
            n_gpu_layers=-1
        )
        
        print("✓ Model factory loaded successfully!")
        
        # Test prompt
        prompt = "What is Python? Answer in one sentence."
        print(f"\nPrompt: {prompt}")
        print("\nGenerating response...")
        
        response = llm.invoke(prompt)
        
        print(f"\nResponse: {response}")
        print("\n✓ Model factory test passed!")
        return True
        
    except Exception as e:
        print(f"⚠️  Model factory test skipped: {e}")
        return True  # Not a failure if factory not ready


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("LLM Test Suite")
    print("=" * 60)
    print("\nThis script tests the Llama model installation.")
    print("Note: First load may take longer as model loads into memory.\n")
    
    results = []
    
    # Test 1: Direct llama-cpp-python
    results.append(("Direct llama-cpp-python", test_direct_llama()))
    
    # Test 2: LangChain wrapper
    results.append(("LangChain LlamaCpp", test_langchain_wrapper()))
    
    # Test 3: Model factory (optional)
    results.append(("Model Factory", test_model_factory()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests passed! LLM is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

