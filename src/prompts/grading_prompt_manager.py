"""
Grading Prompt Manager for versioning LLM output validation prompts.

Educational: Similar to agent prompts, grading prompts also evolve over time.
This manager tracks different versions of grading prompts to ensure consistency
in how we evaluate model outputs across different test runs.
"""

from typing import Optional
from sqlalchemy.orm import Session
from src.database.schema import GradingPromptVersion, get_session


# Default grading prompt template (v1.0)
DEFAULT_GRADING_PROMPT_TEMPLATE = """You are grading the accuracy of a data field extracted by an LLM.

Field name: {field_name}
Correct value (from Gemini Pro): {correct_value}
Actual value (to grade): {actual_value}

Rate the accuracy and provide structured output:

1. Score (0-100):
   - Exact matches = 100%
   - Close/similar meanings = 70-99%
   - Related but different = 40-69%
   - Partially correct = 20-39%
   - Completely wrong or missing = 0-19%

2. Match type: exact | semantic | partial | none
   - exact: Identical values (case-insensitive, whitespace normalized)
   - semantic: Different wording but same meaning (e.g., "SaaS" vs "Software as a Service")
   - partial: Some overlap but not equivalent (e.g., "SaaS" vs "Cloud Software")
   - none: Completely different or missing

3. Brief explanation: Why this score? What's the difference?

4. Confidence (0-1): How confident are you in this grading?
   - 1.0: Very confident (clear match/mismatch)
   - 0.7-0.9: Mostly confident (some ambiguity)
   - 0.5-0.6: Uncertain (borderline case)
   - <0.5: Low confidence (needs human review)

Respond in this exact format (no additional text):
SCORE: <number>
MATCH_TYPE: <exact|semantic|partial|none>
CONFIDENCE: <0.0-1.0>
EXPLANATION: <brief explanation>"""

DEFAULT_GRADING_RUBRIC = """Scoring Rubric:
- 100% (exact): Values are identical or equivalent after normalization
- 70-99% (semantic): Different wording but same meaning/concept
- 40-69% (partial): Related concepts with some overlap but not equivalent
- 20-39% (partial): Some connection but significant differences
- 0-19% (none): Completely different concepts or missing value

Match Types:
- exact: Identical values (normalized)
- semantic: Same meaning, different wording
- partial: Some overlap but not equivalent
- none: Completely different or missing"""


class GradingPromptManager:
    """
    Manages grading prompt versions in the database.
    
    Educational: Similar to agent prompts, grading prompts also evolve over time.
    This manager tracks different versions of grading prompts to ensure consistency
    in how we evaluate model outputs across different test runs.
    """
    
    @staticmethod
    def create_version(
        version: str,
        prompt_template: str,
        scoring_rubric: Optional[str] = None,
        description: Optional[str] = None,
        is_active: bool = True,
        session: Optional[Session] = None,
    ) -> GradingPromptVersion:
        """
        Create a new grading prompt version.
        
        Educational: This demonstrates how to version grading prompts separately
        from agent prompts. Grading prompt versioning is important because
        changes to grading criteria can affect accuracy scores, so we need to
        track which grading prompt was used for each test run.
        
        Args:
            version: Version string (e.g., "1.0", "1.1")
            prompt_template: Template string with placeholders (e.g., {field_name})
            scoring_rubric: Optional detailed scoring rules text
            description: Optional description of changes in this version
            is_active: Whether this version is currently active
            session: Optional database session (creates new if not provided)
            
        Returns:
            Created GradingPromptVersion object
            
        Raises:
            ValueError: If grading prompt version already exists
        """
        db_session = session or get_session()
        try:
            # Check if version already exists
            existing = (
                db_session.query(GradingPromptVersion)
                .filter(GradingPromptVersion.version == version)
                .first()
            )
            if existing:
                raise ValueError(f"Grading prompt version {version} already exists")
            
            grading_prompt_version = GradingPromptVersion(
                version=version,
                prompt_template=prompt_template,
                scoring_rubric=scoring_rubric,
                description=description,
                is_active=is_active,
            )
            
            db_session.add(grading_prompt_version)
            db_session.commit()
            return grading_prompt_version
            
        finally:
            if not session:
                db_session.close()
    
    @staticmethod
    def get_active_version(
        session: Optional[Session] = None,
    ) -> Optional[GradingPromptVersion]:
        """
        Get the active grading prompt version.
        
        Educational: This retrieves the currently active grading prompt,
        which is typically the one used for new test runs.
        
        Args:
            session: Optional database session
            
        Returns:
            GradingPromptVersion object if found, None otherwise
        """
        db_session = session or get_session()
        try:
            return (
                db_session.query(GradingPromptVersion)
                .filter(GradingPromptVersion.is_active == True)
                .order_by(GradingPromptVersion.created_at.desc())
                .first()
            )
        finally:
            if not session:
                db_session.close()
    
    @staticmethod
    def get_version(
        version: str,
        session: Optional[Session] = None,
    ) -> Optional[GradingPromptVersion]:
        """
        Get a specific grading prompt version.
        
        Educational: This enables retrieving specific grading prompt versions
        for comparison or historical analysis.
        
        Args:
            version: Version string to retrieve
            session: Optional database session
            
        Returns:
            GradingPromptVersion object if found, None otherwise
        """
        db_session = session or get_session()
        try:
            return (
                db_session.query(GradingPromptVersion)
                .filter(GradingPromptVersion.version == version)
                .first()
            )
        finally:
            if not session:
                db_session.close()
    
    @staticmethod
    def get_version_by_id(
        version_id: int,
        session: Optional[Session] = None,
    ) -> Optional[GradingPromptVersion]:
        """
        Get a grading prompt version by ID.
        
        Useful when you have the database ID (e.g., from a foreign key reference).
        
        Args:
            version_id: Database ID of the grading prompt version
            session: Optional database session
            
        Returns:
            GradingPromptVersion object if found, None otherwise
        """
        db_session = session or get_session()
        try:
            return (
                db_session.query(GradingPromptVersion)
                .filter(GradingPromptVersion.id == version_id)
                .first()
            )
        finally:
            if not session:
                db_session.close()
    
    @staticmethod
    def create_default_version(
        session: Optional[Session] = None,
    ) -> GradingPromptVersion:
        """
        Create the default grading prompt version (v1.0).
        
        Educational: This creates the initial grading prompt with a clear
        scoring rubric. This is typically called once during setup to
        initialize the grading system.
        
        Args:
            session: Optional database session
            
        Returns:
            Created GradingPromptVersion object (v1.0)
            
        Raises:
            ValueError: If v1.0 already exists
        """
        return GradingPromptManager.create_version(
            version="1.0",
            prompt_template=DEFAULT_GRADING_PROMPT_TEMPLATE,
            scoring_rubric=DEFAULT_GRADING_RUBRIC,
            description="Initial grading prompt with clear scoring rubric",
            is_active=True,
            session=session,
        )

