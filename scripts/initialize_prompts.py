#!/usr/bin/env python3
"""
Script to initialize prompts from files into the database.

Educational: This script demonstrates how to load prompts from markdown files
and store them as versioned entries in the database. This enables prompt
versioning and tracking for prompt engineering experiments.

Usage:
    python scripts/initialize_prompts.py \\
        --prompt prompts/research-agent-prompt.md \\
        --version 1.0 \\
        --description "Initial version" \\
        --created-by "System"
    
    python scripts/initialize_prompts.py \\
        --grading-prompt \\
        --version 1.0
"""

import argparse
from pathlib import Path
from src.prompts.prompt_manager import PromptManager
from src.prompts.grading_prompt_manager import GradingPromptManager, DEFAULT_GRADING_PROMPT_TEMPLATE, DEFAULT_GRADING_RUBRIC
from src.database.schema import create_database, get_session


def initialize_agent_prompt(
    prompt_path: Path,
    prompt_name: str,
    version: str,
    description: str,
    created_by: str,
) -> None:
    """Initialize an agent prompt from a markdown file."""
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    print(f"Loading prompt from: {prompt_path}")
    print(f"Prompt name: {prompt_name}")
    print(f"Version: {version}")
    
    session = get_session()
    try:
        prompt_version = PromptManager.create_version_from_file(
            prompt_name=prompt_name,
            prompt_path=prompt_path,
            version=version,
            description=description,
            created_by=created_by,
            session=session,
        )
        
        # Access all attributes while session is still open
        pv_name = prompt_version.prompt_name
        pv_version = prompt_version.version
        pv_id = prompt_version.id
        instructions_len = len(prompt_version.instructions_content)
        classification_len = len(prompt_version.classification_reference_content or '')
        
        print(f"✅ Created prompt version: {pv_name}@{pv_version}")
        print(f"   ID: {pv_id}")
        print(f"   Instructions length: {instructions_len} chars")
        print(f"   Classification reference length: {classification_len} chars")
    finally:
        session.close()


def initialize_grading_prompt(
    version: str,
    prompt_template: str = None,
    scoring_rubric: str = None,
    description: str = None,
) -> None:
    """Initialize a grading prompt version."""
    if prompt_template is None:
        prompt_template = DEFAULT_GRADING_PROMPT_TEMPLATE
    if scoring_rubric is None:
        scoring_rubric = DEFAULT_GRADING_RUBRIC
    if description is None:
        description = "Initial grading prompt with clear scoring rubric"
    
    print(f"Creating grading prompt version: {version}")
    
    session = get_session()
    try:
        grading_prompt_version = GradingPromptManager.create_version(
            version=version,
            prompt_template=prompt_template,
            scoring_rubric=scoring_rubric,
            description=description,
            session=session,
        )
        
        # Access all attributes while session is still open
        gpv_version = grading_prompt_version.version
        gpv_id = grading_prompt_version.id
        template_len = len(grading_prompt_version.prompt_template)
        
        print(f"✅ Created grading prompt version: {gpv_version}")
        print(f"   ID: {gpv_id}")
        print(f"   Template length: {template_len} chars")
    finally:
        session.close()


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Initialize prompts from files into the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize agent prompt from file
  python scripts/initialize_prompts.py \\
      --prompt prompts/research-agent-prompt.md \\
      --prompt-name research-agent-prompt \\
      --version 1.0 \\
      --description "Initial version" \\
      --created-by "System"
  
  # Initialize grading prompt (default v1.0)
  python scripts/initialize_prompts.py \\
      --grading-prompt \\
      --version 1.0
        """
    )
    
    # Agent prompt options
    parser.add_argument(
        "--prompt",
        type=Path,
        help="Path to agent prompt markdown file"
    )
    parser.add_argument(
        "--prompt-name",
        default="research-agent-prompt",
        help="Name identifier for the prompt (default: research-agent-prompt)"
    )
    
    # Grading prompt option
    parser.add_argument(
        "--grading-prompt",
        action="store_true",
        help="Initialize grading prompt instead of agent prompt"
    )
    
    # Common options
    parser.add_argument(
        "--version",
        required=True,
        help="Version string (e.g., '1.0', '1.1')"
    )
    parser.add_argument(
        "--description",
        help="Description of changes in this version"
    )
    parser.add_argument(
        "--created-by",
        default="System",
        help="User/author who created this version (default: System)"
    )
    
    args = parser.parse_args()
    
    # Ensure database is created
    print("Creating/verifying database...")
    create_database()
    print()
    
    try:
        if args.grading_prompt:
            # Initialize grading prompt
            initialize_grading_prompt(
                version=args.version,
                description=args.description,
            )
        else:
            # Initialize agent prompt
            if not args.prompt:
                parser.error("--prompt is required when not using --grading-prompt")
            
            initialize_agent_prompt(
                prompt_path=args.prompt,
                prompt_name=args.prompt_name,
                version=args.version,
                description=args.description or f"Version {args.version}",
                created_by=args.created_by,
            )
        
        print("\n✅ Prompt initialization complete!")
        
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("   (Version may already exist)")
        return 1
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

