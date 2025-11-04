#!/usr/bin/env python3
"""Check what agent run data exists in the database."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import desc, func
from src.database.schema import get_session, LLMCallLog, TestExecution


def main():
    session = get_session()
    
    try:
        print("Checking database for agent run data...")
        print("=" * 80)
        print()
        
        # Check LLMCallLog
        llm_count = session.query(LLMCallLog).count()
        print(f"LLMCallLog entries: {llm_count}")
        
        if llm_count > 0:
            recent_calls = (
                session.query(LLMCallLog)
                .order_by(desc(LLMCallLog.created_at))
                .limit(5)
                .all()
            )
            print("\nRecent LLM calls:")
            for call in recent_calls:
                print(f"  - {call.created_at}: {call.model_name} ({call.model_type})")
                print(f"    Tokens: {call.total_tokens}, Time: {call.generation_time_seconds:.2f}s")
        
        # Check TestExecution
        test_count = session.query(TestExecution).count()
        print(f"\nTestExecution entries: {test_count}")
        
        if test_count > 0:
            recent_tests = (
                session.query(TestExecution)
                .order_by(desc(TestExecution.created_at))
                .limit(5)
                .all()
            )
            print("\nRecent test executions:")
            for test in recent_tests:
                print(f"  - {test.created_at}: {test.model_name} ({test.model_provider})")
                print(f"    Company: {test.test_company}, Iterations: {test.iterations}")
                print(f"    Success: {test.success}")
        
        print()
        print("=" * 80)
        
        # If we have test executions with iterations, use those
        if test_count >= 2:
            print("\n✅ Found test executions! Comparing last 2:")
            print()
            tests = (
                session.query(TestExecution)
                .order_by(desc(TestExecution.created_at))
                .limit(2)
                .all()
            )
            
            for i, test in enumerate(tests, 1):
                print(f"Run {i}:")
                print(f"  Model: {test.model_name} ({test.model_provider})")
                print(f"  Company: {test.test_company}")
                print(f"  Iterations: {test.iterations}")
                print(f"  Time: {test.execution_time_seconds:.2f}s")
                print(f"  Success: {test.success}")
                print()
            
            if len(tests) == 2:
                print("Comparison:")
                print(f"  {tests[0].model_name}: {tests[0].iterations} iterations")
                print(f"  {tests[1].model_name}: {tests[1].iterations} iterations")
                diff = tests[0].iterations - tests[1].iterations
                print(f"  Difference: {diff:+d} iterations")
        
    finally:
        session.close()


if __name__ == "__main__":
    main()


