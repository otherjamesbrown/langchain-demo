"""
Verification scripts for Stages 1-3 of testing framework implementation.

These tests verify that the database schema changes work correctly:
- Stage 1: PromptVersion and GradingPromptVersion tables
- Stage 2: TestRun and LLMOutputValidation tables
- Stage 3: LLMOutputValidationResult table
"""

import pytest
from datetime import datetime
from src.database.schema import (
    PromptVersion,
    GradingPromptVersion,
    TestRun,
    LLMOutputValidation,
    LLMOutputValidationResult,
    create_database,
    get_session,
)


class TestStage1:
    """Test Stage 1: PromptVersion and GradingPromptVersion tables."""
    
    def test_tables_exist(self):
        """Verify tables are created."""
        create_database()
        session = get_session()
        try:
            # Check PromptVersion table
            count = session.query(PromptVersion).count()
            print(f"✅ PromptVersion table exists (count: {count})")
            
            # Check GradingPromptVersion table
            count = session.query(GradingPromptVersion).count()
            print(f"✅ GradingPromptVersion table exists (count: {count})")
            
        finally:
            session.close()
    
    def test_prompt_version_unique_constraint(self):
        """Test unique constraint on (prompt_name, version)."""
        create_database()
        session = get_session()
        try:
            # Create first version
            test = PromptVersion(
                prompt_name="test-prompt",
                version="1.0",
                instructions_content="test",
                full_content="test"
            )
            session.add(test)
            session.commit()
            print("✅ Can create prompt version")
            
            # Try duplicate (should fail)
            try:
                duplicate = PromptVersion(
                    prompt_name="test-prompt",
                    version="1.0",
                    instructions_content="test2",
                    full_content="test2"
                )
                session.add(duplicate)
                session.commit()
                pytest.fail("❌ Unique constraint failed!")
            except Exception as e:
                print(f"✅ Unique constraint works: {type(e).__name__}")
                session.rollback()
            
            # Cleanup
            session.query(PromptVersion).filter(
                PromptVersion.prompt_name == "test-prompt"
            ).delete()
            session.commit()
            
        finally:
            session.close()
    
    def test_grading_prompt_version_unique_constraint(self):
        """Test unique constraint on grading prompt version."""
        create_database()
        session = get_session()
        try:
            # Create first version
            test = GradingPromptVersion(
                version="1.0",
                prompt_template="test",
                scoring_rubric="test"
            )
            session.add(test)
            session.commit()
            print("✅ Can create grading prompt version")
            
            # Try duplicate (should fail)
            try:
                duplicate = GradingPromptVersion(
                    version="1.0",
                    prompt_template="test2",
                    scoring_rubric="test2"
                )
                session.add(duplicate)
                session.commit()
                pytest.fail("❌ Unique constraint failed!")
            except Exception as e:
                print(f"✅ Unique constraint works: {type(e).__name__}")
                session.rollback()
            
            # Cleanup
            session.query(GradingPromptVersion).filter(
                GradingPromptVersion.version == "1.0"
            ).delete()
            session.commit()
            
        finally:
            session.close()


class TestStage2:
    """Test Stage 2: TestRun and LLMOutputValidation tables."""
    
    def test_test_run_creation(self):
        """Test creating test run with prompt version relationship."""
        create_database()
        session = get_session()
        try:
            # Create test prompt version
            pv = PromptVersion(
                prompt_name="test-prompt",
                version="1.0",
                instructions_content="test",
                full_content="test"
            )
            session.add(pv)
            session.commit()
            
            # Create test run
            test_run = TestRun(
                test_name="llm-output-validation",
                company_name="BitMovin",
                prompt_version_id=pv.id,
                prompt_name=pv.prompt_name,
                prompt_version=pv.version
            )
            session.add(test_run)
            session.commit()
            
            # Verify relationship
            assert test_run.prompt_version_obj.id == pv.id
            print("✅ TestRun created with relationship")
            
            # Cleanup
            session.query(TestRun).filter(TestRun.id == test_run.id).delete()
            session.query(PromptVersion).filter(PromptVersion.id == pv.id).delete()
            session.commit()
            
        finally:
            session.close()
    
    def test_llm_output_validation_creation(self):
        """Test creating LLM output validation with all fields."""
        create_database()
        session = get_session()
        try:
            # Create test prompt version
            pv = PromptVersion(
                prompt_name="test-prompt",
                version="1.0",
                instructions_content="test",
                full_content="test"
            )
            session.add(pv)
            session.commit()
            
            # Create test run
            test_run = TestRun(
                test_name="llm-output-validation",
                company_name="BitMovin",
                prompt_version_id=pv.id,
                prompt_name=pv.prompt_name,
                prompt_version=pv.version
            )
            session.add(test_run)
            session.commit()
            
            # Create output record with JSON fields
            output = LLMOutputValidation(
                test_run_id=test_run.id,
                test_name="llm-output-validation",
                company_name="BitMovin",
                model_name="test-model",
                model_provider="test",
                company_name_field="BitMovin",
                industry="SaaS",
                success=True,
                input_tokens=1000,
                output_tokens=500,
                total_tokens=1500,
                estimated_cost_usd=0.01,
                ground_truth_status="unvalidated",
                products=["Product 1", "Product 2"],  # JSON field
                competitors=["Competitor 1"],  # JSON field
                key_personas=["Persona 1"]  # JSON field
            )
            session.add(output)
            session.commit()
            
            # Verify relationships
            assert output.test_run.id == test_run.id
            assert test_run.prompt_version_obj.id == pv.id
            print("✅ LLMOutputValidation created with relationships")
            
            # Verify JSON fields
            assert output.products == ["Product 1", "Product 2"]
            assert output.competitors == ["Competitor 1"]
            assert output.key_personas == ["Persona 1"]
            print("✅ JSON fields work correctly")
            
            # Cleanup
            session.query(LLMOutputValidation).filter(
                LLMOutputValidation.test_run_id == test_run.id
            ).delete()
            session.query(TestRun).filter(TestRun.id == test_run.id).delete()
            session.query(PromptVersion).filter(PromptVersion.id == pv.id).delete()
            session.commit()
            
        finally:
            session.close()


class TestStage3:
    """Test Stage 3: LLMOutputValidationResult table."""
    
    def test_validation_result_creation(self):
        """Test creating validation result with structured JSON."""
        create_database()
        session = get_session()
        try:
            # Create all linked records
            pv = PromptVersion(
                prompt_name="test-prompt",
                version="1.0",
                instructions_content="test",
                full_content="test"
            )
            gpv = GradingPromptVersion(
                version="1.0",
                prompt_template="test",
                scoring_rubric="test"
            )
            session.add_all([pv, gpv])
            session.commit()
            
            test_run = TestRun(
                test_name="test",
                company_name="BitMovin",
                prompt_version_id=pv.id,
                prompt_name=pv.prompt_name,
                prompt_version=pv.version
            )
            session.add(test_run)
            session.commit()
            
            output = LLMOutputValidation(
                test_run_id=test_run.id,
                test_name="test",
                company_name="BitMovin",
                model_name="test",
                model_provider="test",
                success=True
            )
            session.add(output)
            session.commit()
            
            # Create result with structured JSON
            field_scores = {
                "industry": {
                    "score": 85,
                    "match_type": "semantic",
                    "explanation": "Close match",
                    "confidence": 0.9
                },
                "company_size": {
                    "score": 100,
                    "match_type": "exact",
                    "explanation": "Exact match",
                    "confidence": 1.0
                }
            }
            
            result = LLMOutputValidationResult(
                output_id=output.id,
                test_run_id=test_run.id,
                test_name="test",
                company_name="BitMovin",
                model_name="test",
                model_provider="test",
                field_accuracy_scores=field_scores,
                overall_accuracy=92.5,
                required_fields_accuracy=90.0,
                optional_fields_accuracy=95.0,
                weighted_accuracy=91.0,
                graded_by_model="gemini-flash-latest",
                grading_prompt_version_id=gpv.id,
                grading_confidence=0.95,
                grading_input_tokens=500,
                grading_output_tokens=200,
                grading_total_tokens=700,
                grading_cost_usd=0.01
            )
            session.add(result)
            session.commit()
            
            # Verify JSON storage
            retrieved = session.query(LLMOutputValidationResult).filter(
                LLMOutputValidationResult.id == result.id
            ).first()
            assert retrieved.field_accuracy_scores["industry"]["score"] == 85
            assert retrieved.field_accuracy_scores["company_size"]["match_type"] == "exact"
            print("✅ JSON field storage works")
            
            # Verify relationships
            assert retrieved.output.id == output.id
            assert retrieved.test_run.id == test_run.id
            print("✅ Relationships work correctly")
            
            # Cleanup
            session.query(LLMOutputValidationResult).delete()
            session.query(LLMOutputValidation).delete()
            session.query(TestRun).delete()
            session.query(GradingPromptVersion).delete()
            session.query(PromptVersion).delete()
            session.commit()
            
        finally:
            session.close()


if __name__ == "__main__":
    """Run verification tests directly."""
    print("=" * 60)
    print("Testing Stage 1: PromptVersion and GradingPromptVersion")
    print("=" * 60)
    
    test1 = TestStage1()
    test1.test_tables_exist()
    test1.test_prompt_version_unique_constraint()
    test1.test_grading_prompt_version_unique_constraint()
    
    print("\n" + "=" * 60)
    print("Testing Stage 2: TestRun and LLMOutputValidation")
    print("=" * 60)
    
    test2 = TestStage2()
    test2.test_test_run_creation()
    test2.test_llm_output_validation_creation()
    
    print("\n" + "=" * 60)
    print("Testing Stage 3: LLMOutputValidationResult")
    print("=" * 60)
    
    test3 = TestStage3()
    test3.test_validation_result_creation()
    
    print("\n" + "=" * 60)
    print("✅ All stages 1-3 verification tests passed!")
    print("=" * 60)

