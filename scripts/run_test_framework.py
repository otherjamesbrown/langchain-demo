#!/usr/bin/env python3
"""
Unified test framework CLI runner.

This script runs research agent tests across multiple models using the
testing framework. It supports filtering by model provider, different
output formats, and customizable test parameters.

⚠️ IMPORTANT: This script MUST be run on the remote server where LangChain
and all dependencies are installed.

Usage:
    # Run BitMovin test across all available models
    python scripts/run_test_framework.py --test bitmovin
    
    # Run only Gemini and OpenAI models
    python scripts/run_test_framework.py --test bitmovin --models gemini openai
    
    # Output as JSON for programmatic use
    python scripts/run_test_framework.py --test bitmovin --output json
    
    # Custom max iterations and verbose mode
    python scripts/run_test_framework.py --test bitmovin --max-iterations 15 --verbose
    
    # List available tests
    python scripts/run_test_framework.py --list-tests
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
import json
from typing import List, Dict, Any, Optional

from src.testing.test_runner import TestRunner
from src.testing.baselines import get_baseline, list_baselines
from src.database.operations import (
    get_model_configurations,
    get_api_key,
    ensure_default_configuration,
)
from src.database.schema import get_session, create_database


def check_package_installed(package_name: str) -> bool:
    """Check if a Python package is installed."""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False


def check_provider_packages_installed(provider: str) -> bool:
    """Check if required packages are installed for a provider."""
    package_map = {
        "local": "llama_cpp",
        "openai": "langchain_openai",
        "anthropic": "langchain_anthropic",
        "gemini": "langchain_google_genai",
    }
    
    required_package = package_map.get(provider)
    if not required_package:
        return False
    
    # For langchain packages, check both the langchain package and underlying package
    if provider == "openai":
        return check_package_installed("langchain_openai") or check_package_installed("openai")
    elif provider == "anthropic":
        return check_package_installed("langchain_anthropic") or check_package_installed("anthropic")
    elif provider == "gemini":
        return check_package_installed("langchain_google_genai") or check_package_installed("google.generativeai")
    elif provider == "local":
        return check_package_installed("llama_cpp") or check_package_installed("llama_cpp_python")
    
    return False


def get_available_models(
    provider_filter: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Get available model configurations from database.
    
    Educational: This function queries the database for model configurations
    and validates that they're actually usable (packages installed, model files
    exist for local models, API keys exist for remote models).
    
    Args:
        provider_filter: Optional list of provider names to filter by
        
    Returns:
        List of model configuration dicts ready for TestRunner
    """
    try:
        # Ensure database is initialized and has default configurations
        create_database()
        session = get_session()
        try:
            # Sync default configurations from code registry and env vars
            ensure_default_configuration(session=session)
            session.commit()
            
            # Get all active model configurations
            model_configs = get_model_configurations(session=session)
            
            available_models = []
            for config in model_configs:
                # Apply provider filter if specified
                if provider_filter and config.provider not in provider_filter:
                    continue
                
                # First check if required packages are installed
                if not check_provider_packages_installed(config.provider):
                    print(f"⚠️  Skipping {config.name}: Required packages not installed for {config.provider}", 
                          file=sys.stderr)
                    continue
                
                # Check if model is usable
                is_usable = False
                reason = ""
                
                if config.provider == "local":
                    # Check if model file exists
                    if config.model_path:
                        if os.path.exists(config.model_path):
                            is_usable = True
                        else:
                            # Try expanding path
                            expanded_path = os.path.expanduser(config.model_path)
                            if os.path.exists(expanded_path):
                                is_usable = True
                            else:
                                reason = f"Model file not found: {config.model_path}"
                    else:
                        reason = "No model_path configured"
                else:
                    # For remote models, check if API key is available in database
                    api_key = get_api_key(config.provider, session=session)
                    if api_key and api_key.strip():
                        is_usable = True
                    else:
                        reason = f"API key not found in database for {config.provider}"
                
                if is_usable:
                    model_dict = {
                        "name": config.name,
                        "provider": config.provider,
                        "config_id": config.id,
                    }
                    
                    if config.provider == "local":
                        model_dict["model_path"] = config.model_path
                        if config.model_key:
                            model_dict["model_key"] = config.model_key
                    else:
                        if config.api_identifier:
                            model_dict["api_identifier"] = config.api_identifier
                    
                    available_models.append(model_dict)
                else:
                    print(f"⚠️  Skipping {config.name}: {reason}", file=sys.stderr)
            
            return available_models
        finally:
            session.close()
    except Exception as e:
        print(f"❌ Error querying database: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return []


def format_results(result, output_format: str = "text") -> str:
    """
    Format test results for display.
    
    Educational: This function demonstrates how to format structured test
    results for both human-readable (text) and machine-readable (JSON)
    output formats.
    """
    if output_format == "json":
        # JSON output for programmatic use
        output = {
            "test_name": result.test_name,
            "average_score": result.average_score,
            "best_model": result.best_model,
            "execution_time": result.execution_time,
            "baseline": {
                "company_name": result.baseline.company_name,
                "description": result.baseline.description,
            },
            "model_results": [
                {
                    "model_name": mr.model_name,
                    "provider": mr.model_provider,
                    "success": mr.success,
                    "overall_score": mr.overall_score,
                    "required_fields_score": mr.required_fields_score,
                    "optional_fields_score": mr.optional_fields_score,
                    "execution_time": mr.execution_time,
                    "iterations": mr.iterations,
                    "error_message": mr.error_message,
                    "field_results": {
                        field_name: {
                            "is_match": fr.is_match,
                            "confidence": fr.confidence,
                            "expected_value": str(fr.expected_value),
                            "actual_value": str(fr.actual_value) if fr.actual_value is not None else None,
                            "error_message": fr.error_message,
                            "match_type": fr.match_type,
                        }
                        for field_name, fr in mr.field_results.items()
                    },
                }
                for mr in result.model_results
            ]
        }
        return json.dumps(output, indent=2)
    else:
        # Text output for human reading
        lines = [
            "=" * 70,
            f"Test: {result.test_name}",
            f"Company: {result.baseline.company_name}",
            "=" * 70,
            "",
            f"Average Score: {result.average_score:.2%}",
            f"Best Model: {result.best_model}",
            f"Total Execution Time: {result.execution_time:.2f}s",
            "",
            "Model Results:",
            "",
        ]
        
        for mr in result.model_results:
            status = "✅" if mr.success else "❌"
            lines.extend([
                f"  {status} {mr.model_name} ({mr.model_provider})",
                f"    Overall Score: {mr.overall_score:.2%}",
                f"    Required Fields: {mr.required_fields_score:.2%}",
                f"    Optional Fields: {mr.optional_fields_score:.2%}",
                f"    Execution Time: {mr.execution_time:.2f}s",
                f"    Iterations: {mr.iterations}",
            ])
            
            if mr.error_message:
                lines.append(f"    Error: {mr.error_message}")
            
            # Show field-level results for failed fields or low confidence
            failed_fields = [
                (field_name, fr) for field_name, fr in mr.field_results.items()
                if not fr.is_match or fr.confidence < 0.8
            ]
            
            if failed_fields:
                lines.append("    Field Issues:")
                for field_name, fr in failed_fields[:5]:  # Show first 5 issues
                    match_status = "✅" if fr.is_match else "❌"
                    lines.append(
                        f"      {match_status} {field_name}: "
                        f"{fr.confidence:.0%} confidence "
                        f"(expected: {fr.expected_value}, got: {fr.actual_value})"
                    )
                if len(failed_fields) > 5:
                    lines.append(f"      ... and {len(failed_fields) - 5} more issues")
            
            lines.append("")
        
        return "\n".join(lines)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run test framework for research agent validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run BitMovin test across all models
  python scripts/run_test_framework.py --test bitmovin
  
  # Run only Gemini and OpenAI
  python scripts/run_test_framework.py --test bitmovin --models gemini openai
  
  # Output as JSON
  python scripts/run_test_framework.py --test bitmovin --output json
  
  # Verbose mode with custom iterations
  python scripts/run_test_framework.py --test bitmovin --verbose --max-iterations 15
  
  # List available tests
  python scripts/run_test_framework.py --list-tests
        """
    )
    
    parser.add_argument(
        "--test",
        help="Test name (e.g., 'bitmovin'). Use --list-tests to see available tests."
    )
    parser.add_argument(
        "--models",
        nargs="+",
        help="Filter to specific model providers (e.g., gemini openai anthropic local)"
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=10,
        help="Maximum agent iterations (default: 10)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging from research agent"
    )
    parser.add_argument(
        "--list-tests",
        action="store_true",
        help="List all available test baselines"
    )
    
    args = parser.parse_args()
    
    # Handle list-tests flag
    if args.list_tests:
        tests = list_baselines()
        print("Available tests:")
        for test_name in tests:
            try:
                baseline = get_baseline(test_name)
                print(f"  - {test_name}: {baseline.description}")
            except Exception as e:
                print(f"  - {test_name}: (error loading: {e})")
        return 0
    
    # Validate test argument
    if not args.test:
        parser.error("--test is required (use --list-tests to see available tests)")
    
    # Get baseline
    try:
        baseline = get_baseline(args.test)
        print(f"📋 Loaded test: {baseline.test_name}")
        print(f"   Company: {baseline.company_name}")
        print(f"   Description: {baseline.description}")
        print(f"   Required fields: {len(baseline.required_fields)}")
        print(f"   Optional fields: {len(baseline.optional_fields)}")
    except ValueError as e:
        print(f"❌ Error loading baseline: {e}", file=sys.stderr)
        print(f"\nAvailable tests:", file=sys.stderr)
        for test_name in list_baselines():
            print(f"  - {test_name}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error loading baseline: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    
    # Get available models
    print(f"\n🔍 Searching for available models...")
    models = get_available_models(provider_filter=args.models)
    
    if not models:
        print("❌ No models available for testing", file=sys.stderr)
        if args.models:
            print(f"   Filtered by providers: {args.models}", file=sys.stderr)
        print("\n💡 Tips:", file=sys.stderr)
        print("   - Ensure database is initialized and models are configured", file=sys.stderr)
        print("   - For local models: check that model files exist", file=sys.stderr)
        print("   - For remote models: check that API keys are set in database", file=sys.stderr)
        return 1
    
    print(f"✅ Found {len(models)} available model(s):")
    for model in models:
        print(f"   - {model['name']} ({model['provider']})")
    
    # Run test
    print(f"\n🚀 Running test across {len(models)} model(s)...")
    print(f"   Max iterations: {args.max_iterations}")
    print(f"   Verbose: {args.verbose}")
    print("")
    
    try:
        runner = TestRunner(model_configs=models)
        result = runner.run_test(
            baseline=baseline,
            max_iterations=args.max_iterations,
            verbose=args.verbose,
        )
        
        # Output results
        print(format_results(result, args.output))
        
        # Exit code based on results
        successful_models = sum(1 for mr in result.model_results if mr.success)
        if successful_models == len(result.model_results):
            return 0
        elif successful_models > 0:
            return 0  # Partial success is still OK
        else:
            return 1  # All models failed
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\n❌ Unexpected error during test execution: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

