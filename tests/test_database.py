"""
Tests for database schema and operations.

Tests cover:
- Database schema creation
- CRUD operations
- Model relationships
- Query functions
- Database migrations
"""

from datetime import datetime
from unittest.mock import Mock

import pytest
from sqlalchemy import select

from src.database.schema import (
    Company,
    SearchHistory,
    AgentExecution,
    ResearchQuery,
    ProcessingRun,
    ValidationResult,
    LLMCallLog,
    Base,
)
from src.database.operations import (
    save_company,
    get_company,
    save_search_history,
    save_agent_execution,
    get_recent_searches,
)


@pytest.mark.unit
class TestDatabaseSchema:
    """Tests for database schema models."""

    def test_create_company(self, test_db_session):
        """Test creating a Company record."""
        company = Company(
            name="Test Company",
            website="https://test.com",
            industry="Technology",
            funding_status="Series A",
            company_size="50-100",
            summary="A test company"
        )

        test_db_session.add(company)
        test_db_session.commit()

        # Query back
        result = test_db_session.query(Company).filter_by(name="Test Company").first()

        assert result is not None
        assert result.name == "Test Company"
        assert result.website == "https://test.com"
        assert result.industry == "Technology"

    def test_create_search_history(self, test_db_session):
        """Test creating a SearchHistory record."""
        search = SearchHistory(
            company_name="Test Company",
            query="Test Company funding",
            provider="tavily",
            results_count=5,
            raw_results={"results": [{"title": "Test"}]}
        )

        test_db_session.add(search)
        test_db_session.commit()

        result = test_db_session.query(SearchHistory).first()

        assert result is not None
        assert result.company_name == "Test Company"
        assert result.query == "Test Company funding"
        assert result.provider == "tavily"
        assert result.results_count == 5
        assert "results" in result.raw_results

    def test_create_agent_execution(self, test_db_session):
        """Test creating an AgentExecution record."""
        execution = AgentExecution(
            company_name="Test Company",
            model_type="openai",
            model_name="gpt-4",
            success=True,
            iterations=3,
            total_tokens=1500,
            execution_time_seconds=12.5,
            result={"industry": "Technology"}
        )

        test_db_session.add(execution)
        test_db_session.commit()

        result = test_db_session.query(AgentExecution).first()

        assert result is not None
        assert result.company_name == "Test Company"
        assert result.success is True
        assert result.iterations == 3
        assert result.total_tokens == 1500

    def test_create_research_query(self, test_db_session):
        """Test creating a ResearchQuery record."""
        query = ResearchQuery(
            company_name="Test Company",
            query_type="general",
            query_text="Test Company information",
            metadata={"category": "overview"}
        )

        test_db_session.add(query)
        test_db_session.commit()

        result = test_db_session.query(ResearchQuery).first()

        assert result is not None
        assert result.company_name == "Test Company"
        assert result.query_type == "general"
        assert result.metadata["category"] == "overview"

    def test_create_processing_run(self, test_db_session):
        """Test creating a ProcessingRun record."""
        run = ProcessingRun(
            company_name="Test Company",
            llm_provider="openai",
            llm_model="gpt-4",
            prompt_version="1.0",
            success=True,
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            processing_time_seconds=5.5,
            output={"summary": "Test output"}
        )

        test_db_session.add(run)
        test_db_session.commit()

        result = test_db_session.query(ProcessingRun).first()

        assert result is not None
        assert result.company_name == "Test Company"
        assert result.llm_provider == "openai"
        assert result.total_tokens == 300
        assert result.success is True

    def test_create_validation_result(self, test_db_session):
        """Test creating a ValidationResult record."""
        # First create a processing run
        run = ProcessingRun(
            company_name="Test Company",
            llm_provider="openai",
            llm_model="gpt-4",
            success=True,
            output={"test": "data"}
        )
        test_db_session.add(run)
        test_db_session.commit()

        # Now create validation result
        validation = ValidationResult(
            processing_run_id=run.id,
            validation_type="completeness",
            score=0.95,
            details={"fields_present": 10}
        )

        test_db_session.add(validation)
        test_db_session.commit()

        result = test_db_session.query(ValidationResult).first()

        assert result is not None
        assert result.validation_type == "completeness"
        assert result.score == 0.95
        assert result.processing_run_id == run.id

    def test_create_llm_call_log(self, test_db_session):
        """Test creating an LLMCallLog record."""
        log = LLMCallLog(
            model_type="openai",
            model_name="gpt-4",
            call_type="chat",
            prompt="Test prompt",
            response="Test response",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            generation_time_seconds=2.5,
            tokens_per_second=12.0,
            success=True
        )

        test_db_session.add(log)
        test_db_session.commit()

        result = test_db_session.query(LLMCallLog).first()

        assert result is not None
        assert result.model_name == "gpt-4"
        assert result.total_tokens == 30
        assert result.success is True

    def test_model_relationships(self, test_db_session):
        """Test relationships between models."""
        # Create processing run
        run = ProcessingRun(
            company_name="Test Company",
            llm_provider="openai",
            llm_model="gpt-4",
            success=True,
            output={}
        )
        test_db_session.add(run)
        test_db_session.commit()

        # Create validation linked to run
        validation = ValidationResult(
            processing_run_id=run.id,
            validation_type="completeness",
            score=0.9,
            details={}
        )
        test_db_session.add(validation)
        test_db_session.commit()

        # Query with relationship
        result = test_db_session.query(ProcessingRun).filter_by(id=run.id).first()

        assert result is not None
        assert len(result.validations) == 1
        assert result.validations[0].score == 0.9


@pytest.mark.unit
class TestDatabaseOperations:
    """Tests for database operation functions."""

    def test_save_company(self, test_db_session):
        """Test saving a company via operations module."""
        company_data = {
            "name": "BitMovin",
            "website": "https://bitmovin.com",
            "industry": "Video Technology",
            "funding_status": "Series B",
            "company_size": "200+",
            "summary": "Video infrastructure company"
        }

        saved = save_company(test_db_session, company_data)

        assert saved is not None
        assert saved.name == "BitMovin"
        assert saved.id is not None

    def test_save_company_duplicate(self, test_db_session):
        """Test saving duplicate company updates existing record."""
        company_data = {
            "name": "BitMovin",
            "website": "https://bitmovin.com",
            "industry": "Video Technology"
        }

        # Save first time
        first = save_company(test_db_session, company_data)
        first_id = first.id

        # Save again with updated data
        company_data["industry"] = "Streaming Technology"
        second = save_company(test_db_session, company_data)

        # Should update, not create new
        assert second.id == first_id
        assert second.industry == "Streaming Technology"

    def test_get_company(self, test_db_session):
        """Test retrieving a company by name."""
        # Create company
        company = Company(name="Test Co", website="https://test.com")
        test_db_session.add(company)
        test_db_session.commit()

        # Retrieve
        result = get_company(test_db_session, "Test Co")

        assert result is not None
        assert result.name == "Test Co"

    def test_get_company_not_found(self, test_db_session):
        """Test retrieving non-existent company returns None."""
        result = get_company(test_db_session, "Nonexistent Company")
        assert result is None

    def test_save_search_history(self, test_db_session):
        """Test saving search history."""
        search_data = {
            "company_name": "BitMovin",
            "query": "BitMovin funding",
            "provider": "tavily",
            "results": [
                {"title": "Result 1", "url": "https://example.com"}
            ]
        }

        saved = save_search_history(test_db_session, search_data)

        assert saved is not None
        assert saved.company_name == "BitMovin"
        assert saved.results_count == 1

    def test_save_agent_execution(self, test_db_session):
        """Test saving agent execution."""
        execution_data = {
            "company_name": "BitMovin",
            "model_type": "openai",
            "model_name": "gpt-4",
            "success": True,
            "iterations": 2,
            "total_tokens": 1000,
            "execution_time_seconds": 8.5,
            "result": {"industry": "Video Technology"}
        }

        saved = save_agent_execution(test_db_session, execution_data)

        assert saved is not None
        assert saved.success is True
        assert saved.iterations == 2

    def test_get_recent_searches(self, test_db_session):
        """Test retrieving recent searches."""
        # Create multiple searches
        for i in range(5):
            search = SearchHistory(
                company_name=f"Company {i}",
                query=f"Query {i}",
                provider="tavily",
                results_count=3
            )
            test_db_session.add(search)

        test_db_session.commit()

        # Get recent searches
        recent = get_recent_searches(test_db_session, limit=3)

        assert len(recent) == 3
        # Should be in reverse chronological order (most recent first)
        assert recent[0].company_name == "Company 4"


@pytest.mark.unit
class TestDatabaseQueries:
    """Tests for complex database queries."""

    def test_query_executions_by_model(self, test_db_session):
        """Test querying executions by model type."""
        # Create executions with different models
        for model in ["openai", "anthropic", "local"]:
            execution = AgentExecution(
                company_name="Test Co",
                model_type=model,
                model_name=f"{model}-model",
                success=True
            )
            test_db_session.add(execution)

        test_db_session.commit()

        # Query OpenAI executions
        openai_execs = test_db_session.query(AgentExecution).filter_by(
            model_type="openai"
        ).all()

        assert len(openai_execs) == 1
        assert openai_execs[0].model_type == "openai"

    def test_query_failed_executions(self, test_db_session):
        """Test querying failed executions."""
        # Create mix of successful and failed
        for i in range(5):
            execution = AgentExecution(
                company_name=f"Company {i}",
                model_type="openai",
                model_name="gpt-4",
                success=(i % 2 == 0)  # Alternate success/failure
            )
            test_db_session.add(execution)

        test_db_session.commit()

        # Query failed
        failed = test_db_session.query(AgentExecution).filter_by(
            success=False
        ).all()

        assert len(failed) == 2

    def test_query_token_usage_stats(self, test_db_session):
        """Test aggregating token usage statistics."""
        from sqlalchemy import func

        # Create executions with token usage
        for i in range(3):
            execution = AgentExecution(
                company_name="Test Co",
                model_type="openai",
                model_name="gpt-4",
                success=True,
                total_tokens=1000 * (i + 1)
            )
            test_db_session.add(execution)

        test_db_session.commit()

        # Aggregate stats
        total_tokens = test_db_session.query(
            func.sum(AgentExecution.total_tokens)
        ).scalar()

        assert total_tokens == 6000  # 1000 + 2000 + 3000

    def test_query_search_history_by_company(self, test_db_session):
        """Test querying search history for specific company."""
        # Create searches for different companies
        companies = ["BitMovin", "Notion", "BitMovin"]
        for company in companies:
            search = SearchHistory(
                company_name=company,
                query=f"{company} info",
                provider="tavily",
                results_count=5
            )
            test_db_session.add(search)

        test_db_session.commit()

        # Query BitMovin searches
        bitmovin_searches = test_db_session.query(SearchHistory).filter_by(
            company_name="BitMovin"
        ).all()

        assert len(bitmovin_searches) == 2
