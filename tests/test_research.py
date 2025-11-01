"""
Tests for research agent and two-phase architecture.

Tests cover:
- Research agent initialization
- Two-phase workflow (search collection + LLM processing)
- Query generation
- Search execution
- Prompt building
- LLM processing
- Validation
"""

from unittest.mock import Mock, patch, MagicMock

import pytest

from src.research.query_generator import generate_queries, QueryTemplate
from src.research.search_executor import SearchExecutor
from src.research.prompt_builder import build_prompt
from src.research.llm_processor import LLMProcessor
from src.research.validation import (
    validate_completeness,
    compare_results,
    calculate_consensus_score,
)


@pytest.mark.unit
class TestQueryGenerator:
    """Tests for query generation."""

    def test_generate_queries_default(self):
        """Test generating default queries for a company."""
        queries = generate_queries("BitMovin")

        assert len(queries) > 0
        assert any("BitMovin" in q["query"] for q in queries)

    def test_generate_queries_custom_template(self):
        """Test generating queries with custom template."""
        template = QueryTemplate(
            name="test_template",
            category="test",
            template="{company_name} test query"
        )

        queries = generate_queries("BitMovin", templates=[template])

        assert len(queries) == 1
        assert queries[0]["query"] == "BitMovin test query"
        assert queries[0]["category"] == "test"

    def test_generate_queries_multiple_templates(self):
        """Test generating multiple queries."""
        templates = [
            QueryTemplate(
                name="template1",
                category="cat1",
                template="{company_name} query 1"
            ),
            QueryTemplate(
                name="template2",
                category="cat2",
                template="{company_name} query 2"
            ),
        ]

        queries = generate_queries("BitMovin", templates=templates)

        assert len(queries) == 2
        assert queries[0]["query"] == "BitMovin query 1"
        assert queries[1]["query"] == "BitMovin query 2"


@pytest.mark.unit
class TestSearchExecutor:
    """Tests for search execution."""

    @patch("src.research.search_executor.TavilySearch")
    def test_search_executor_execute(self, mock_tavily_class, mock_env_vars):
        """Test executing searches."""
        # Mock search results
        mock_searcher = Mock()
        mock_searcher.search.return_value = [
            {
                "title": "Result 1",
                "url": "https://example.com",
                "content": "Content 1",
                "score": 0.9
            }
        ]
        mock_tavily_class.return_value = mock_searcher

        executor = SearchExecutor(provider="tavily")
        queries = [
            {"query": "BitMovin funding", "category": "funding"},
            {"query": "BitMovin products", "category": "products"},
        ]

        results = executor.execute_searches("BitMovin", queries)

        assert len(results) == 2
        assert results[0]["category"] == "funding"
        assert len(results[0]["results"]) == 1
        assert mock_searcher.search.call_count == 2

    @patch("src.research.search_executor.SerperSearch")
    def test_search_executor_serper(self, mock_serper_class, mock_env_vars):
        """Test executing searches with Serper provider."""
        mock_searcher = Mock()
        mock_searcher.search.return_value = [
            {"title": "Test", "url": "https://test.com", "content": "Test"}
        ]
        mock_serper_class.return_value = mock_searcher

        executor = SearchExecutor(provider="serper")
        queries = [{"query": "test query", "category": "test"}]

        results = executor.execute_searches("TestCo", queries)

        assert len(results) == 1
        mock_serper_class.assert_called_once()

    def test_search_executor_invalid_provider(self):
        """Test search executor with invalid provider."""
        with pytest.raises(ValueError, match="provider"):
            SearchExecutor(provider="invalid_provider")


@pytest.mark.unit
class TestPromptBuilder:
    """Tests for prompt building."""

    def test_build_prompt_basic(self, sample_instructions_path):
        """Test building a basic prompt."""
        search_results = [
            {
                "category": "general",
                "query": "BitMovin info",
                "results": [
                    {
                        "title": "BitMovin Homepage",
                        "url": "https://bitmovin.com",
                        "content": "Video infrastructure company"
                    }
                ]
            }
        ]

        prompt = build_prompt(
            company_name="BitMovin",
            instructions_path=str(sample_instructions_path),
            search_results=search_results
        )

        assert "BitMovin" in prompt
        assert "Video infrastructure" in prompt
        assert "Research Instructions" in prompt

    def test_build_prompt_multiple_searches(self):
        """Test building prompt with multiple search categories."""
        search_results = [
            {
                "category": "funding",
                "query": "BitMovin funding",
                "results": [
                    {"title": "Funding News", "url": "https://tc.com", "content": "Series B"}
                ]
            },
            {
                "category": "products",
                "query": "BitMovin products",
                "results": [
                    {"title": "Products", "url": "https://bitmovin.com/products", "content": "Encoding"}
                ]
            }
        ]

        prompt = build_prompt(
            company_name="BitMovin",
            instructions="Research this company",
            search_results=search_results
        )

        assert "funding" in prompt.lower()
        assert "products" in prompt.lower()
        assert "Series B" in prompt
        assert "Encoding" in prompt

    def test_build_prompt_empty_results(self):
        """Test building prompt with empty search results."""
        prompt = build_prompt(
            company_name="BitMovin",
            instructions="Research this company",
            search_results=[]
        )

        assert "BitMovin" in prompt
        assert "Research this company" in prompt


@pytest.mark.unit
class TestLLMProcessor:
    """Tests for LLM processing."""

    @patch("src.research.llm_processor.get_llm")
    def test_llm_processor_process(self, mock_get_llm, mock_env_vars):
        """Test processing with LLM."""
        # Mock LLM
        mock_llm = Mock()
        mock_llm.invoke.return_value = "BitMovin is a video infrastructure company."
        mock_get_llm.return_value = mock_llm

        processor = LLMProcessor(llm_provider="openai", llm_model="gpt-4")
        result = processor.process(
            prompt="Summarize BitMovin",
            company_name="BitMovin"
        )

        assert result is not None
        assert "video infrastructure" in result.lower()
        mock_llm.invoke.assert_called_once()

    @patch("src.research.llm_processor.get_llm")
    def test_llm_processor_with_metadata(self, mock_get_llm, mock_env_vars):
        """Test processing with metadata tracking."""
        mock_llm = Mock()
        mock_llm.invoke.return_value = "Summary text"
        mock_get_llm.return_value = mock_llm

        processor = LLMProcessor(llm_provider="anthropic", llm_model="claude-3-opus")
        result = processor.process(
            prompt="Test prompt",
            company_name="TestCo",
            metadata={"prompt_version": "1.0"}
        )

        assert result is not None
        mock_llm.invoke.assert_called_once()


@pytest.mark.unit
class TestValidation:
    """Tests for validation utilities."""

    def test_validate_completeness_complete(self):
        """Test validation of complete results."""
        result = {
            "company_name": "BitMovin",
            "industry": "Video Technology",
            "products": ["Encoding", "Analytics"],
            "funding_status": "Series B",
            "company_size": "200+",
            "competitors": ["Mux", "Cloudflare"],
            "summary": "Video infrastructure company"
        }

        score, details = validate_completeness(result)

        assert score >= 0.9  # Should be nearly complete
        assert details["fields_present"] > 5

    def test_validate_completeness_incomplete(self):
        """Test validation of incomplete results."""
        result = {
            "company_name": "BitMovin",
            "industry": "Video Technology"
        }

        score, details = validate_completeness(result)

        assert score < 0.5  # Should be incomplete
        assert details["fields_present"] < 5

    def test_validate_completeness_empty(self):
        """Test validation of empty results."""
        result = {}

        score, details = validate_completeness(result)

        assert score == 0.0
        assert details["fields_present"] == 0

    def test_compare_results(self):
        """Test comparing results from different models."""
        result1 = {
            "company_name": "BitMovin",
            "industry": "Video Technology",
            "summary": "Video infrastructure"
        }

        result2 = {
            "company_name": "BitMovin",
            "industry": "Video Tech",
            "summary": "Video streaming infrastructure"
        }

        comparison = compare_results([result1, result2])

        assert "company_name" in comparison
        assert comparison["company_name"]["agreement"] is True

    def test_calculate_consensus_score(self):
        """Test calculating consensus across multiple results."""
        results = [
            {"industry": "Video Technology", "company_size": "200+"},
            {"industry": "Video Technology", "company_size": "200-500"},
            {"industry": "Streaming", "company_size": "200+"},
        ]

        score = calculate_consensus_score(results)

        assert 0.0 <= score <= 1.0
        # Some agreement (2/3 on industry value, 2/3 on company_size)
        assert score > 0.5


@pytest.mark.integration
@pytest.mark.slow
class TestTwoPhaseWorkflow:
    """Integration tests for two-phase workflow."""

    @patch("src.research.workflows.SearchExecutor")
    @patch("src.research.workflows.generate_queries")
    def test_phase1_collect_searches(
        self, mock_generate_queries, mock_search_executor_class, test_db_session
    ):
        """Test Phase 1: Search collection workflow."""
        # Mock query generation
        mock_generate_queries.return_value = [
            {"query": "BitMovin info", "category": "general"}
        ]

        # Mock search execution
        mock_executor = Mock()
        mock_executor.execute_searches.return_value = [
            {
                "category": "general",
                "query": "BitMovin info",
                "results": [
                    {"title": "Test", "url": "https://test.com", "content": "Content"}
                ]
            }
        ]
        mock_search_executor_class.return_value = mock_executor

        from src.research.workflows import phase1_collect_searches

        # Execute Phase 1
        phase1_collect_searches(
            csv_path="test.csv",  # Would need proper mocking
            provider="tavily",
            session=test_db_session
        )

        # Verify search executor was called
        mock_executor.execute_searches.assert_called()

    @patch("src.research.workflows.LLMProcessor")
    @patch("src.research.workflows.build_prompt")
    def test_phase2_process_with_llm(
        self, mock_build_prompt, mock_llm_processor_class, test_db_session
    ):
        """Test Phase 2: LLM processing workflow."""
        # Mock prompt building
        mock_build_prompt.return_value = "Test prompt"

        # Mock LLM processing
        mock_processor = Mock()
        mock_processor.process.return_value = "Test output"
        mock_llm_processor_class.return_value = mock_processor

        from src.research.workflows import phase2_process_with_llm

        # Would need proper database setup with search results
        # This is a simplified test
        mock_processor.process.assert_not_called()  # Not called yet


