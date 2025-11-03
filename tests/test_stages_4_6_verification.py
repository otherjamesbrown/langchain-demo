"""
Verification scripts for Stages 4-6 of testing framework implementation.

These tests verify that the prompt management system works correctly:
- Stage 4: PromptManager class with CRUD operations
- Stage 5: GradingPromptManager class
- Stage 6: Initialize prompts script
"""

import pytest
from pathlib import Path
from src.prompts.prompt_manager import PromptManager
from src.prompts.grading_prompt_manager import (
    GradingPromptManager,
    DEFAULT_GRADING_PROMPT_TEMPLATE,
    DEFAULT_GRADING_RUBRIC,
)
from src.database.schema import create_database, get_session


class TestStage4:
    """Test Stage 4: PromptManager class."""
    
    def test_load_prompt_from_file(self):
        """Test loading prompt sections from markdown file."""
        prompt_path = Path("prompts/research-agent-prompt.md")
        
        if not prompt_path.exists():
            pytest.skip(f"Prompt file not found: {prompt_path}")
        
        sections = PromptManager.load_prompt_from_file(prompt_path)
        
        assert "instructions" in sections
        assert "classification_reference" in sections
        assert "full_content" in sections
        assert len(sections["instructions"]) > 0
        assert len(sections["full_content"]) > 0
        
        print(f"✅ Loaded prompt sections: {list(sections.keys())}")
        print(f"   Instructions length: {len(sections['instructions'])} chars")
        print(f"   Classification reference length: {len(sections['classification_reference'])} chars")
    
    def test_create_version_from_file(self):
        """Test creating prompt version from file."""
        create_database()
        prompt_path = Path("prompts/research-agent-prompt.md")
        
        if not prompt_path.exists():
            pytest.skip(f"Prompt file not found: {prompt_path}")
        
        session = get_session()
        try:
            # Clean up any existing test versions
            existing = PromptManager.get_version("test-prompt", "1.0", session=session)
            if existing:
                session.delete(existing)
                session.commit()
            
            pv = PromptManager.create_version_from_file(
                prompt_name="test-prompt",
                prompt_path=prompt_path,
                version="1.0",
                description="Test version",
                created_by="test",
                session=session,
            )
            
            assert pv.prompt_name == "test-prompt"
            assert pv.version == "1.0"
            assert pv.is_active is True
            assert len(pv.instructions_content) > 0
            print(f"✅ Created prompt version: {pv.prompt_name}@{pv.version}")
            print(f"   ID: {pv.id}")
            
            # Cleanup
            existing = PromptManager.get_version("test-prompt", "1.0", session=session)
            if existing:
                session.delete(existing)
                session.commit()
            
        finally:
            session.close()
    
    def test_get_active_version(self):
        """Test retrieving active version."""
        create_database()
        prompt_path = Path("prompts/research-agent-prompt.md")
        
        if not prompt_path.exists():
            pytest.skip(f"Prompt file not found: {prompt_path}")
        
        session = get_session()
        try:
            # Create test version
            pv = PromptManager.create_version_from_file(
                prompt_name="test-prompt-active",
                prompt_path=prompt_path,
                version="1.0",
                description="Test",
                created_by="test",
                session=session,
            )
            
            # Retrieve active version
            active = PromptManager.get_active_version("test-prompt-active", session=session)
            assert active is not None
            assert active.id == pv.id
            print("✅ Can retrieve active version")
            
            # Cleanup
            existing = PromptManager.get_version("test-prompt-active", "1.0", session=session)
            if existing:
                session.delete(existing)
                session.commit()
            
        finally:
            session.close()
    
    def test_get_version(self):
        """Test retrieving specific version."""
        create_database()
        prompt_path = Path("prompts/research-agent-prompt.md")
        
        if not prompt_path.exists():
            pytest.skip(f"Prompt file not found: {prompt_path}")
        
        session = get_session()
        try:
            # Create test version
            pv = PromptManager.create_version_from_file(
                prompt_name="test-prompt-specific",
                prompt_path=prompt_path,
                version="1.0",
                description="Test",
                created_by="test",
                session=session,
            )
            
            # Retrieve specific version
            specific = PromptManager.get_version("test-prompt-specific", "1.0", session=session)
            assert specific is not None
            assert specific.id == pv.id
            print("✅ Can retrieve specific version")
            
            # Cleanup
            existing = PromptManager.get_version("test-prompt-specific", "1.0", session=session)
            if existing:
                session.delete(existing)
                session.commit()
            
        finally:
            session.close()
    
    def test_list_versions(self):
        """Test listing all versions."""
        create_database()
        prompt_path = Path("prompts/research-agent-prompt.md")
        
        if not prompt_path.exists():
            pytest.skip(f"Prompt file not found: {prompt_path}")
        
        session = get_session()
        try:
            # Create test versions
            pv1 = PromptManager.create_version_from_file(
                prompt_name="test-prompt-list",
                prompt_path=prompt_path,
                version="1.0",
                description="Test",
                created_by="test",
                session=session,
            )
            
            pv2 = PromptManager.create_version_from_file(
                prompt_name="test-prompt-list",
                prompt_path=prompt_path,
                version="2.0",
                description="Test",
                created_by="test",
                session=session,
            )
            
            # List versions
            versions = PromptManager.list_versions("test-prompt-list", session=session)
            assert len(versions) >= 2
            print(f"✅ Can list versions ({len(versions)} found)")
            
            # Cleanup
            for version in versions:
                session.delete(version)
            session.commit()
            
        finally:
            session.close()


class TestStage5:
    """Test Stage 5: GradingPromptManager class."""
    
    def test_create_version(self):
        """Test creating grading prompt version."""
        create_database()
        session = get_session()
        try:
            # Clean up any existing test versions
            existing = GradingPromptManager.get_version("test-1.0", session=session)
            if existing:
                session.delete(existing)
                session.commit()
            
            gpv = GradingPromptManager.create_version(
                version="test-1.0",
                prompt_template=DEFAULT_GRADING_PROMPT_TEMPLATE,
                scoring_rubric=DEFAULT_GRADING_RUBRIC,
                description="Test grading prompt",
                session=session,
            )
            
            assert gpv.version == "test-1.0"
            assert gpv.is_active is True
            assert len(gpv.prompt_template) > 0
            print(f"✅ Created grading prompt version: {gpv.version}")
            print(f"   ID: {gpv.id}")
            
            # Cleanup
            session.delete(gpv)
            session.commit()
            
        finally:
            session.close()
    
    def test_get_active_version(self):
        """Test retrieving active grading prompt."""
        create_database()
        session = get_session()
        try:
            # Create test version
            gpv = GradingPromptManager.create_version(
                version="test-active-1.0",
                prompt_template=DEFAULT_GRADING_PROMPT_TEMPLATE,
                scoring_rubric=DEFAULT_GRADING_RUBRIC,
                session=session,
            )
            
            # Retrieve active version
            active = GradingPromptManager.get_active_version(session=session)
            assert active is not None
            assert active.version == "test-active-1.0"
            print("✅ Can retrieve active grading prompt")
            
            # Cleanup
            session.delete(gpv)
            session.commit()
            
        finally:
            session.close()
    
    def test_get_version(self):
        """Test retrieving specific grading prompt version."""
        create_database()
        session = get_session()
        try:
            # Create test version
            gpv = GradingPromptManager.create_version(
                version="test-specific-1.0",
                prompt_template=DEFAULT_GRADING_PROMPT_TEMPLATE,
                scoring_rubric=DEFAULT_GRADING_RUBRIC,
                session=session,
            )
            
            # Retrieve specific version
            specific = GradingPromptManager.get_version("test-specific-1.0", session=session)
            assert specific is not None
            assert specific.id == gpv.id
            print("✅ Can retrieve specific grading prompt version")
            
            # Cleanup
            session.delete(gpv)
            session.commit()
            
        finally:
            session.close()
    
    def test_create_default_version(self):
        """Test creating default grading prompt version."""
        create_database()
        session = get_session()
        try:
            # Check if default exists, delete if it does
            existing = GradingPromptManager.get_version("1.0", session=session)
            if existing:
                session.delete(existing)
                session.commit()
            
            gpv = GradingPromptManager.create_default_version(session=session)
            
            assert gpv.version == "1.0"
            assert gpv.is_active is True
            assert "{field_name}" in gpv.prompt_template
            print("✅ Created default grading prompt version (v1.0)")
            
            # Cleanup
            session.delete(gpv)
            session.commit()
            
        finally:
            session.close()


class TestStage6:
    """Test Stage 6: Initialize prompts script."""
    
    def test_script_imports(self):
        """Test that the script can be imported."""
        import scripts.initialize_prompts as init_script
        assert hasattr(init_script, 'main')
        assert hasattr(init_script, 'initialize_agent_prompt')
        assert hasattr(init_script, 'initialize_grading_prompt')
        print("✅ Script imports successfully")
    
    def test_initialize_agent_prompt_function(self):
        """Test the initialize_agent_prompt function."""
        prompt_path = Path("prompts/research-agent-prompt.md")
        
        if not prompt_path.exists():
            pytest.skip(f"Prompt file not found: {prompt_path}")
        
        create_database()
        session = get_session()
        try:
            # Clean up any existing test versions
            existing = PromptManager.get_version("script-test-prompt", "1.0", session=session)
            if existing:
                session.delete(existing)
                session.commit()
            
            from scripts.initialize_prompts import initialize_agent_prompt
            
            initialize_agent_prompt(
                prompt_path=prompt_path,
                prompt_name="script-test-prompt",
                version="1.0",
                description="Script test",
                created_by="test",
            )
            
            # Verify it was created
            pv = PromptManager.get_version("script-test-prompt", "1.0", session=session)
            assert pv is not None
            print("✅ initialize_agent_prompt function works")
            
            # Cleanup
            session.delete(pv)
            session.commit()
            
        finally:
            session.close()
    
    def test_initialize_grading_prompt_function(self):
        """Test the initialize_grading_prompt function."""
        create_database()
        session = get_session()
        try:
            # Clean up any existing test versions
            existing = GradingPromptManager.get_version("script-test-1.0", session=session)
            if existing:
                session.delete(existing)
                session.commit()
            
            from scripts.initialize_prompts import initialize_grading_prompt
            
            initialize_grading_prompt(
                version="script-test-1.0",
                description="Script test",
            )
            
            # Verify it was created
            gpv = GradingPromptManager.get_version("script-test-1.0", session=session)
            assert gpv is not None
            print("✅ initialize_grading_prompt function works")
            
            # Cleanup
            session.delete(gpv)
            session.commit()
            
        finally:
            session.close()


if __name__ == "__main__":
    """Run verification tests directly."""
    print("=" * 60)
    print("Testing Stage 4: PromptManager")
    print("=" * 60)
    
    test4 = TestStage4()
    test4.test_load_prompt_from_file()
    test4.test_create_version_from_file()
    test4.test_get_active_version()
    test4.test_get_version()
    test4.test_list_versions()
    
    print("\n" + "=" * 60)
    print("Testing Stage 5: GradingPromptManager")
    print("=" * 60)
    
    test5 = TestStage5()
    test5.test_create_version()
    test5.test_get_active_version()
    test5.test_get_version()
    test5.test_create_default_version()
    
    print("\n" + "=" * 60)
    print("Testing Stage 6: Initialize Prompts Script")
    print("=" * 60)
    
    test6 = TestStage6()
    test6.test_script_imports()
    test6.test_initialize_agent_prompt_function()
    test6.test_initialize_grading_prompt_function()
    
    print("\n" + "=" * 60)
    print("✅ All stages 4-6 verification tests passed!")
    print("=" * 60)

