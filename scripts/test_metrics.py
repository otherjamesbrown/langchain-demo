#!/usr/bin/env python3
"""
Test script for LLM metrics tracking.

This script demonstrates how to track token usage and other metrics
when using the local LLM.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.metrics import MetricsTracker, LLMMetrics
from llama_cpp import Llama
from langchain_community.llms import LlamaCpp
from dotenv import load_dotenv

load_dotenv()


def test_direct_llama_metrics():
    """Test metrics extraction from direct llama-cpp-python usage."""
    print("=" * 60)
    print("Test 1: Direct llama-cpp-python Metrics")
    print("=" * 60)
    
    model_path = os.getenv("MODEL_PATH", "./models/llama-2-7b-chat.Q4_K_M.gguf")
    
    print(f"Loading model: {model_path}")
    model = Llama(model_path=model_path, n_ctx=512, verbose=False)
    
    tracker = MetricsTracker()
    
    # Test with multiple prompts
    prompts = [
        "What is Python?",
        "Explain machine learning briefly.",
        "Count from 1 to 5."
    ]
    
    for prompt in prompts:
        print(f"\nPrompt: {prompt}")
        
        start_time = time.time()
        result = model(prompt, max_tokens=50)
        end_time = time.time()
        
        generation_time = end_time - start_time
        metrics = tracker.extract_from_llama_result(
            result, 
            model_path=model_path,
            generation_time=generation_time
        )
        
        tracker.record(metrics)
        
        print(f"  Response: {result['choices'][0]['text'][:50]}...")
        print(f"  Metrics: {metrics}")
    
    # Show summary
    print("\n" + "-" * 60)
    print("Summary:")
    print("-" * 60)
    summary = tracker.summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    return tracker


def test_langchain_metrics():
    """Test metrics with LangChain wrapper."""
    print("\n" + "=" * 60)
    print("Test 2: LangChain LlamaCpp Metrics")
    print("=" * 60)
    
    model_path = os.getenv("MODEL_PATH", "./models/llama-2-7b-chat.Q4_K_M.gguf")
    
    print(f"Loading model via LangChain: {model_path}")
    llm = LlamaCpp(model_path=model_path, n_ctx=512, verbose=False)
    
    # Note: LangChain LlamaCpp doesn't expose usage metrics directly
    # We need to use the underlying client or track manually
    print("\nNote: LangChain LlamaCpp wrapper doesn't expose token usage")
    print("directly. We need to access the underlying client or use")
    print("direct llama-cpp-python for detailed metrics.")
    
    prompt = "What is artificial intelligence?"
    print(f"\nPrompt: {prompt}")
    
    start_time = time.time()
    response = llm.invoke(prompt)
    end_time = time.time()
    
    generation_time = end_time - start_time
    
    print(f"Response: {response[:50]}...")
    print(f"Generation time: {generation_time:.2f}s")
    print(f"Response length: {len(response)} characters")
    
    # Try to get metrics from the underlying client
    if hasattr(llm, 'client'):
        print("\nAccessing underlying client for metrics...")
        # We'd need to call the client directly to get usage metrics


def test_metrics_tracking():
    """Test the MetricsTracker class functionality."""
    print("\n" + "=" * 60)
    print("Test 3: MetricsTracker Class")
    print("=" * 60)
    
    tracker = MetricsTracker()
    
    # Simulate multiple LLM calls
    test_results = [
        {
            "usage": {"prompt_tokens": 10, "completion_tokens": 25, "total_tokens": 35},
            "model": "llama-2-7b",
            "id": "test-1"
        },
        {
            "usage": {"prompt_tokens": 15, "completion_tokens": 30, "total_tokens": 45},
            "model": "llama-2-7b",
            "id": "test-2"
        },
        {
            "usage": {"prompt_tokens": 12, "completion_tokens": 40, "total_tokens": 52},
            "model": "llama-2-7b",
            "id": "test-3"
        }
    ]
    
    for i, result in enumerate(test_results):
        metrics = tracker.extract_from_llama_result(
            result,
            model_path="test-model",
            generation_time=1.5 + i * 0.5
        )
        tracker.record(metrics)
        print(f"Call {i+1}: {metrics}")
    
    print("\nAggregate Summary:")
    print("-" * 60)
    summary = tracker.summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")


def main():
    """Run all metric tests."""
    print("\n" + "=" * 60)
    print("LLM Metrics Tracking Test Suite")
    print("=" * 60)
    
    try:
        # Test 1: Direct llama-cpp-python
        tracker = test_direct_llama_metrics()
        
        # Test 2: LangChain wrapper (limitations)
        test_langchain_metrics()
        
        # Test 3: MetricsTracker class
        test_metrics_tracking()
        
        print("\n" + "=" * 60)
        print("✅ All metric tests completed!")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

