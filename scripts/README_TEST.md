# Testing the Research Agent

## Quick Start

To test the research agent with the three companies (BitMovin, Hydrolix, Queue-it):

```bash
# From project root
python scripts/test_companies.py
```

## Configuration

Make sure you have set up your `.env` file with required API keys:

1. **Web Search API** (Required):
   - `TAVILY_API_KEY` or `SERPER_API_KEY`

2. **Model Configuration** (Choose one):
   - Local model: `MODEL_TYPE=local` and `MODEL_PATH=./models/your-model.gguf`
   - OpenAI: `MODEL_TYPE=openai` and `OPENAI_API_KEY=your-key`
   - Anthropic: `MODEL_TYPE=anthropic` and `ANTHROPIC_API_KEY=your-key`
   - Gemini: `MODEL_TYPE=gemini` and `GOOGLE_API_KEY=your-key`

## Command Options

```bash
# Use specific companies (instead of CSV)
python scripts/test_companies.py --companies BitMovin Hydrolix Queue-it

# Use a specific model type
python scripts/test_companies.py --model-type openai

# Disable verbose output
python scripts/test_companies.py --no-verbose

# Don't save to database
python scripts/test_companies.py --no-db
```

## Example Output

The script will:
1. Load companies from `examples/companies/sample_companies.csv`
2. Initialize the database (if enabled)
3. Research each company using web search
4. Display results and save to database
5. Show a summary with execution times

## Requirements

- Python 3.10+
- All dependencies from `requirements.txt` installed
- Valid API keys in `.env` file
- For local models: model file must exist at `MODEL_PATH`

