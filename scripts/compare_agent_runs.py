#!/usr/bin/env python3
"""
Compare the last 2 agent runs from the database.

This script queries LLMCallLog entries to analyze iteration patterns
between different models (e.g., Gemini vs Llama 3.1B).
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
from sqlalchemy import desc, func
from src.database.schema import get_session, LLMCallLog


def get_recent_agent_runs(session, limit=2):
    """
    Get recent agent runs by grouping LLM calls that occurred close together.
    
    Groups calls within 5 minutes of each other as a single "run".
    Returns runs sorted by most recent.
    """
    # Get all recent LLM calls, ordered by time
    all_calls = (
        session.query(LLMCallLog)
        .order_by(desc(LLMCallLog.created_at))
        .limit(100)  # Get last 100 calls to find runs
        .all()
    )
    
    if not all_calls:
        return []
    
    # Group calls into runs (calls within 5 minutes belong to same run)
    runs = []
    current_run = []
    last_time = None
    
    for call in all_calls:
        if last_time is None:
            current_run = [call]
            last_time = call.created_at
        else:
            time_diff = (last_time - call.created_at).total_seconds()
            # If calls are more than 5 minutes apart, start new run
            if time_diff > 300:  # 5 minutes
                if current_run:
                    runs.append(current_run)
                current_run = [call]
            else:
                current_run.append(call)
            last_time = call.created_at
    
    # Add the last run
    if current_run:
        runs.append(current_run)
    
    # Sort runs by most recent (first call in each run)
    runs.sort(key=lambda r: r[0].created_at, reverse=True)
    
    return runs[:limit]


def analyze_run(run_calls):
    """Analyze a single run and return summary statistics."""
    if not run_calls:
        return None
    
    first_call = run_calls[0]
    last_call = run_calls[-1]
    
    # Count unique iterations by looking at time clusters
    # Each iteration typically involves 1-2 LLM calls (reasoning + possible structured output)
    # We'll estimate iterations by counting distinct "bursts" of calls
    
    # Group calls by minute to estimate iterations
    calls_by_minute = {}
    for call in run_calls:
        minute_key = call.created_at.replace(second=0, microsecond=0)
        if minute_key not in calls_by_minute:
            calls_by_minute[minute_key] = []
        calls_by_minute[minute_key].append(call)
    
    # Count total calls and tokens
    total_calls = len(run_calls)
    total_tokens = sum(c.total_tokens for c in run_calls)
    total_time = (last_call.created_at - first_call.created_at).total_seconds()
    
    # Estimate iterations (assuming 1-2 calls per iteration)
    estimated_iterations = max(1, total_calls // 2) if total_calls > 1 else total_calls
    
    return {
        "model_type": first_call.model_type,
        "model_name": first_call.model_name,
        "start_time": first_call.created_at,
        "end_time": last_call.created_at,
        "duration_seconds": total_time,
        "total_calls": total_calls,
        "total_tokens": total_tokens,
        "estimated_iterations": estimated_iterations,
        "calls_by_minute": len(calls_by_minute),
        "avg_tokens_per_call": total_tokens / total_calls if total_calls > 0 else 0,
    }


def main():
    """Main function to compare last 2 runs."""
    session = get_session()
    
    try:
        print("=" * 80)
        print("Comparing Last 2 Agent Runs")
        print("=" * 80)
        print()
        
        runs = get_recent_agent_runs(session, limit=2)
        
        if len(runs) < 2:
            print(f"⚠️  Only found {len(runs)} run(s) in the database.")
            print("   Need at least 2 runs to compare.")
            if runs:
                print("\n   Single run found:")
                analysis = analyze_run(runs[0])
                if analysis:
                    print(f"   Model: {analysis['model_name']} ({analysis['model_type']})")
                    print(f"   Estimated Iterations: {analysis['estimated_iterations']}")
                    print(f"   Total LLM Calls: {analysis['total_calls']}")
            return
        
        print(f"Found {len(runs)} recent runs")
        print()
        
        analyses = []
        for i, run in enumerate(runs, 1):
            analysis = analyze_run(run)
            if analysis:
                analyses.append(analysis)
                print(f"Run {i}:")
                print(f"  Model: {analysis['model_name']} ({analysis['model_type']})")
                print(f"  Time: {analysis['start_time']}")
                print(f"  Duration: {analysis['duration_seconds']:.2f} seconds")
                print(f"  Total LLM Calls: {analysis['total_calls']}")
                print(f"  Estimated Iterations: {analysis['estimated_iterations']}")
                print(f"  Total Tokens: {analysis['total_tokens']:,}")
                print(f"  Avg Tokens/Call: {analysis['avg_tokens_per_call']:.0f}")
                print()
        
        if len(analyses) == 2:
            print("=" * 80)
            print("Comparison:")
            print("=" * 80)
            print()
            
            run1, run2 = analyses[0], analyses[1]
            
            print(f"Model Comparison:")
            print(f"  Run 1: {run1['model_name']} ({run1['model_type']})")
            print(f"  Run 2: {run2['model_name']} ({run2['model_type']})")
            print()
            
            print(f"Iterations:")
            print(f"  Run 1: {run1['estimated_iterations']} iterations ({run1['total_calls']} LLM calls)")
            print(f"  Run 2: {run2['estimated_iterations']} iterations ({run2['total_calls']} LLM calls)")
            iter_diff = run2['estimated_iterations'] - run1['estimated_iterations']
            print(f"  Difference: {iter_diff:+d} iterations")
            print()
            
            print(f"Token Usage:")
            print(f"  Run 1: {run1['total_tokens']:,} tokens")
            print(f"  Run 2: {run2['total_tokens']:,} tokens")
            token_diff = run2['total_tokens'] - run1['total_tokens']
            print(f"  Difference: {token_diff:+,} tokens")
            print()
            
            print(f"Duration:")
            print(f"  Run 1: {run1['duration_seconds']:.2f} seconds")
            print(f"  Run 2: {run2['duration_seconds']:.2f} seconds")
            time_diff = run2['duration_seconds'] - run1['duration_seconds']
            print(f"  Difference: {time_diff:+.2f} seconds")
            print()
            
            # Show which model iterated more
            if run1['estimated_iterations'] > run2['estimated_iterations']:
                print(f"✅ {run1['model_name']} used MORE iterations ({run1['estimated_iterations']} vs {run2['estimated_iterations']})")
            elif run2['estimated_iterations'] > run1['estimated_iterations']:
                print(f"✅ {run2['model_name']} used MORE iterations ({run2['estimated_iterations']} vs {run1['estimated_iterations']})")
            else:
                print(f"✅ Both models used the same number of iterations ({run1['estimated_iterations']})")
        
    finally:
        session.close()


if __name__ == "__main__":
    main()



