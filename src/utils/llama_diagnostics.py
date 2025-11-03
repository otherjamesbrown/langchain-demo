"""
Diagnostic utilities for troubleshooting Llama model truncation issues.

This module provides detailed logging and token counting to help identify
where and why the Llama 3.1 model is truncating output mid-generation.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

# Set up diagnostic logger with detailed formatting
diagnostic_logger = logging.getLogger("llama_diagnostics")
diagnostic_logger.setLevel(logging.DEBUG)

# Create handler if not already configured
if not diagnostic_logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s | [LLAMA-DIAG] | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    diagnostic_logger.addHandler(handler)


def estimate_token_count(text: str) -> int:
    """
    Rough estimate of token count for Llama models.
    
    Uses a simple heuristic: ~4 characters per token on average for English text.
    This is not precise but gives us a ballpark number for diagnostics.
    
    Args:
        text: Input text to estimate tokens for
        
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    # Rough heuristic: average 4 chars per token
    # LLama tokenizer typically produces 1 token per ~4 chars for English
    return max(len(text) // 4, 1)


def log_model_initialization(
    model_path: str,
    parameters: Dict[str, Any],
    context_window: Optional[int] = None,
) -> None:
    """
    Log detailed information about ChatLlamaCpp model initialization.
    
    Args:
        model_path: Path to the model file
        parameters: All parameters passed to ChatLlamaCpp constructor
        context_window: Expected context window from registry
    """
    diagnostic_logger.info("=" * 80)
    diagnostic_logger.info("LLAMA MODEL INITIALIZATION")
    diagnostic_logger.info("=" * 80)
    diagnostic_logger.info(f"Model Path: {model_path}")
    diagnostic_logger.info(f"Model File Exists: {Path(model_path).exists()}")
    
    if context_window:
        diagnostic_logger.info(f"Registry Context Window: {context_window}")
    
    diagnostic_logger.info("\nChatLlamaCpp Constructor Parameters:")
    for key, value in sorted(parameters.items()):
        if key == "model_path":
            continue  # Already logged above
        diagnostic_logger.info(f"  {key}: {value}")
    
    # Highlight key parameters for truncation debugging
    n_ctx = parameters.get("n_ctx", "NOT SET")
    max_tokens = parameters.get("max_tokens", "NOT SET")
    n_predict = parameters.get("n_predict", "NOT SET")
    
    diagnostic_logger.info("\n🔍 TRUNCATION-RELEVANT PARAMETERS:")
    diagnostic_logger.info(f"  n_ctx (context window):     {n_ctx}")
    diagnostic_logger.info(f"  max_tokens (max output):    {max_tokens}")
    diagnostic_logger.info(f"  n_predict (llama-cpp arg):  {n_predict}")
    
    # Calculate available output space
    if isinstance(n_ctx, int):
        if isinstance(max_tokens, int):
            diagnostic_logger.info(f"\n📊 CAPACITY ANALYSIS:")
            diagnostic_logger.info(f"  Total context budget:       {n_ctx} tokens")
            diagnostic_logger.info(f"  Requested max output:       {max_tokens} tokens")
            diagnostic_logger.info(f"  Available for input:        ~{n_ctx - max_tokens} tokens")
    
    diagnostic_logger.info("=" * 80)


def log_prompt_stats(
    prompt: str,
    iteration: int,
    model_call_count: int,
) -> None:
    """
    Log statistics about the prompt being sent to the model.
    
    Args:
        prompt: The full prompt text being sent
        iteration: Agent iteration number
        model_call_count: Total model calls so far
    """
    estimated_tokens = estimate_token_count(prompt)
    char_count = len(prompt)
    line_count = prompt.count("\n") + 1
    
    diagnostic_logger.info("-" * 80)
    diagnostic_logger.info(f"📤 PROMPT SENT - Iteration {iteration} (Model Call #{model_call_count})")
    diagnostic_logger.info("-" * 80)
    diagnostic_logger.info(f"Prompt Length (chars):     {char_count}")
    diagnostic_logger.info(f"Prompt Length (lines):     {line_count}")
    diagnostic_logger.info(f"Estimated Tokens:          ~{estimated_tokens}")
    
    # Show first/last few lines of prompt
    lines = prompt.split("\n")
    if len(lines) > 20:
        diagnostic_logger.info(f"\nFirst 10 lines:")
        for i, line in enumerate(lines[:10], 1):
            preview = line[:100] + "..." if len(line) > 100 else line
            diagnostic_logger.info(f"  {i}: {preview}")
        diagnostic_logger.info(f"\n  ... ({len(lines) - 20} middle lines omitted) ...")
        diagnostic_logger.info(f"\nLast 10 lines:")
        for i, line in enumerate(lines[-10:], len(lines) - 9):
            preview = line[:100] + "..." if len(line) > 100 else line
            diagnostic_logger.info(f"  {i}: {preview}")
    else:
        diagnostic_logger.info(f"\nFull prompt:")
        for i, line in enumerate(lines, 1):
            diagnostic_logger.info(f"  {i}: {line}")
    
    diagnostic_logger.info("-" * 80)


def log_response_stats(
    response: str,
    iteration: int,
    model_call_count: int,
    generation_time: float,
    is_final: bool = False,
) -> Dict[str, Any]:
    """
    Log statistics about the model response.
    
    Args:
        response: The response text from the model
        iteration: Agent iteration number
        model_call_count: Total model calls so far
        generation_time: Time taken to generate response (seconds)
        is_final: Whether this is the final response from the agent
        
    Returns:
        Dictionary with response statistics
    """
    estimated_tokens = estimate_token_count(response)
    char_count = len(response)
    line_count = response.count("\n") + 1
    tokens_per_sec = estimated_tokens / generation_time if generation_time > 0 else 0
    
    # Check for truncation indicators
    truncation_indicators = {
        "ends_mid_sentence": not response.rstrip().endswith((".", "!", "?", "}", "]", ")")),
        "ends_mid_word": response and response[-1].isalpha(),
        "incomplete_json": response.count("{") != response.count("}"),
        "incomplete_list": response.count("[") != response.count("]"),
    }
    likely_truncated = any(truncation_indicators.values())
    
    diagnostic_logger.info("-" * 80)
    diagnostic_logger.info(
        f"📥 RESPONSE RECEIVED - Iteration {iteration} (Model Call #{model_call_count})"
        + (" [FINAL]" if is_final else "")
    )
    diagnostic_logger.info("-" * 80)
    diagnostic_logger.info(f"Response Length (chars):   {char_count}")
    diagnostic_logger.info(f"Response Length (lines):   {line_count}")
    diagnostic_logger.info(f"Estimated Tokens:          ~{estimated_tokens}")
    diagnostic_logger.info(f"Generation Time:           {generation_time:.2f} seconds")
    diagnostic_logger.info(f"Estimated Speed:           ~{tokens_per_sec:.1f} tokens/sec")
    
    # Truncation analysis
    if likely_truncated:
        diagnostic_logger.warning("\n⚠️  POSSIBLE TRUNCATION DETECTED:")
        for indicator, detected in truncation_indicators.items():
            if detected:
                diagnostic_logger.warning(f"  ✗ {indicator}: {detected}")
    else:
        diagnostic_logger.info("\n✓ Response appears complete (no truncation indicators)")
    
    # Show end of response
    lines = response.split("\n")
    if len(lines) > 15:
        diagnostic_logger.info(f"\nLast 15 lines of response:")
        for i, line in enumerate(lines[-15:], len(lines) - 14):
            preview = line[:120] if len(line) > 120 else line
            diagnostic_logger.info(f"  {i}: {preview}")
    else:
        diagnostic_logger.info(f"\nFull response:")
        for i, line in enumerate(lines, 1):
            diagnostic_logger.info(f"  {i}: {line}")
    
    diagnostic_logger.info("-" * 80)
    
    return {
        "char_count": char_count,
        "line_count": line_count,
        "estimated_tokens": estimated_tokens,
        "generation_time": generation_time,
        "tokens_per_sec": tokens_per_sec,
        "likely_truncated": likely_truncated,
        "truncation_indicators": truncation_indicators,
    }


def log_agent_iteration_summary(
    iteration: int,
    total_iterations: int,
    agent_finished: bool,
    reason: Optional[str] = None,
) -> None:
    """
    Log summary at the end of each agent iteration.
    
    Args:
        iteration: Current iteration number
        total_iterations: Total iterations completed
        agent_finished: Whether the agent has finished
        reason: Reason for finishing (if applicable)
    """
    diagnostic_logger.info("=" * 80)
    diagnostic_logger.info(f"🔄 AGENT ITERATION {iteration} COMPLETE")
    diagnostic_logger.info("=" * 80)
    diagnostic_logger.info(f"Total Iterations So Far:   {total_iterations}")
    diagnostic_logger.info(f"Agent Finished:            {agent_finished}")
    if reason:
        diagnostic_logger.info(f"Finish Reason:             {reason}")
    diagnostic_logger.info("=" * 80)


def log_context_budget_analysis(
    n_ctx: int,
    estimated_input_tokens: int,
    estimated_output_tokens: int,
    max_tokens: int,
) -> None:
    """
    Analyze whether we're at risk of context window exhaustion.
    
    Args:
        n_ctx: Context window size
        estimated_input_tokens: Estimated tokens in input
        estimated_output_tokens: Estimated tokens in output
        max_tokens: Maximum tokens requested for output
    """
    total_estimated = estimated_input_tokens + estimated_output_tokens
    utilization_pct = (total_estimated / n_ctx) * 100 if n_ctx > 0 else 0
    remaining = n_ctx - total_estimated
    
    diagnostic_logger.info("=" * 80)
    diagnostic_logger.info("📊 CONTEXT BUDGET ANALYSIS")
    diagnostic_logger.info("=" * 80)
    diagnostic_logger.info(f"Context Window (n_ctx):           {n_ctx} tokens")
    diagnostic_logger.info(f"Max Output Requested (max_tokens): {max_tokens} tokens")
    diagnostic_logger.info(f"\nEstimated Token Usage:")
    diagnostic_logger.info(f"  Input (prompt):                 ~{estimated_input_tokens} tokens")
    diagnostic_logger.info(f"  Output (response):              ~{estimated_output_tokens} tokens")
    diagnostic_logger.info(f"  Total Used:                     ~{total_estimated} tokens")
    diagnostic_logger.info(f"  Remaining Available:            ~{remaining} tokens")
    diagnostic_logger.info(f"  Utilization:                    {utilization_pct:.1f}%")
    
    # Warning thresholds
    if utilization_pct > 90:
        diagnostic_logger.error("\n🚨 CRITICAL: Context window >90% full! Truncation likely!")
    elif utilization_pct > 75:
        diagnostic_logger.warning("\n⚠️  WARNING: Context window >75% full. Monitor closely.")
    elif total_estimated > n_ctx:
        diagnostic_logger.error(
            f"\n🚨 CRITICAL: Estimated usage ({total_estimated}) exceeds "
            f"context window ({n_ctx})! Truncation WILL occur!"
        )
    else:
        diagnostic_logger.info(f"\n✓ Context budget healthy ({utilization_pct:.1f}% used)")
    
    diagnostic_logger.info("=" * 80)


def save_diagnostic_snapshot(
    output_dir: Path,
    company_name: str,
    iteration_data: Dict[str, Any],
) -> Path:
    """
    Save a detailed snapshot of diagnostic data to disk for analysis.
    
    Args:
        output_dir: Directory to save snapshot to
        company_name: Name of company being researched
        iteration_data: Dictionary of diagnostic data
        
    Returns:
        Path to saved snapshot file
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_company_name = "".join(c if c.isalnum() else "_" for c in company_name)
    filename = f"llama_diagnostic_{safe_company_name}_{timestamp}.json"
    filepath = output_dir / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(iteration_data, f, indent=2, default=str)
    
    diagnostic_logger.info(f"💾 Diagnostic snapshot saved: {filepath}")
    return filepath

