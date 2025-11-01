"""
Pytest configuration and shared fixtures.

This module provides common fixtures and configuration for all tests.
"""

import os
import sys
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.schema import Base


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return path to test data directory."""
    test_dir = Path(__file__).parent / "test_data"
    test_dir.mkdir(exist_ok=True)
    return test_dir


@pytest.fixture(scope="session")
def sample_csv_path(test_data_dir: Path) -> Path:
    """Create a sample CSV file for testing."""
    csv_path = test_data_dir / "test_companies.csv"
    csv_content = """Company Name,Website,Industry
BitMovin,https://bitmovin.com,Video Technology
Notion,https://notion.so,Productivity Software
Stripe,https://stripe.com,Payment Processing
"""
    csv_path.write_text(csv_content)
    return csv_path


@pytest.fixture(scope="session")
def sample_instructions_path(test_data_dir: Path) -> Path:
    """Create a sample instructions file for testing."""
    md_path = test_data_dir / "test_instructions.md"
    md_content = """# Research Instructions

Please research the following aspects of each company:

1. **Industry**: What industry does the company operate in?
2. **Products**: What are their main products or services?
3. **Funding**: What is their funding status?
4. **Company Size**: How many employees do they have?
5. **Competitors**: Who are their main competitors?
"""
    md_path.write_text(md_content)
    return md_path


@pytest.fixture(scope="function")
def test_db_session() -> Generator[Session, None, None]:
    """Create a test database session with isolated tables."""
    # Use in-memory SQLite database for tests
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Create all tables
    Base.metadata.create_all(engine)

    # Create session
    TestSession = sessionmaker(bind=engine)
    session = TestSession()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(scope="function")
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for testing."""
    test_env = {
        "MODEL_TYPE": "local",
        "MODEL_PATH": "./models/test-model.gguf",
        "DATABASE_PATH": ":memory:",
        "LOG_LEVEL": "DEBUG",
        "TAVILY_API_KEY": "test_tavily_key",
        "SERPER_API_KEY": "test_serper_key",
        "OPENAI_API_KEY": "test_openai_key",
        "ANTHROPIC_API_KEY": "test_anthropic_key",
        "GOOGLE_API_KEY": "test_google_key",
        "LANGCHAIN_API_KEY": "test_langsmith_key",
        "LANGCHAIN_TRACING_V2": "false",
    }

    for key, value in test_env.items():
        monkeypatch.setenv(key, value)

    return test_env


@pytest.fixture
def mock_search_results():
    """Return mock search results for testing."""
    return [
        {
            "title": "BitMovin - Video Infrastructure",
            "url": "https://bitmovin.com",
            "content": "BitMovin provides video encoding and streaming infrastructure for OTT platforms.",
            "score": 0.95
        },
        {
            "title": "BitMovin Raises $25M Series B",
            "url": "https://techcrunch.com/bitmovin-funding",
            "content": "BitMovin announced $25M Series B funding led by Atomico.",
            "score": 0.88
        },
        {
            "title": "About BitMovin",
            "url": "https://bitmovin.com/about",
            "content": "Founded in 2013, BitMovin has 200+ employees across offices in San Francisco, Vienna, and Chicago.",
            "score": 0.82
        }
    ]


@pytest.fixture
def mock_llm_response():
    """Return mock LLM response for testing."""
    return {
        "company_name": "BitMovin",
        "industry": "Video Technology",
        "products": ["Video Encoding", "Streaming Infrastructure", "Analytics"],
        "funding_status": "Series B - $25M",
        "company_size": "200+ employees",
        "competitors": ["Mux", "Cloudflare Stream", "AWS Elemental"],
        "summary": "BitMovin is a video infrastructure company providing encoding and streaming solutions."
    }


# Configure pytest
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "requires_api: marks tests that require API keys"
    )
    config.addinivalue_line(
        "markers", "requires_model: marks tests that require a local model"
    )
