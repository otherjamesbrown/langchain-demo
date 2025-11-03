#!/usr/bin/env python3
"""
Simple quick test for LLM functionality.

This is a minimal test that verifies the model can:
1. Load successfully
2. Generate a response

Uses the database as the source of truth for model configuration,
consistent with the rest of the codebase.

Usage:
    python scripts/test_llm_simple.py
"""

import os
import sys
from pathlib import Path
from langchain_community.llms import LlamaCpp
from dotenv import load_dotenv

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

def main():
    """Quick LLM test."""
    print("Testing LLM...")
    print("=" * 50)
    
    # Try to get model path from database first (consistent with model_factory)
    model_path = None
    try:
        from src.database.operations import get_default_model_configuration
        from src.database.schema import create_database
        
        # Ensure database exists
        create_database()
        
        # Get default model from database
        db_model = get_default_model_configuration()
        if db_model and db_model.provider == "local" and db_model.model_path:
            # Use model path from database
            model_path = db_model.model_path
            # Resolve relative paths relative to project root
            if not os.path.isabs(model_path):
                model_path = str(project_root / model_path)
            print(f"✓ Using model from database: {db_model.name}")
            print(f"  Path: {model_path}")
    except Exception as e:
        print(f"⚠️  Could not load from database: {e}")
        print("   Falling back to environment variables...")
    
    # Fallback to environment variable or default
    if not model_path:
        model_path = os.getenv("MODEL_PATH", "./models/llama-2-7b-chat.Q4_K_M.gguf")
        if not os.path.isabs(model_path):
            model_path = str(project_root / model_path)
    
    # Resolve and verify path
    model_path = Path(model_path).expanduser().resolve()
    if not model_path.exists():
        print(f"❌ Model not found: {model_path}")
        print(f"   Current directory: {os.getcwd()}")
        print(f"   Project root: {project_root}")
        
        # Try to find available models
        models_dir = project_root / "models"
        if models_dir.exists():
            available = list(models_dir.glob("*.gguf"))
            if available:
                print(f"\n   Available models in {models_dir}:")
                for model in available:
                    print(f"     - {model.name}")
        
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

