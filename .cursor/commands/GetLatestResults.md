# Get Latest LLM Output Validation Test Results

Reference docs: `docs/infrastructure/SSH_ACCESS_GUIDE.md`, `docs/infrastructure/INFRASTRUCTURE_QUICK_REFERENCE.md`, `src/testing/prompt_analytics.py`, `src/ui/pages/5_🧪_LLM_Output_Validation.py`.

## 0. Prerequisites

- SSH access to the Linode server configured (see `docs/infrastructure/SSH_ACCESS_GUIDE.md`)
- Virtual environment activated on the server (or use `source venv/bin/activate` in commands)
- Database must exist on the server with test results (`data/research_agent.db`)

## 1. Quick Method: Use the Review Script (Recommended)

The easiest way to get the latest test results is to use the `review_latest_test_results.py` script:

```bash
# SSH to server and run the script
ssh linode-langchain-user "cd ~/langchain-demo && source venv/bin/activate && python3 scripts/review_latest_test_results.py"
```

**What it shows:**
- Latest 5 test runs with full details
- Accuracy scores (overall, required fields, weighted)
- Individual model performance comparisons
- Summary statistics across recent results

**Output format:**
- ✅ = 80%+ accuracy (good)
- ⚠️ = 50-79% accuracy (warning)
- ❌ = <50% accuracy (poor)

## 2. Alternative: Use the Streamlit UI

The Streamlit dashboard provides a visual interface for reviewing test results:

1. **Access the dashboard:**
   ```bash
   # Open in browser
   open http://172.234.181.156:8501
   # Or manually navigate to: http://172.234.181.156:8501
   ```

2. **Navigate to LLM Output Validation page:**
   - Click on "🧪 LLM Output Validation" in the sidebar
   - Or go directly to: http://172.234.181.156:8501/🧪_LLM_Output_Validation

3. **Review test results:**
   - **Tab 1 (Run Test)**: Run new validation tests
   - **Tab 2 (Compare Versions)**: Compare prompt versions across test runs
   - **Tab 3 (Cost Analysis)**: View cost breakdowns by prompt version, company, or model
   - **Tab 4 (Review Test)**: Select and review specific test runs with detailed field-level accuracy

## 3. Direct Database Query (Advanced)

For custom queries or programmatic access, you can query the database directly:

```bash
# SSH to server
ssh linode-langchain-user

# Activate virtual environment
cd ~/langchain-demo
source venv/bin/activate

# Run Python interactive session
python3
```

Then in Python:

```python
from src.database.schema import get_session
from src.testing.prompt_analytics import PromptAnalytics

session = get_session()

# Get latest 5 test runs
history = PromptAnalytics.get_test_run_history(limit=5)
for test_run in history:
    print(f"Test Run #{test_run['test_run_id']}: {test_run['company_name']}")
    print(f"  Overall Accuracy: {test_run.get('average_overall_accuracy', 'N/A')}%")
    print(f"  Created: {test_run['created_at']}")
    print()

# Compare prompt versions
comparison = PromptAnalytics.compare_prompt_versions(
    prompt_name="research-agent-prompt"
)
for version in comparison:
    print(f"{version['prompt_version']}: {version.get('average_overall_accuracy', 'N/A')}%")

session.close()
```

## 4. Understanding the Results

### Accuracy Metrics

- **Overall Accuracy**: Average accuracy across all fields (0-100%)
- **Required Fields Accuracy**: Average accuracy for required fields only
- **Optional Fields Accuracy**: Average accuracy for optional fields only
- **Weighted Accuracy**: Weighted average where critical fields count more

### Model Performance

Test results compare multiple models:
- **Google Gemini Flash Latest**: Fast, cost-effective grading model (also used as ground truth)
- **Meta Llama 3.1 8B**: Local quantized model (Q4_K_M)
- **Llama 2 7B Chat**: Older local quantized model (Q4_K_M)

### Test Run Structure

Each test run includes:
- **Ground Truth**: Gemini Pro output (used as reference)
- **Other Models**: All other available models tested against ground truth
- **Grading Results**: Field-by-field accuracy scores from Gemini Flash

## 5. Troubleshooting

### No test results found

If you see "❌ No test results found in database":

1. **Check if database exists:**
   ```bash
   ssh linode-langchain-user "ls -lh ~/langchain-demo/data/research_agent.db"
   ```

2. **Run a test first:**
   ```bash
   ssh linode-langchain-user "cd ~/langchain-demo && source venv/bin/activate && python3 scripts/run_llm_output_validation.py --company BitMovin"
   ```

### Script not found on server

If the script doesn't exist on the server:

1. **Copy it from local:**
   ```bash
   scp scripts/review_latest_test_results.py linode-langchain-user:~/langchain-demo/scripts/
   ```

2. **Or pull latest code:**
   ```bash
   ssh linode-langchain-user "cd ~/langchain-demo && git pull"
   ```

### Database connection errors

If you get database errors:

1. **Check database path:**
   ```bash
   ssh linode-langchain-user "cd ~/langchain-demo && source venv/bin/activate && python3 -c 'from src.database.schema import get_database_url; print(get_database_url())'"
   ```

2. **Verify database file permissions:**
   ```bash
   ssh linode-langchain-user "ls -la ~/langchain-demo/data/"
   ```

## 6. Related Commands

- **Run a new test:** See `scripts/run_llm_output_validation.py --help`
- **Compare prompt versions:** Use `PromptAnalytics.compare_prompt_versions()` in Python
- **Get cost analysis:** Use `PromptAnalytics.get_cost_analysis()` in Python
- **View in UI:** Access Streamlit dashboard at http://172.234.181.156:8501

## 7. Example Output

```
================================================================================
Latest LLM Output Validation Test Results
================================================================================

Found 5 recent test run(s):

================================================================================
Test Run #1: ID 6
================================================================================
Company: BitMovin
Prompt: research-agent-prompt@1.0
Test Suite: initial test
Created: 2025-11-05 11:59:46.647664
Outputs: 4
Grading Results: 3

📊 Accuracy Scores:
  Overall: ⚠️  54.1%
  Required Fields: ⚠️  54.3%
  Weighted: ⚠️  53.8%

📋 Model Results:
  Google Gemini Flash Latest (gemini): ⚠️  60.7%
    Required Fields: ✅ 81.0%
    Weighted: ⚠️  63.6%
  Meta Llama 3.1 8B Instruct (Q4_K_M) (local): ⚠️  56.8%
    Required Fields: ⚠️  52.0%
    Weighted: ⚠️  56.4%
  Llama 2 7B Chat (Q4_K_M) (local): ❌ 44.8%
    Required Fields: ❌ 30.0%
    Weighted: ❌ 41.4%
```

