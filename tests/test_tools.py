"""
Tests for tools (web search, data loaders).

Tests cover:
- Web search functionality (Tavily, Serper)
- CSV data loading
- Markdown instruction loading
- Tool error handling
"""

import csv
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.tools.web_search import web_search, TavilySearch, SerperSearch
from src.tools.data_loaders import load_csv_companies, load_instructions, get_company_names
from src.tools.models import SearchResult, CompanyInfo


@pytest.mark.unit
class TestWebSearch:
    """Tests for web search functionality."""

    @patch("src.tools.web_search.requests.post")
    def test_tavily_search_success(self, mock_post):
        """Test successful Tavily search."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com",
                    "content": "Test content",
                    "score": 0.9
                }
            ]
        }
        mock_post.return_value = mock_response

        # Perform search
        searcher = TavilySearch(api_key="test_key")
        results = searcher.search("test query")

        # Assertions
        assert len(results) == 1
        assert results[0]["title"] == "Test Result"
        assert results[0]["url"] == "https://example.com"
        assert results[0]["score"] == 0.9

        # Verify API was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "tavily" in call_args[0][0].lower()

    @patch("src.tools.web_search.requests.post")
    def test_serper_search_success(self, mock_post):
        """Test successful Serper search."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "organic": [
                {
                    "title": "Serper Result",
                    "link": "https://example.com",
                    "snippet": "Serper content"
                }
            ]
        }
        mock_post.return_value = mock_response

        # Perform search
        searcher = SerperSearch(api_key="test_key")
        results = searcher.search("test query")

        # Assertions
        assert len(results) == 1
        assert results[0]["title"] == "Serper Result"
        assert results[0]["url"] == "https://example.com"
        assert "content" in results[0]

    @patch("src.tools.web_search.requests.post")
    def test_web_search_api_error(self, mock_post):
        """Test web search handles API errors gracefully."""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("API Error")
        mock_post.return_value = mock_response

        searcher = TavilySearch(api_key="test_key")

        with pytest.raises(Exception):
            searcher.search("test query")

    @patch("src.tools.web_search.requests.post")
    def test_web_search_empty_results(self, mock_post):
        """Test web search handles empty results."""
        # Mock empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_post.return_value = mock_response

        searcher = TavilySearch(api_key="test_key")
        results = searcher.search("test query")

        assert len(results) == 0
        assert isinstance(results, list)

    @patch("src.tools.web_search.TavilySearch")
    def test_web_search_tool_function(self, mock_tavily_class, mock_env_vars):
        """Test the web_search tool function."""
        # Mock TavilySearch instance
        mock_instance = Mock()
        mock_instance.search.return_value = [
            {
                "title": "Test",
                "url": "https://test.com",
                "content": "Content",
                "score": 0.8
            }
        ]
        mock_tavily_class.return_value = mock_instance

        # Call tool function
        result = web_search("test query")

        # Assertions
        assert "Test" in result
        assert "https://test.com" in result
        mock_instance.search.assert_called_once_with("test query")


@pytest.mark.unit
class TestDataLoaders:
    """Tests for data loading utilities."""

    def test_load_csv_companies(self, sample_csv_path):
        """Test loading companies from CSV."""
        companies = load_csv_companies(str(sample_csv_path))

        assert len(companies) == 3
        assert companies[0]["Company Name"] == "BitMovin"
        assert companies[1]["Company Name"] == "Notion"
        assert companies[2]["Company Name"] == "Stripe"

        # Check all columns are present
        assert "Website" in companies[0]
        assert "Industry" in companies[0]

    def test_load_csv_companies_file_not_found(self):
        """Test CSV loading handles missing file."""
        with pytest.raises(FileNotFoundError):
            load_csv_companies("/nonexistent/file.csv")

    def test_load_csv_companies_invalid_format(self, tmp_path):
        """Test CSV loading handles invalid format."""
        # Create invalid CSV (missing required column)
        invalid_csv = tmp_path / "invalid.csv"
        invalid_csv.write_text("Name,NotTheRightColumn\nTest,Value")

        with pytest.raises(KeyError):
            companies = load_csv_companies(str(invalid_csv))
            # Try to access expected column
            _ = companies[0]["Company Name"]

    def test_load_instructions(self, sample_instructions_path):
        """Test loading instructions from markdown file."""
        instructions = load_instructions(str(sample_instructions_path))

        assert "Research Instructions" in instructions
        assert "Industry" in instructions
        assert "Products" in instructions
        assert "Funding" in instructions

    def test_load_instructions_file_not_found(self):
        """Test instructions loading handles missing file."""
        with pytest.raises(FileNotFoundError):
            load_instructions("/nonexistent/instructions.md")

    def test_load_instructions_empty_file(self, tmp_path):
        """Test instructions loading handles empty file."""
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("")

        instructions = load_instructions(str(empty_file))
        assert instructions == ""

    def test_get_company_names(self, sample_csv_path):
        """Test extracting company names from CSV."""
        companies = load_csv_companies(str(sample_csv_path))
        names = get_company_names(companies)

        assert len(names) == 3
        assert "BitMovin" in names
        assert "Notion" in names
        assert "Stripe" in names

    def test_get_company_names_empty_list(self):
        """Test company name extraction with empty list."""
        names = get_company_names([])
        assert len(names) == 0


@pytest.mark.unit
class TestModels:
    """Tests for Pydantic models."""

    def test_search_result_model(self):
        """Test SearchResult model validation."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            content="Test content",
            relevance_score=0.85
        )

        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.content == "Test content"
        assert result.relevance_score == 0.85

    def test_search_result_model_optional_score(self):
        """Test SearchResult with optional score."""
        result = SearchResult(
            title="Test",
            url="https://example.com",
            content="Content"
        )

        assert result.relevance_score is None

    def test_company_info_model(self):
        """Test CompanyInfo model validation."""
        info = CompanyInfo(
            company_name="Test Company",
            industry="Technology",
            company_size="50-100 employees",
            headquarters="Austin, TX",
            products=["Product A", "Product B"],
            competitors=["Competitor 1", "Competitor 2"],
            revenue="$5M-$10M",
            funding_stage="Series A",
            growth_stage="Startup",
            growth_stage_reason="Raised Series A in 2024 and still expanding core product market fit.",
            industry_vertical="SaaS (SMB/Scale)",
            industry_vertical_reason="Targets SMB customers with subscription workflow software.",
            sub_industry_vertical="AdTech/MarTech",
            sub_industry_vertical_reason="Platform optimizes digital marketing campaigns.",
            financial_health="VC-Funded (Early)",
            financial_health_reason="Seed and Series A rounds disclosed totalling $18M.",
            business_and_technology_adoption="Digitally-Transforming",
            business_and_technology_adoption_reason="Clients adopt service to modernize marketing analytics.",
            company_size_reason="LinkedIn headcount sits at 65 employees as of April 2025.",
            buyer_journey="Hybrid",
            buyer_journey_reason="Engineers trial the API before procurement negotiates contracts.",
            budget_maturity="Team Budget",
            budget_maturity_reason="Marketing ops leaders approve spend for departmental tooling.",
            cloud_spend_capacity="$5K-$50K/month",
            cloud_spend_capacity_reason="Customer case studies cite mid-market spend profiles.",
            procurement_process="Lightweight Review",
            procurement_process_reason="Security checklist completed through short vendor questionnaire.",
            key_personas=["Head of Marketing Operations", "Lead Growth Engineer"],
            key_personas_reason="These roles evaluate attribution tooling and own budget approvals."
        )

        assert info.company_name == "Test Company"
        assert len(info.products) == 2
        assert len(info.competitors) == 2
        assert info.growth_stage == "Startup"
        assert info.growth_stage_reason
        assert info.key_personas_reason

    def test_company_info_model_missing_required_field(self):
        """Test CompanyInfo validation fails for missing fields."""
        with pytest.raises(ValueError):
            CompanyInfo(
                company_name="Test",
                # Missing required fields
            )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.requires_api
class TestWebSearchIntegration:
    """Integration tests for web search (requires API keys)."""

    @pytest.mark.skipif(
        not pytest.config.getoption("--run-integration", default=False),
        reason="Integration tests disabled"
    )
    def test_tavily_search_real_api(self):
        """Test Tavily search with real API (if key available)."""
        import os
        api_key = os.getenv("TAVILY_API_KEY")

        if not api_key:
            pytest.skip("TAVILY_API_KEY not available")

        searcher = TavilySearch(api_key=api_key)
        results = searcher.search("Python programming language")

        assert len(results) > 0
        assert "title" in results[0]
        assert "url" in results[0]
        assert "content" in results[0]

    @pytest.mark.skipif(
        not pytest.config.getoption("--run-integration", default=False),
        reason="Integration tests disabled"
    )
    def test_serper_search_real_api(self):
        """Test Serper search with real API (if key available)."""
        import os
        api_key = os.getenv("SERPER_API_KEY")

        if not api_key:
            pytest.skip("SERPER_API_KEY not available")

        searcher = SerperSearch(api_key=api_key)
        results = searcher.search("Python programming language")

        assert len(results) > 0
        assert "title" in results[0]
        assert "url" in results[0]


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require API keys"
    )
