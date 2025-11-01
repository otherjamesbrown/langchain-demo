#!/usr/bin/env python3
"""
Test script for LLM call logging to database.

This script demonstrates how LLM calls are automatically logged
with token usage and metrics to the database.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.metrics import LLMMetrics
from src.utils.llm_logger import log_llm_call, get_llm_logger
from src.database.schema import LLMCallLog, get_session
from src.database.operations import create_database
from llama_cpp import Llama
from dotenv import load_dotenv

load_dotenv()


def test_logging_to_database():
    """Test logging LLM calls to the database."""
    print("=" * 60)
    print("LLM Call Logging Test")
    print("=" * 60)
    
    # Initialize database
    print("\n1. Initializing database...")
    create_database()
    print("   ✓ Database initialized")
    
    # Load model
    model_path = os.getenv("MODEL_PATH", "./models/llama-2-7b-chat.Q4_K_M.gguf")
    print(f"\n2. Loading model: {model_path}")
    model = Llama(model_path=model_path, n_ctx=512, verbose=False)
    print("   ✓ Model loaded")
    
    # Test prompts
    test_prompts = [
        "What is Python programming? Answer briefly.",
        "Explain machine learning in one sentence.",
        "What is 2+2?"
    ]
    
    logger = get_llm_logger()
    
    print("\n3. Making LLM calls and logging to database...")
    print("-" * 60)
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\nCall {i}: {prompt}")
        
        start_time = time.time()
        result = model(prompt, max_tokens=50)
        end_time = time.time()
        
        generation_time = end_time - start_time
        response_text = result['choices'][0]['text']
        
        # Extract metrics
        usage = result.get('usage', {})
        metrics = LLMMetrics(
            prompt_tokens=usage.get('prompt_tokens', 0),
            completion_tokens=usage.get('completion_tokens', 0),
            total_tokens=usage.get('total_tokens', 0),
            start_time=start_time,
            end_time=end_time,
            generation_time=generation_time,
            model_name=model_path,
            model_type="local"
        )
        
        # Log to database
        log_entry = log_llm_call(
            metrics=metrics,
            prompt=prompt,
            response=response_text,
            model_name=os.path.basename(model_path),
            call_type="test"
        )
        
        if log_entry:
            print(f"   ✓ Logged to database (ID: {log_entry.id})")
            print(f"   Tokens: {metrics.total_tokens} | Time: {generation_time:.2f}s")
        else:
            print("   ⚠️  Logging failed")
    
    # Query and display logs
    print("\n" + "=" * 60)
    print("4. Querying logged calls from database...")
    print("-" * 60)
    
    from src.database.operations import get_session
    session = get_session()
    
    try:
        logs = session.query(LLMCallLog).order_by(LLMCallLog.created_at.desc()).limit(5).all()
        
        print(f"\nFound {len(logs)} recent log entries:")
        print()
        
        for log in logs:
            print(f"ID: {log.id}")
            print(f"  Model: {log.model_name} ({log.model_type})")
            print(f"  Tokens: {log.total_tokens} (prompt: {log.prompt_tokens}, completion: {log.completion_tokens})")
            print(f"  Time: {log.generation_time_seconds:.2f}s")
            print(f"  Speed: {log.tokens_per_second:.1f} tok/s" if log.tokens_per_second else "  Speed: N/A")
            print(f"  Success: {'✅' if log.success else '❌'}")
            print(f"  Timestamp: {log.created_at}")
            print()
        
        # Summary stats
        total_calls = session.query(LLMCallLog).count()
        total_tokens = session.query(LLMCallLog.total_tokens).with_entities(
            func.sum(LLMCallLog.total_tokens)
        ).scalar() or 0
        
        print(f"Total calls in database: {total_calls}")
        print(f"Total tokens logged: {total_tokens:,}")
        
    finally:
        session.close()
    
    print("\n" + "=" * 60)
    print("✅ Logging test complete!")
    print("=" * 60)
    print("\nNext step: Run the Streamlit dashboard to view logs:")
    print("  streamlit run src/ui/streamlit_dashboard.py")


if __name__ == "__main__":
    from sqlalchemy import func
    try:
        test_logging_to_database()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

