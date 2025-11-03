# Llama Diagnostics Guide

Complete guide to using the diagnostic logging system for troubleshooting Llama model truncation issues.

## Overview

The diagnostic logging system provides detailed insights into:
- **Model Initialization**: What parameters are passed to ChatLlamaCpp
- **Token Counts**: Estimated input/output token usage per iteration
- **Prompt Content**: Full prompts sent to the model
- **Response Content**: Complete responses with truncation detection
- **Context Budget**: Analysis of context window utilization
- **Generation Performance**: Timing and tokens-per-second metrics

## Quick Start

### Option 1: Enable in Streamlit UI

1. Navigate to the Agent page (`http://your-server:8501/Agent`)
2. In the sidebar, check **"Enable Diagnostics"**
3. Run your research as normal
4. Check the **console output** (where Streamlit is running) for diagnostic logs

**Note**: Diagnostic logs appear in the terminal/console where Streamlit is running, **not** in the web UI.

### Option 2: Use Command-Line Test Script

```bash
# Test with default company (BitMovin)
python scripts/test_llama_diagnostics.py

# Test with specific company
python scripts/test_llama_diagnostics.py "Queue-it"

# Customize max iterations
python scripts/test_llama_diagnostics.py BitMovin --max-iterations 3

# Specify model path manually
python scripts/test_llama_diagnostics.py BitMovin --model-path /path/to/model.gguf

# Run without diagnostics (for comparison)
python scripts/test_llama_diagnostics.py BitMovin --no-diagnostics
```

### Option 3: Programmatic Use

```python
from src.agent.research_agent import ResearchAgent

agent = ResearchAgent(
    model_type="local",
    verbose=True,
    max_iterations=5,
    enable_diagnostics=True,  # 🔍 Enable diagnostics
    model_kwargs={"max_tokens": 4096},
)

result = agent.research_company("BitMovin")
```

## Understanding the Output

### 1. Model Initialization Log

Appears once when the agent is created:

```
================================================================================
LLAMA MODEL INITIALIZATION
================================================================================
Model Path: /home/langchain/langchain-demo/models/meta-llama-3.1-8b-instruct.Q4_K_M.gguf
Model File Exists: True
Registry Context Window: 8192

ChatLlamaCpp Constructor Parameters:
  chat_format: llama-3
  max_tokens: 4096
  n_batch: 512
  n_ctx: 8192
  n_gpu_layers: -1
  n_predict: 4096
  temperature: 0.2
  verbose: False

🔍 TRUNCATION-RELEVANT PARAMETERS:
  n_ctx (context window):     8192
  max_tokens (max output):    4096
  n_predict (llama-cpp arg):  4096

📊 CAPACITY ANALYSIS:
  Total context budget:       8192 tokens
  Requested max output:       4096 tokens
  Available for input:        ~4096 tokens
================================================================================
```

**What to check**:
- ✅ `n_ctx` matches your model's context window (8192 for Llama 3.1 8B)
- ✅ `max_tokens` and `n_predict` are both set to reasonable values
- ✅ Available input space is sufficient for your prompts

### 2. Prompt Stats (Before Each Model Call)

```
--------------------------------------------------------------------------------
📤 PROMPT SENT - Iteration 1 (Model Call #1)
--------------------------------------------------------------------------------
Prompt Length (chars):     3524
Prompt Length (lines):     52
Estimated Tokens:          ~881

First 10 lines:
  1: [SystemMessage]: You are a focused company research analyst...
  2: 
  3: Research instructions (GTM playbook summary):
  ...

Last 10 lines:
  ...
  52: call the web_search_tool whenever you need fresh context.
--------------------------------------------------------------------------------
```

**What to check**:
- Estimated input tokens vs your `n_ctx` budget
- If estimated tokens + max_output_tokens > n_ctx, truncation will occur
- Prompt content to verify it's what you expect

### 3. Response Stats (After Each Model Call)

```
--------------------------------------------------------------------------------
📥 RESPONSE RECEIVED - Iteration 1 (Model Call #1)
--------------------------------------------------------------------------------
Response Length (chars):   245
Response Length (lines):   5
Estimated Tokens:          ~61
Generation Time:           2.45 seconds
Estimated Speed:           ~24.9 tokens/sec

⚠️  POSSIBLE TRUNCATION DETECTED:
  ✗ ends_mid_sentence: True
  ✗ incomplete_json: True

Last 15 lines of response:
  1: Based on the web search tool, here's what I found about BitMovin:
  2: 
  3: Company Name: Bitmovin
  4: Industry: Digital Media and Entertainment...
  5: [truncated at] ...Bitmovin offers a range of products,
--------------------------------------------------------------------------------
```

**What to check**:
- ⚠️ Truncation indicators (ends mid-sentence, incomplete JSON, etc.)
- Generation speed (should be 20-100 tokens/sec depending on hardware)
- Whether response is unusually short

### 4. Context Budget Analysis (After Agent Completes)

```
================================================================================
📊 CONTEXT BUDGET ANALYSIS
================================================================================
Context Window (n_ctx):           8192 tokens
Max Output Requested (max_tokens): 4096 tokens

Estimated Token Usage:
  Input (prompt):                 ~3245 tokens
  Output (response):              ~245 tokens
  Total Used:                     ~3490 tokens
  Remaining Available:            ~4702 tokens
  Utilization:                    42.6%

✓ Context budget healthy (42.6% used)
================================================================================
```

**What to check**:
- 🚨 **If >90% full**: Context exhaustion likely causing truncation
- ⚠️ **If >75% full**: Monitor closely, may hit limits with longer responses
- ✅ **If <75%**: Context window not the issue

## Common Truncation Scenarios

### Scenario 1: Context Window Exhaustion

**Symptoms**:
- Budget analysis shows >90% utilization
- Truncation occurs consistently
- Input prompts are very long

**Solution**:
```python
# Reduce prompt size or increase context window
model_kwargs = {
    "n_ctx": 16384,  # Increase if model supports it
    "max_tokens": 4096
}
```

### Scenario 2: max_tokens Not Respected

**Symptoms**:
- Budget analysis shows plenty of space (<50% used)
- Truncation occurs early (< 500 tokens)
- Initialization shows `max_tokens: 4096` correctly set

**Possible Causes**:
- ChatLlamaCpp not accepting `max_tokens` parameter
- Need to use `n_predict` exclusively
- Version mismatch in `llama-cpp-python`

**Investigation Steps**:
```bash
# Check llama-cpp-python version
pip show llama-cpp-python

# Check langchain-community version
pip show langchain-community

# Try direct llama-cpp-python test (see section below)
```

### Scenario 3: Stop Sequences Triggering Early

**Symptoms**:
- Truncation at consistent points (e.g., always after "Thought:")
- Budget analysis shows low utilization
- Response ends cleanly but prematurely

**Investigation**:
- Check if agent framework is adding stop sequences
- Look for patterns in where truncation occurs
- May need to customize stop sequences

### Scenario 4: Model-Specific Behavior

**Symptoms**:
- Only affects certain models (e.g., Llama 3.1 but not Gemini)
- Parameters look correct
- Context budget healthy

**Possible Causes**:
- Model's chat template has implicit stop tokens
- Model trained with shorter response patterns
- Quantization affecting output quality

## Direct llama-cpp-python Testing

To isolate whether the issue is with LangChain or the underlying library:

```python
from llama_cpp import Llama

# Initialize model directly
llm = Llama(
    model_path="/path/to/model.gguf",
    n_ctx=8192,
    n_gpu_layers=-1,
    verbose=True,
)

# Test generation
response = llm.create_completion(
    prompt="Research the company BitMovin and provide detailed information.",
    max_tokens=4096,
    temperature=0.2,
)

print(f"Generated {len(response['choices'][0]['text'])} characters")
print(response['choices'][0]['text'])
```

If this works correctly but LangChain doesn't, the issue is in the LangChain wrapper.

## Reading Diagnostic Logs

### Where to Find Logs

**Streamlit UI**:
- Logs appear in the **terminal/console** where you ran `streamlit run`
- **Not** in the web browser UI
- Look for `[LLAMA-DIAG]` prefix

**Command-Line Script**:
- Logs appear directly in the terminal output
- Interleaved with agent execution messages

**Server/Remote**:
```bash
# SSH into server and tail the logs
ssh your-server
cd langchain-demo
tail -f logs/streamlit.log  # if you're redirecting output

# Or run Streamlit in foreground to see live output
streamlit run src/ui/Home.py
```

### Log Format

All diagnostic logs use this format:
```
2025-11-03 14:23:45 | [LLAMA-DIAG] | INFO | <message>
```

Levels:
- `INFO`: Normal diagnostic information
- `WARNING`: Potential issues detected (e.g., truncation indicators)
- `ERROR`: Critical issues (e.g., context window exceeded)

## Token Estimation Accuracy

The diagnostic tool uses a **rough heuristic** for token counting:
- **~4 characters per token** for English text
- This is an **estimate only**, not exact
- Actual tokenizer may vary ±20%

**Why not use the actual tokenizer?**
- Performance: Would slow down execution significantly
- Complexity: Requires loading tokenizer separately
- Goal: Quick diagnostics, not perfect accuracy

For exact token counts, use the actual tokenizer:
```python
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("meta-llama/Meta-Llama-3.1-8B-Instruct")
tokens = tokenizer.encode(text)
print(f"Exact token count: {len(tokens)}")
```

## Troubleshooting Tips

### 1. Compare with Working Model

Run the same company research with both Llama and Gemini:
```bash
# With diagnostics
python scripts/test_llama_diagnostics.py BitMovin

# Switch to Gemini in UI and run again
# Compare outputs and diagnostic info
```

### 2. Test with Minimal Prompt

Reduce prompt complexity to isolate the issue:
```python
agent = ResearchAgent(
    model_type="local",
    max_iterations=1,  # Just one iteration
    enable_diagnostics=True,
)
```

### 3. Check llama-cpp-python Verbose Output

Enable verbose mode in model initialization:
```python
model_kwargs = {
    "verbose": True,  # Shows llama-cpp-python internals
    "max_tokens": 4096,
}
```

### 4. Monitor GPU Memory

```bash
# On Linode GPU instance
nvidia-smi -l 1  # Update every second

# Check for OOM or memory pressure
```

### 5. Try Different Quantization

Some quantization formats handle long outputs better:
- Try Q5_K_M instead of Q4_K_M
- Try full precision if available
- Some quantizations may truncate more aggressively

## Next Steps for Investigation

Based on diagnostic output, here's where to investigate next:

| Symptom | Investigation |
|---------|--------------|
| Budget >90% full | Reduce prompt size or increase n_ctx |
| Budget <50%, still truncates | Check ChatLlamaCpp parameter handling |
| Consistent truncation point | Look for stop sequences |
| Works in direct test, fails in LangChain | LangChain wrapper issue |
| Slow generation (<10 tok/s) | GPU not being used, check n_gpu_layers |
| Perfect params, still truncates | Model-specific behavior, try different model |

## Reporting Issues

When reporting truncation issues, include:

1. **Model initialization log** (shows parameters)
2. **Last iteration's prompt/response logs** (shows truncation point)
3. **Context budget analysis** (shows utilization)
4. **Environment info**:
   - llama-cpp-python version
   - langchain-community version
   - Model file and quantization
   - GPU type (if using GPU)

## Disabling Diagnostics

Once you've identified the issue:

**In UI**: Uncheck "Enable Diagnostics"

**In code**: Remove or set to `False`:
```python
agent = ResearchAgent(
    enable_diagnostics=False,  # Disable
    ...
)
```

**In script**: Use `--no-diagnostics` flag:
```bash
python scripts/test_llama_diagnostics.py --no-diagnostics
```

## Performance Impact

Diagnostic logging has minimal performance impact:
- ~5-10ms overhead per model call (negligible)
- No impact on token generation speed
- Logs to console (buffered I/O, fast)
- Main cost is visual clutter in output

For production use, keep diagnostics disabled.

---

## Related Documentation

- [LLAMA_TRUNCATION_ISSUE.md](LLAMA_TRUNCATION_ISSUE.md) - Original issue report
- [LLM_LOGGING_GUIDE.md](LLM_LOGGING_GUIDE.md) - Database LLM call logging
- [LLM_COMPONENTS.md](LLM_COMPONENTS.md) - LLM architecture overview

## Support

If you're still experiencing truncation issues after using diagnostics:

1. Review diagnostic output carefully
2. Check related documentation above
3. Try the direct llama-cpp-python test
4. Consider filing an issue with diagnostic logs attached

