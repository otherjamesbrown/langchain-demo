"""
Validation utilities for comparing and evaluating processing runs.

This module provides tools for validating outputs, comparing models,
and tracking quality metrics.
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from src.database.schema import ProcessingRun, ValidationResult
from src.utils.database import get_db_session
from src.tools.models import CompanyInfo


def validate_completeness(processing_run: ProcessingRun) -> ValidationResult:
    """
    Validate completeness of extracted information.
    
    Checks if all required fields are present in the output.
    
    Args:
        processing_run: ProcessingRun to validate
        
    Returns:
        ValidationResult record
    """
    if not processing_run.output:
        score = 0.0
        details = {"error": "No output to validate"}
    else:
        output = processing_run.output
        
        # Required fields
        required_fields = [
            "company_name", "industry", "company_size", "headquarters"
        ]
        
        # Optional but important fields
        important_fields = [
            "founded", "products", "competitors", "revenue"
        ]
        
        required_present = sum(1 for field in required_fields if output.get(field))
        important_present = sum(1 for field in important_fields if output.get(field))
        
        # Score: 50% for required, 50% for important
        required_score = (required_present / len(required_fields)) * 0.5
        important_score = (important_present / len(important_fields)) * 0.5
        score = required_score + important_score
        
        details = {
            "required_fields": {field: bool(output.get(field)) for field in required_fields},
            "important_fields": {field: bool(output.get(field)) for field in important_fields},
            "required_completeness": required_present / len(required_fields),
            "important_completeness": important_present / len(important_fields)
        }
    
    with get_db_session() as session:
        validation = ValidationResult(
            processing_run_id=processing_run.id,
            validation_type="completeness",
            score=score,
            details=details,
            validated_by="automated"
        )
        session.add(validation)
        session.commit()
        return validation


def compare_processing_runs(
    processing_runs: List[ProcessingRun]
) -> Dict:
    """
    Compare multiple processing runs (e.g., different models on same data).
    
    Args:
        processing_runs: List of ProcessingRun objects to compare
        
    Returns:
        Dictionary with comparison results
    """
    if not processing_runs:
        return {"error": "No processing runs to compare"}
    
    comparison = {
        "num_runs": len(processing_runs),
        "runs": []
    }
    
    for run in processing_runs:
        run_info = {
            "id": run.id,
            "model": f"{run.llm_provider}/{run.llm_model}",
            "success": run.success,
            "execution_time": run.execution_time_seconds,
            "has_output": bool(run.output)
        }
        
        if run.output:
            # Extract key fields for comparison
            run_info["fields"] = {
                "industry": run.output.get("industry"),
                "company_size": run.output.get("company_size"),
                "headquarters": run.output.get("headquarters"),
                "founded": run.output.get("founded")
            }
        
        comparison["runs"].append(run_info)
    
    # Check for consensus (fields that match across runs)
    if len(processing_runs) > 1 and all(r.output for r in processing_runs):
        consensus = {}
        key_fields = ["industry", "company_size", "headquarters", "founded"]
        
        for field in key_fields:
            values = [r.output.get(field) for r in processing_runs if r.output.get(field)]
            if len(set(values)) == 1:
                consensus[field] = values[0]
        
        comparison["consensus"] = consensus
        comparison["consensus_rate"] = len(consensus) / len(key_fields)
    
    return comparison


def validate_processing_run(
    processing_run_id: int,
    validation_types: Optional[List[str]] = None
) -> List[ValidationResult]:
    """
    Run validation on a processing run.
    
    Args:
        processing_run_id: ID of ProcessingRun to validate
        validation_types: List of validation types to run. If None, runs all
        
    Returns:
        List of ValidationResult records
    """
    if validation_types is None:
        validation_types = ["completeness"]
    
    with get_db_session() as session:
        processing_run = session.query(ProcessingRun).filter_by(id=processing_run_id).first()
        if not processing_run:
            raise ValueError(f"ProcessingRun {processing_run_id} not found")
    
    results = []
    
    if "completeness" in validation_types:
        results.append(validate_completeness(processing_run))
    
    # Add more validation types here as needed
    
    return results


def get_validation_summary(processing_run_id: int) -> Dict:
    """
    Get validation summary for a processing run.
    
    Args:
        processing_run_id: ProcessingRun ID
        
    Returns:
        Dictionary with validation summary
    """
    with get_db_session() as session:
        validations = session.query(ValidationResult).filter_by(
            processing_run_id=processing_run_id
        ).all()
        
        if not validations:
            return {"message": "No validations found"}
        
        summary = {
            "processing_run_id": processing_run_id,
            "num_validations": len(validations),
            "validations": {}
        }
        
        for validation in validations:
            summary["validations"][validation.validation_type] = {
                "score": validation.score,
                "validated_by": validation.validated_by,
                "created_at": str(validation.created_at)
            }
        
        # Calculate average score
        scores = [v.score for v in validations if v.score is not None]
        if scores:
            summary["average_score"] = sum(scores) / len(scores)
        
        return summary

