# Test Suite

This directory contains the comprehensive test suite for the LangChain Research Agent project.

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Pytest configuration and shared fixtures
├── pytest.ini                  # Pytest settings
├── README.md                   # This file
├── test_models.py              # Tests for model factory and LLM integrations
├── test_tools.py               # Tests for web search and data loaders
├── test_database.py            # Tests for database schema and operations
├── test_utils.py               # Tests for logging, metrics, monitoring
├── test_research.py            # Tests for research agent and two-phase architecture
└── test_data/                  # Test fixtures (auto-generated)
    ├── test_companies.csv
    └── test_instructions.md
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_models.py
pytest tests/test_database.py
```

### Run Specific Test Class

```bash
pytest tests/test_models.py::TestModelFactory
```

### Run Specific Test Function

```bash
pytest tests/test_models.py::TestModelFactory::test_list_available_providers
```

### Run with Verbose Output

```bash
pytest -v
```

### Run with Coverage Report

```bash
pytest --cov=src --cov-report=html --cov-report=term
```

This generates:
- Terminal coverage summary
- HTML report in `htmlcov/index.html`

## Test Markers

Tests are organized with markers for selective execution:

### Unit Tests (Fast)

```bash
pytest -m unit
```

### Integration Tests (Slower, may require API keys)

```bash
pytest -m integration
```

### Skip Slow Tests

```bash
pytest -m "not slow"
```

### Tests Requiring API Keys

```bash
pytest -m requires_api
```

### Tests Requiring Local Model

```bash
pytest -m requires_model
```

### Run Integration Tests with Real APIs

```bash
pytest --run-integration
```

**Note:** Integration tests are skipped by default. Use `--run-integration` flag to run them.

## Test Categories

### 1. Model Tests (`test_models.py`)

Tests for model factory and LLM integrations:
- ✅ Model factory initialization
- ✅ Local LLM loading (LlamaCpp)
- ✅ OpenAI integration
- ✅ Anthropic integration
- ✅ Google Gemini integration
- ✅ Model configuration validation
- ✅ Custom parameters

**Run:** `pytest tests/test_models.py`

### 2. Tools Tests (`test_tools.py`)

Tests for web search and data loading:
- ✅ Tavily search
- ✅ Serper search
- ✅ CSV loading
- ✅ Markdown instruction loading
- ✅ Error handling
- ✅ Pydantic model validation

**Run:** `pytest tests/test_tools.py`

### 3. Database Tests (`test_database.py`)

Tests for database operations:
- ✅ Schema creation (all 7 tables)
- ✅ CRUD operations
- ✅ Model relationships
- ✅ Query functions
- ✅ Data validation
- ✅ Search history
- ✅ Agent execution tracking
- ✅ Two-phase architecture tables

**Run:** `pytest tests/test_database.py`

### 4. Utilities Tests (`test_utils.py`)

Tests for logging, metrics, and monitoring:
- ✅ LLM call logging
- ✅ Metrics collection
- ✅ Token usage tracking
- ✅ Cost calculation
- ✅ Performance monitoring
- ✅ Callback handlers

**Run:** `pytest tests/test_utils.py`

### 5. Research Tests (`test_research.py`)

Tests for research agent and two-phase architecture:
- ✅ Query generation
- ✅ Search execution
- ✅ Prompt building
- ✅ LLM processing
- ✅ Validation utilities
- ✅ Two-phase workflows
- ✅ Research agent

**Run:** `pytest tests/test_research.py`

## Fixtures

### Database Fixtures

- `test_db_session`: In-memory SQLite database for testing
- Auto-created and torn down for each test

### Test Data Fixtures

- `test_data_dir`: Temporary directory for test data
- `sample_csv_path`: Sample companies CSV
- `sample_instructions_path`: Sample instructions markdown

### Mock Fixtures

- `mock_env_vars`: Mock environment variables
- `mock_search_results`: Mock web search results
- `mock_llm_response`: Mock LLM response

## Environment Setup

### 1. Install Test Dependencies

```bash
pip install -r requirements.txt
```

This includes:
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `pytest-mock` - Mocking utilities
- `pytest-cov` - Coverage reporting

### 2. Set Up Test Environment Variables

Tests use mocked environment variables by default. For integration tests with real APIs:

```bash
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"
export TAVILY_API_KEY="your-key"
export SERPER_API_KEY="your-key"
```

### 3. Run Tests

```bash
# Unit tests only (default, fast)
pytest -m unit

# All tests including integration (requires API keys)
pytest --run-integration
```

## Test Coverage

To check test coverage:

```bash
pytest --cov=src --cov-report=term-missing
```

This shows which lines are not covered by tests.

### Coverage Goals

- **Target:** 80%+ coverage for core modules
- **Priority Areas:**
  - Model factory: 90%+
  - Database operations: 85%+
  - Tools: 85%+
  - Research workflows: 75%+

## Writing New Tests

### Test File Naming

- Name test files: `test_<module>.py`
- Match source structure: `src/models/` → `tests/test_models.py`

### Test Function Naming

```python
def test_<feature>_<scenario>():
    """Test description."""
    # Arrange
    # Act
    # Assert
```

### Using Fixtures

```python
def test_something(test_db_session, mock_env_vars):
    """Test that uses fixtures."""
    # Fixtures are automatically injected
    assert test_db_session is not None
```

### Marking Tests

```python
@pytest.mark.unit
def test_fast_unit():
    """Fast unit test."""
    pass

@pytest.mark.integration
@pytest.mark.slow
def test_slow_integration():
    """Slow integration test."""
    pass

@pytest.mark.requires_api
def test_with_api():
    """Test requiring real API."""
    pass
```

### Mocking Examples

```python
from unittest.mock import Mock, patch

@patch("src.models.model_factory.LlamaCpp")
def test_with_mock(mock_llama):
    """Test with mocked dependency."""
    mock_llama.return_value = Mock()
    # Test code
```

## Continuous Integration

### GitHub Actions (Recommended Setup)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pytest -m unit
      - run: pytest --cov=src --cov-report=xml
```

### Pre-commit Hook (Optional)

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
pytest -m unit
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

## Troubleshooting

### Import Errors

If you see import errors:

```bash
# Ensure project root is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}"
pytest
```

### Database Errors

Tests use in-memory SQLite. If you see database errors:
- Check that `test_db_session` fixture is used
- Ensure session is properly closed

### API Key Warnings

Integration tests skip if API keys aren't available. This is expected behavior.

To run integration tests:

```bash
# Set API keys first
export OPENAI_API_KEY="your-key"

# Then run with flag
pytest --run-integration
```

## Best Practices

1. **Keep tests isolated** - Each test should be independent
2. **Use fixtures** - Avoid code duplication
3. **Mock external calls** - Don't hit real APIs in unit tests
4. **Test edge cases** - Test both success and failure paths
5. **Clear test names** - Make test purpose obvious
6. **Fast unit tests** - Keep unit tests under 1 second each
7. **Document complex tests** - Add docstrings explaining intent

## Test Statistics

Run `pytest --collect-only` to see test count:

```bash
pytest --collect-only
```

Current test count:
- **Model tests:** ~15 tests
- **Tools tests:** ~15 tests
- **Database tests:** ~20 tests
- **Utils tests:** ~15 tests
- **Research tests:** ~15 tests
- **Total:** ~80+ tests

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure tests pass: `pytest`
3. Check coverage: `pytest --cov=src`
4. Add integration tests if applicable
5. Update this README if needed

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py](https://coverage.readthedocs.io/)
