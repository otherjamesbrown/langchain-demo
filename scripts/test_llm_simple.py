#!/usr/bin/env python3
"""
Simple quick test for LLM functionality.

This is a minimal test that verifies the model can:
1. Load successfully
2. Generate a response

Usage:
    python scripts/test_llm_simple.py
"""

import os
from pathlib import Path
from langchain_community.llms import LlamaCpp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Quick LLM test."""
    print("Testing LLM...")
    print("=" * 50)
    
    # Get model path from environment or use default
    model_path = os.getenv("MODEL_PATH", "./models/llama-2-7b-chat.Q4_K_M.gguf")
    
    if not os.path.exists(model_path):
        print(f"❌ Model not found: {model_path}")
        print(f"   Current directory: {os.getcwd()}")
        return 1
    
    print(f"Model: {model_path}")
    print("Loading model (this may take 10-30 seconds on first load)...\n")
    
    try:
        # Load model
        llm = LlamaCpp(
            model_path=model_path,
            n_ctx=2048,
            n_gpu_layers=-1,  # Use GPU if available
            temperature=0.7,
            verbose=False
        )
        
        print("✓ Model loaded successfully!\n")
        
        # Test with a simple prompt
        prompt = "What is Python programming? Answer in 2-3 sentences."
        print(f"Prompt: {prompt}\n")
        print("Generating response...\n")
        
        response = llm.invoke(prompt)
        
        print("Response:")
        print("-" * 50)
        print(response)
        print("-" * 50)
        
        print("\n✅ LLM test successful!")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

