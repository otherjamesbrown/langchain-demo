# Contributing to LangChain Research Agent

Thank you for your interest in contributing!

## Development Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy environment template:
   ```bash
   cp config/env.example .env
   # Edit .env with your configuration
   ```

## Development Workflow

### Code Standards

- Follow PEP 8 style guide
- Include type hints for all functions and classes
- Write docstrings for all functions and classes
- Add inline comments for complex logic
- Keep code maintainable and production-ready

### Testing

- Test code as you build it
- Use example data from `examples/` directory
- Verify both local and remote model configurations work
- Write tests in `tests/` directory
- Run tests: `pytest tests/`

### Pull Request Process

1. Create a feature branch from `main`
2. Make your changes following code standards
3. Write or update tests as needed
4. Ensure all tests pass
5. Update documentation if necessary
6. Submit pull request with clear description

## Code Structure

The project follows a modular structure:

- `src/agent/` - Research agent implementation
- `src/tools/` - LangChain tools
- `src/models/` - Model abstraction layer
- `src/database/` - Database operations
- `src/utils/` - Shared utilities

## Questions?

If you have questions:
- LangChain concepts: [LangChain documentation](https://python.langchain.com/)
- This project: Review PRD.md and README.md
- Setup issues: Check troubleshooting sections
