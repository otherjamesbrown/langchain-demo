#!/usr/bin/env python3
"""
Test Llama Diagnostics

Quick test script to run the research agent with diagnostic logging enabled.
This helps identify truncation issues with local Llama models.

Usage:
    python scripts/test_llama_diagnostics.py [company_name]

Examples:
    python scripts/test_llama_diagnostics.py BitMovin
    python scripts/test_llama_diagnostics.py "Queue-it"
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
from src.agent.research_agent import ResearchAgent
from src.database.operations import get_default_model_configuration, get_session


def main():
    """Run diagnostic test for Llama truncation issue."""
    
    parser = argparse.ArgumentParser(
        description="Test research agent with diagnostic logging"
    )
    parser.add_argument(
        "company_name",
        nargs="?",
        default="BitMovin",
        help="Company name to research (default: BitMovin)"
    )
    parser.add_argument(
        "--model-path",
        help="Path to local model file (optional, uses database default if not provided)"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Maximum agent iterations (default: 5)"
    )
    parser.add_argument(
        "--no-diagnostics",
        action="store_true",
        help="Disable diagnostic logging (for comparison)"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🔍 LLAMA DIAGNOSTIC TEST")
    print("=" * 80)
    print(f"Company: {args.company_name}")
    print(f"Max Iterations: {args.max_iterations}")
    print(f"Diagnostics: {'DISABLED' if args.no_diagnostics else 'ENABLED'}")
    print("=" * 80)
    print()
    
    # Get model configuration from database
    model_kwargs = {}
    local_model_key = None
    model_path = args.model_path
    
    if not model_path:
        try:
            session = get_session()
            db_model = get_default_model_configuration(session=session)
            session.close()
            
            if db_model and db_model.provider == "local":
                model_path = db_model.model_path
                local_model_key = db_model.model_key
                
                # Extract metadata
                metadata = db_model.extra_metadata or {}
                context_window = metadata.get("context_window")
                if context_window:
                    max_output_tokens = max(int(context_window) // 2, 512)
                    model_kwargs["max_tokens"] = max_output_tokens
                    print(f"📊 Using database model configuration:")
                    print(f"   Model: {db_model.name}")
                    print(f"   Path: {model_path}")
                    print(f"   Context Window: {context_window}")
                    print(f"   Max Output Tokens: {max_output_tokens}")
                    print()
        except Exception as e:
            print(f"⚠️  Warning: Could not load model from database: {e}")
            print("Using environment variables or defaults instead.")
            print()
    
    # Initialize agent with diagnostics enabled
    try:
        agent = ResearchAgent(
            model_type="local",
            verbose=True,
            max_iterations=args.max_iterations,
            local_model=local_model_key,
            model_path=model_path,
            model_kwargs=model_kwargs,
            enable_diagnostics=not args.no_diagnostics,
        )
        
        print(f"✅ Agent initialized successfully")
        print(f"   Model: {agent._model_display_name}")
        if agent._resolved_model_path:
            print(f"   Path: {agent._resolved_model_path}")
        print()
        
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        return 1
    
    # Run research
    print("🚀 Starting research...")
    print("=" * 80)
    print()
    
    try:
        result = agent.research_company(args.company_name)
        
        print()
        print("=" * 80)
        print("📊 RESEARCH RESULT")
        print("=" * 80)
        print(f"Success: {result.success}")
        print(f"Iterations: {result.iterations}")
        print(f"Execution Time: {result.execution_time_seconds:.2f}s")
        print()
        
        if result.raw_output:
            print("📝 Raw Output:")
            print("-" * 80)
            print(result.raw_output)
            print("-" * 80)
            print()
        
        if result.company_info:
            print("✅ Parsed Company Info:")
            print(f"   Name: {result.company_info.company_name}")
            print(f"   Industry: {result.company_info.industry}")
            print(f"   Size: {result.company_info.company_size}")
            print(f"   HQ: {result.company_info.headquarters}")
            print(f"   Products: {len(result.company_info.products)} listed")
            print(f"   Competitors: {len(result.company_info.competitors)} listed")
            print()
        else:
            print("❌ Failed to parse company info")
            print()
        
        # Check for truncation
        if result.raw_output:
            last_char = result.raw_output.rstrip()[-1] if result.raw_output.rstrip() else ""
            if last_char.isalpha():
                print("⚠️  WARNING: Output appears truncated (ends mid-word)")
            elif last_char not in (".", "!", "?", "}", "]", ")"):
                print("⚠️  WARNING: Output may be truncated (no proper ending)")
        
        print("=" * 80)
        
        return 0 if result.success else 1
        
    except Exception as e:
        print()
        print("=" * 80)
        print(f"❌ ERROR: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

