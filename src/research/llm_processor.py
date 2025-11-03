"""
LLM processor for Phase 2: Processing search results through LLMs.

This module processes search results through LLMs and stores all metadata,
enabling model comparison and prompt versioning.
"""

import time
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import PydanticOutputParser

from src.database.schema import ProcessingRun, SearchHistory
from src.utils.database import get_db_session
from src.models.model_factory import get_llm
from src.tools.models import CompanyInfo
import os
import json


def process_with_llm(
    prompt: str,
    company_name: str,
    search_result_ids: list[int],
    llm_model: str,
    llm_provider: str,
    prompt_version: Optional[str] = None,
    instructions_source: Optional[str] = None,
    temperature: float = 0.7,
    session: Optional[Session] = None
) -> ProcessingRun:
    """
    Process search results through an LLM and store results.
    
    Args:
        prompt: Complete prompt with instructions and search results
        company_name: Company being researched
        search_result_ids: List of SearchHistory IDs used in prompt
        llm_model: Model name (e.g., "gpt-4", "claude-3-opus")
        llm_provider: Provider type ('openai', 'anthropic', 'local', 'gemini')
        prompt_version: Optional prompt version hash
        instructions_source: Optional path to instructions file
        temperature: LLM temperature setting
        session: Optional database session
        
    Returns:
        ProcessingRun record with output
    """
    start_time = time.time()
    
    try:
        with get_db_session(session) as db_session:
            # Get LLM instance
            llm = get_llm(model_type=llm_provider, temperature=temperature)
            
            # Prepare input context (for storage)
            input_context = {
                "prompt_length": len(prompt),
                "num_search_results": len(search_result_ids),
                "search_result_ids": search_result_ids
            }
            
            # Execute LLM
            print(f"Processing {company_name} with {llm_provider}/{llm_model}...")
            raw_output = llm.invoke(prompt)
            
            execution_time = time.time() - start_time
            
            # Try to parse structured output
            try:
                parser = PydanticOutputParser(pydantic_object=CompanyInfo)
                # Note: This may need adjustment based on actual LLM output format
                company_info = _parse_llm_output(raw_output, company_name)
            except Exception as e:
                print(f"Warning: Failed to parse structured output: {e}")
                company_info = None
            
            # Create processing run record
            processing_run = ProcessingRun(
                company_name=company_name,
                prompt_version=prompt_version,
                prompt_template=prompt,  # Store full prompt
                instructions_source=instructions_source,
                llm_model=llm_model,
                llm_provider=llm_provider,
                temperature=temperature,
                search_result_ids=search_result_ids,
                input_context=input_context,
                output=company_info.model_dump() if company_info else None,
                raw_output=str(raw_output),
                execution_time_seconds=execution_time,
                success=True
            )
            
            db_session.add(processing_run)
            db_session.commit()
            
            print(f"✓ Completed in {execution_time:.2f}s")
            return processing_run
            
    except Exception as e:
        execution_time = time.time() - start_time
        
        # Record failed processing in a new session if original failed
        with get_db_session() as db_session:
            processing_run = ProcessingRun(
                company_name=company_name,
                prompt_version=prompt_version,
                prompt_template=prompt[:1000] if len(prompt) > 1000 else prompt,  # Truncate if too long
                instructions_source=instructions_source,
                llm_model=llm_model,
                llm_provider=llm_provider,
                temperature=temperature,
                search_result_ids=search_result_ids,
                execution_time_seconds=execution_time,
                success=False,
                error_message=str(e)
            )
            
            db_session.add(processing_run)
            db_session.commit()
        
        raise Exception(f"LLM processing failed: {str(e)}")


def _parse_llm_output(raw_output: Any, company_name: str) -> CompanyInfo:
    """
    Parse LLM output into structured CompanyInfo.
    
    This is a basic parser - can be enhanced with better extraction logic.
    
    Args:
        raw_output: Raw LLM response
        company_name: Company name
        
    Returns:
        CompanyInfo object
    """
    # Convert to string if needed
    if hasattr(raw_output, 'content'):
        text = raw_output.content
    else:
        text = str(raw_output)
    
    # Basic extraction (this could be improved)
    # For now, create minimal CompanyInfo with what we can extract
    return CompanyInfo(
        company_name=company_name,
        industry=_extract_field(text, ["industry", "sector"]),
        company_size=_extract_field(text, ["employees", "company size", "headcount"]),
        headquarters=_extract_field(text, ["headquarters", "based in", "located in"]),
        revenue=None,  # Could add extraction logic
        founded=None,  # Could add extraction logic
        products=[],  # Could add extraction logic
        competitors=[],  # Could add extraction logic
        funding_stage=None,
        description=text[:1000] if len(text) > 1000 else text
    )


def _extract_field(text: str, keywords: list[str]) -> str:
    """Extract a field from text using keywords."""
    text_lower = text.lower()
    for keyword in keywords:
        idx = text_lower.find(keyword)
        if idx != -1:
            # Extract surrounding context
            start = max(0, idx - 50)
            end = min(len(text), idx + 200)
            return text[start:end].strip()
    return ""


def process_company_with_multiple_models(
    company_name: str,
    prompt: str,
    search_result_ids: list[int],
    models: list[Dict[str, Any]],
    prompt_version: Optional[str] = None,
    instructions_source: Optional[str] = None
) -> list[ProcessingRun]:
    """
    Process same company/prompt with multiple LLM models for comparison.
    
    Args:
        company_name: Company name
        prompt: Prompt to use
        search_result_ids: Search result IDs
        models: List of model configs, e.g., [
            {"provider": "openai", "model": "gpt-4", "temperature": 0.7},
            {"provider": "anthropic", "model": "claude-3-opus", "temperature": 0.7}
        ]
        prompt_version: Optional prompt version
        instructions_source: Optional instructions file path
        
    Returns:
        List of ProcessingRun records
    """
    results = []
    
    for model_config in models:
        try:
            result = process_with_llm(
                prompt=prompt,
                company_name=company_name,
                search_result_ids=search_result_ids,
                llm_model=model_config["model"],
                llm_provider=model_config["provider"],
                temperature=model_config.get("temperature", 0.7),
                prompt_version=prompt_version,
                instructions_source=instructions_source
            )
            results.append(result)
        except Exception as e:
            print(f"Failed to process with {model_config['provider']}/{model_config['model']}: {e}")
            continue
    
    return results

