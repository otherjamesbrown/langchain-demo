"""
LLM Call Logging Utility

This module provides automatic logging of LLM calls to the database.
It integrates with the metrics tracking and stores call information
for monitoring and analysis.
"""

import os
import time
from typing import Optional, Dict, Any
from datetime import datetime

from src.database.schema import LLMCallLog, get_database_url
from src.database.operations import get_session
from src.utils.metrics import LLMMetrics
from sqlalchemy.orm import Session


class LLMLogger:
    """Logger for tracking LLM calls to the database."""
    
    def __init__(self, auto_log: bool = True):
        """
        Initialize LLM logger.
        
        Args:
            auto_log: If True, automatically log calls via decorator/context manager
        """
        self.auto_log = auto_log
        self.enabled = os.getenv("LOG_LLM_CALLS", "true").lower() == "true"
    
    def log_call(
        self,
        metrics: LLMMetrics,
        prompt: Optional[str] = None,
        response: Optional[str] = None,
        model_name: str = "",
        call_type: str = "invoke",
        agent_execution_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session: Optional[Session] = None
    ) -> Optional[LLMCallLog]:
        """
        Log an LLM call to the database.
        
        Args:
            metrics: LLMMetrics object with token usage and timing
            prompt: The prompt that was sent to the LLM
            response: The response from the LLM
            model_name: Name of the model used
            call_type: Type of call (invoke, stream, batch)
            agent_execution_id: Optional ID of the agent execution this call belongs to
            metadata: Additional metadata to store
            session: Optional database session (creates new if not provided)
        
        Returns:
            LLMCallLog object if logging successful, None otherwise
        """
        if not self.enabled:
            return None
        
        try:
            # Use provided session or create new one
            if session is None:
                db_session = get_session()
                should_close = True
            else:
                db_session = session
                should_close = False
            
            try:
                # Calculate tokens per second
                tokens_per_second = metrics.tokens_per_second()
                
                # Create log entry
                log_entry = LLMCallLog(
                    model_type=metrics.model_type,
                    model_name=model_name or metrics.model_name,
                    call_type=call_type,
                    agent_execution_id=agent_execution_id,
                    prompt_tokens=metrics.prompt_tokens,
                    completion_tokens=metrics.completion_tokens,
                    total_tokens=metrics.total_tokens,
                    generation_time_seconds=metrics.generation_time,
                    tokens_per_second=tokens_per_second,
                    prompt=prompt[:5000] if prompt and len(prompt) > 5000 else prompt,  # Truncate long prompts
                    prompt_length=len(prompt) if prompt else None,
                    response=response[:5000] if response and len(response) > 5000 else response,  # Truncate long responses
                    response_length=len(response) if response else None,
                    success=True,
                    extra_metadata=metadata or {}
                )
                
                db_session.add(log_entry)
                
                if should_close:
                    db_session.commit()
                    db_session.close()
                else:
                    db_session.flush()  # Don't commit, let caller handle it
                
                return log_entry
                
            except Exception as e:
                if should_close:
                    db_session.rollback()
                    db_session.close()
                raise e
                
        except Exception as e:
            # Logging failure shouldn't break the application
            print(f"Warning: Failed to log LLM call: {e}")
            return None
    
    def log_error(
        self,
        model_type: str,
        model_name: str,
        error_message: str,
        prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session: Optional[Session] = None
    ) -> Optional[LLMCallLog]:
        """
        Log a failed LLM call.
        
        Args:
            model_type: Type of model (local, openai, etc.)
            model_name: Name of the model
            error_message: Error message
            prompt: The prompt that was attempted
            metadata: Additional metadata
            session: Optional database session
        
        Returns:
            LLMCallLog object if logging successful
        """
        if not self.enabled:
            return None
        
        try:
            if session is None:
                db_session = get_session()
                should_close = True
            else:
                db_session = session
                should_close = False
            
            try:
                log_entry = LLMCallLog(
                    model_type=model_type,
                    model_name=model_name,
                    call_type="error",
                    prompt=prompt[:5000] if prompt and len(prompt) > 5000 else prompt,
                    prompt_length=len(prompt) if prompt else None,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    generation_time_seconds=0.0,
                    success=False,
                    error_message=error_message[:1000],  # Truncate long errors
                    extra_metadata=metadata or {}
                )
                
                db_session.add(log_entry)
                
                if should_close:
                    db_session.commit()
                    db_session.close()
                else:
                    db_session.flush()
                
                return log_entry
                
            except Exception as e:
                if should_close:
                    db_session.rollback()
                    db_session.close()
                raise e
                
        except Exception as e:
            print(f"Warning: Failed to log LLM error: {e}")
            return None


# Global logger instance
_llm_logger = LLMLogger()


def log_llm_call(
    metrics: LLMMetrics,
    prompt: Optional[str] = None,
    response: Optional[str] = None,
    **kwargs
) -> Optional[LLMCallLog]:
    """
    Convenience function to log an LLM call.
    
    Usage:
        metrics = LLMMetrics(...)
        log_llm_call(metrics, prompt="Hello", response="Hi there")
    """
    return _llm_logger.log_call(metrics, prompt=prompt, response=response, **kwargs)


def get_llm_logger() -> LLMLogger:
    """Get the global LLM logger instance."""
    return _llm_logger

