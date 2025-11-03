"""
Prompt Manager for versioning research agent prompts.

Educational: This demonstrates how to version prompts for A/B testing and
tracking prompt engineering experiments. Each prompt can have multiple versions,
allowing comparison of accuracy across different prompt iterations.
"""

from typing import Optional, List, Dict, Any
from pathlib import Path
from sqlalchemy.orm import Session
from src.database.schema import PromptVersion, get_session


class PromptManager:
    """
    Manages prompt versions in the database.
    
    Educational: This shows how to version prompts for A/B testing and
    tracking prompt engineering experiments. Each prompt can have multiple versions,
    allowing comparison of accuracy across different prompt iterations.
    """
    
    @staticmethod
    def load_prompt_from_file(prompt_path: Path) -> Dict[str, str]:
        """
        Load prompt sections from markdown file.
        
        Parses the markdown file to extract:
        - RESEARCH INSTRUCTIONS section (main instruction content)
        - CLASSIFICATION REFERENCE section (classification guide)
        - Full content (complete file for reference)
        
        Educational: This shows how to parse structured markdown files
        where sections are marked by headers. The extraction logic handles
        cases where sections might not exist (fallback to full content).
        
        Args:
            prompt_path: Path to the markdown prompt file
            
        Returns:
            Dict with keys: 'instructions', 'classification_reference', 'full_content'
            
        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
        content = prompt_path.read_text(encoding="utf-8").strip()
        
        # Extract RESEARCH INSTRUCTIONS section
        instructions = ""
        if "# RESEARCH INSTRUCTIONS" in content:
            parts = content.split("# RESEARCH INSTRUCTIONS", 1)
            if len(parts) > 1:
                # Extract everything until next major section
                instructions = parts[1].split("# CLASSIFICATION REFERENCE", 1)[0].strip()
        
        # Extract CLASSIFICATION REFERENCE section
        classification_ref = ""
        if "# CLASSIFICATION REFERENCE" in content:
            parts = content.split("# CLASSIFICATION REFERENCE", 1)
            if len(parts) > 1:
                # Stop at next major section (DETAILED CLASSIFICATION DEFINITIONS or end)
                classification_ref = parts[1].split("# DETAILED CLASSIFICATION DEFINITIONS", 1)[0].strip()
        
        return {
            "instructions": instructions or content,  # Fallback to full content if no section found
            "classification_reference": classification_ref,
            "full_content": content,
        }
    
    @staticmethod
    def create_version_from_file(
        prompt_name: str,
        prompt_path: Path,
        version: str,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> PromptVersion:
        """
        Create a new prompt version from a file.
        
        Educational: This demonstrates how to create versioned prompts from files.
        The version is stored in the database with all metadata, enabling
        historical tracking and comparison of prompt changes.
        
        Args:
            prompt_name: Name identifier for the prompt (e.g., "research-agent-prompt")
            prompt_path: Path to the markdown prompt file
            version: Version string (e.g., "1.0", "1.1", "v2-base")
            description: Optional description of changes in this version
            created_by: Optional user/author identifier
            session: Optional database session (creates new if not provided)
            
        Returns:
            Created PromptVersion object
            
        Raises:
            FileNotFoundError: If prompt file doesn't exist
            ValueError: If prompt version already exists
        """
        sections = PromptManager.load_prompt_from_file(prompt_path)
        
        db_session = session or get_session()
        try:
            # Check if version already exists
            existing = (
                db_session.query(PromptVersion)
                .filter(
                    PromptVersion.prompt_name == prompt_name,
                    PromptVersion.version == version,
                )
                .first()
            )
            if existing:
                raise ValueError(f"Prompt version {prompt_name}@{version} already exists")
            
            prompt_version = PromptVersion(
                prompt_name=prompt_name,
                version=version,
                instructions_content=sections["instructions"],
                classification_reference_content=sections["classification_reference"],
                full_content=sections["full_content"],
                description=description,
                created_by=created_by,
                is_active=True,
            )
            
            db_session.add(prompt_version)
            db_session.commit()
            return prompt_version
            
        finally:
            if not session:
                db_session.close()
    
    @staticmethod
    def get_active_version(
        prompt_name: str,
        session: Optional[Session] = None,
    ) -> Optional[PromptVersion]:
        """
        Get the active version of a prompt.
        
        Educational: This shows how to retrieve the currently active prompt version.
        The active version is the most recently created version marked as active,
        which is typically the one used in production.
        
        Args:
            prompt_name: Name identifier for the prompt
            session: Optional database session
            
        Returns:
            PromptVersion object if found, None otherwise
        """
        db_session = session or get_session()
        try:
            return (
                db_session.query(PromptVersion)
                .filter(
                    PromptVersion.prompt_name == prompt_name,
                    PromptVersion.is_active == True,
                )
                .order_by(PromptVersion.created_at.desc())
                .first()
            )
        finally:
            if not session:
                db_session.close()
    
    @staticmethod
    def get_version(
        prompt_name: str,
        version: str,
        session: Optional[Session] = None,
    ) -> Optional[PromptVersion]:
        """
        Get a specific version of a prompt.
        
        Educational: This enables retrieving specific prompt versions for
        testing or comparison. Useful for A/B testing different prompt versions.
        
        Args:
            prompt_name: Name identifier for the prompt
            version: Version string to retrieve
            session: Optional database session
            
        Returns:
            PromptVersion object if found, None otherwise
        """
        db_session = session or get_session()
        try:
            return (
                db_session.query(PromptVersion)
                .filter(
                    PromptVersion.prompt_name == prompt_name,
                    PromptVersion.version == version,
                )
                .first()
            )
        finally:
            if not session:
                db_session.close()
    
    @staticmethod
    def get_version_by_id(
        version_id: int,
        session: Optional[Session] = None,
    ) -> Optional[PromptVersion]:
        """
        Get a prompt version by ID.
        
        Useful when you have the database ID (e.g., from a foreign key reference).
        
        Args:
            version_id: Database ID of the prompt version
            session: Optional database session
            
        Returns:
            PromptVersion object if found, None otherwise
        """
        db_session = session or get_session()
        try:
            return db_session.query(PromptVersion).filter(PromptVersion.id == version_id).first()
        finally:
            if not session:
                db_session.close()
    
    @staticmethod
    def list_versions(
        prompt_name: str,
        session: Optional[Session] = None,
    ) -> List[PromptVersion]:
        """
        List all versions of a prompt.
        
        Educational: This enables seeing the full history of prompt versions,
        useful for understanding how prompts evolved over time.
        
        Args:
            prompt_name: Name identifier for the prompt
            session: Optional database session
            
        Returns:
            List of PromptVersion objects, ordered by creation date (newest first)
        """
        db_session = session or get_session()
        try:
            return (
                db_session.query(PromptVersion)
                .filter(PromptVersion.prompt_name == prompt_name)
                .order_by(PromptVersion.created_at.desc())
                .all()
            )
        finally:
            if not session:
                db_session.close()

