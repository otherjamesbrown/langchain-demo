#!/usr/bin/env python3
"""
Script to toggle LangSmith tracing on/off via database.

This script allows you to enable or disable LangSmith tracing by updating
the setting in the database. The setting is stored in the app_settings table
and takes effect immediately for new LLM calls.

Usage:
    # Enable tracing
    python scripts/toggle_langsmith_tracing.py --enable
    
    # Disable tracing
    python scripts/toggle_langsmith_tracing.py --disable
    
    # Check current status
    python scripts/toggle_langsmith_tracing.py --status
"""

import sys
import argparse
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.monitoring import (
    get_langsmith_tracing_enabled,
    set_langsmith_tracing_enabled,
    configure_langsmith_tracing
)


def main():
    parser = argparse.ArgumentParser(
        description="Toggle LangSmith tracing on/off via database"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--enable", action="store_true", help="Enable LangSmith tracing")
    group.add_argument("--disable", action="store_true", help="Disable LangSmith tracing")
    group.add_argument("--status", action="store_true", help="Check current tracing status")
    
    args = parser.parse_args()
    
    if args.status:
        # Check current status
        enabled = get_langsmith_tracing_enabled()
        api_key = bool(__import__("os").getenv("LANGCHAIN_API_KEY"))
        
        print("\n" + "="*60)
        print("LangSmith Tracing Status")
        print("="*60)
        print(f"Tracing Enabled: {'✅ YES' if enabled else '❌ NO'}")
        print(f"API Key Set: {'✅ YES' if api_key else '❌ NO'}")
        
        if enabled and api_key:
            print("\n✅ LangSmith tracing is active")
            print("   Traces will be sent to LangSmith dashboard")
        elif not api_key:
            print("\n⚠️  LANGCHAIN_API_KEY not set")
            print("   Set it in .env file to enable tracing")
        else:
            print("\n⚠️  Tracing is disabled in database")
            print("   Run with --enable to turn it on")
        print("="*60)
        
        return 0
    
    elif args.enable:
        # Enable tracing
        print("\nEnabling LangSmith tracing...")
        set_langsmith_tracing_enabled(True)
        
        # Verify configuration
        configure_langsmith_tracing(verbose=True)
        
        print("\n✅ LangSmith tracing has been ENABLED")
        print("   New LLM calls will be traced to LangSmith")
        print("   Check your LangSmith dashboard for traces")
        
        return 0
    
    elif args.disable:
        # Disable tracing
        print("\nDisabling LangSmith tracing...")
        set_langsmith_tracing_enabled(False)
        
        print("\n✅ LangSmith tracing has been DISABLED")
        print("   New LLM calls will NOT be traced")
        print("   (Existing traces in LangSmith are not affected)")
        
        return 0


if __name__ == "__main__":
    sys.exit(main())

