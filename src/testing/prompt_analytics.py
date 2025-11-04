"""
Prompt Analytics Module

Provides analytics functions for comparing prompt versions and analyzing test results.

Educational: This module demonstrates how to query and aggregate test data to answer
questions like "Which prompt version performs best?" and "How has accuracy changed
over time?" This is essential for systematic prompt engineering.

Features:
- Compare accuracy across prompt versions
- Retrieve test run history
- Aggregate statistics by prompt version, company, or model
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from src.database.schema import (
    get_session,
    PromptVersion,
    TestRun,
    LLMOutputValidationResult,
    LLMOutputValidation,
)


class PromptAnalytics:
    """
    Analytics class for prompt version comparison and test run analysis.
    
    Educational: This class provides static methods for querying and aggregating
    test data. It uses SQLAlchemy ORM queries to efficiently retrieve and process
    test results from the database.
    """
    
    @staticmethod
    def compare_prompt_versions(
        prompt_name: str,
        company_name: Optional[str] = None,
        min_test_runs: int = 1,
        session: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Compare accuracy across different prompt versions.
        
        Educational: This function aggregates test results by prompt version,
        allowing you to see which version performs best. It calculates average
        accuracy scores across all test runs for each version.
        
        Args:
            prompt_name: Name of the prompt to compare (e.g., "research-agent-prompt")
            company_name: Optional filter by specific company
            min_test_runs: Minimum number of test runs required for a version to be included
            session: Optional database session (creates new one if not provided)
        
        Returns:
            List of dicts, each containing:
                - prompt_version: Version string (e.g., "1.0")
                - prompt_version_id: ID of the prompt version
                - test_runs_count: Number of test runs for this version
                - average_overall_accuracy: Average overall accuracy across all runs
                - average_required_fields_accuracy: Average required fields accuracy
                - average_optional_fields_accuracy: Average optional fields accuracy
                - average_weighted_accuracy: Average weighted accuracy
                - companies_tested: List of companies tested with this version
                - first_test_run: Date of first test run
                - latest_test_run: Date of most recent test run
        """
        db_session, should_close = _resolve_session(session)
        
        try:
            # Build base query - get test runs for this prompt
            query = db_session.query(
                TestRun.prompt_version,
                TestRun.prompt_version_id,
                func.count(TestRun.id).label('test_runs_count'),
                func.avg(LLMOutputValidationResult.overall_accuracy).label('avg_overall'),
                func.avg(LLMOutputValidationResult.required_fields_accuracy).label('avg_required'),
                func.avg(LLMOutputValidationResult.optional_fields_accuracy).label('avg_optional'),
                func.avg(LLMOutputValidationResult.weighted_accuracy).label('avg_weighted'),
                func.min(TestRun.created_at).label('first_test_run'),
                func.max(TestRun.created_at).label('latest_test_run'),
            ).join(
                LLMOutputValidationResult,
                TestRun.id == LLMOutputValidationResult.test_run_id
            ).filter(
                TestRun.prompt_name == prompt_name
            )
            
            # Optional filter by company
            if company_name:
                query = query.filter(TestRun.company_name == company_name)
            
            # Group by prompt version and filter by minimum test runs
            query = query.group_by(
                TestRun.prompt_version,
                TestRun.prompt_version_id
            ).having(
                func.count(TestRun.id) >= min_test_runs
            )
            
            # Order by latest test run (most recent first)
            query = query.order_by(func.max(TestRun.created_at).desc())
            
            results = query.all()
            
            # Get unique companies for each version
            version_data = []
            for result in results:
                # Get companies tested with this version
                companies_query = db_session.query(
                    TestRun.company_name
                ).filter(
                    TestRun.prompt_version_id == result.prompt_version_id
                ).distinct()
                
                if company_name:
                    companies_query = companies_query.filter(
                        TestRun.company_name == company_name
                    )
                
                companies = [row[0] for row in companies_query.all()]
                
                version_data.append({
                    'prompt_version': result.prompt_version,
                    'prompt_version_id': result.prompt_version_id,
                    'test_runs_count': result.test_runs_count,
                    'average_overall_accuracy': float(result.avg_overall) if result.avg_overall else None,
                    'average_required_fields_accuracy': float(result.avg_required) if result.avg_required else None,
                    'average_optional_fields_accuracy': float(result.avg_optional) if result.avg_optional else None,
                    'average_weighted_accuracy': float(result.avg_weighted) if result.avg_weighted else None,
                    'companies_tested': sorted(companies),
                    'first_test_run': result.first_test_run,
                    'latest_test_run': result.latest_test_run,
                })
            
            return version_data
            
        finally:
            if should_close:
                db_session.close()
    
    @staticmethod
    def get_test_run_history(
        prompt_name: Optional[str] = None,
        company_name: Optional[str] = None,
        prompt_version: Optional[str] = None,
        limit: Optional[int] = None,
        session: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical test runs with their results.
        
        Educational: This function retrieves test run history, allowing you to
        track how accuracy has changed over time. It includes metadata about
        each test run and optionally aggregates accuracy scores.
        
        Args:
            prompt_name: Optional filter by prompt name
            company_name: Optional filter by company name
            prompt_version: Optional filter by specific prompt version
            limit: Optional limit on number of results
            session: Optional database session (creates new one if not provided)
        
        Returns:
            List of dicts, each containing:
                - test_run_id: ID of the test run
                - test_name: Name of the test
                - company_name: Company tested
                - test_suite_name: Test suite name (if part of suite)
                - prompt_name: Name of the prompt used
                - prompt_version: Version of the prompt used
                - description: Test run description
                - created_at: When the test run was created
                - outputs_count: Number of model outputs in this test run
                - grading_results_count: Number of grading results
                - average_overall_accuracy: Average accuracy across all graded outputs
                - average_required_fields_accuracy: Average required fields accuracy
                - average_weighted_accuracy: Average weighted accuracy
        """
        db_session, should_close = _resolve_session(session)
        
        try:
            # Build base query
            query = db_session.query(TestRun)
            
            # Apply filters
            if prompt_name:
                query = query.filter(TestRun.prompt_name == prompt_name)
            
            if company_name:
                query = query.filter(TestRun.company_name == company_name)
            
            if prompt_version:
                query = query.filter(TestRun.prompt_version == prompt_version)
            
            # Order by most recent first
            query = query.order_by(TestRun.created_at.desc())
            
            # Apply limit
            if limit:
                query = query.limit(limit)
            
            test_runs = query.all()
            
            # Enrich with aggregated results
            history = []
            for test_run in test_runs:
                # Count outputs and grading results
                outputs_count = db_session.query(
                    func.count(LLMOutputValidation.id)
                ).filter(
                    LLMOutputValidation.test_run_id == test_run.id
                ).scalar() or 0
                
                grading_results_count = db_session.query(
                    func.count(LLMOutputValidationResult.id)
                ).filter(
                    LLMOutputValidationResult.test_run_id == test_run.id
                ).scalar() or 0
                
                # Get average accuracy scores
                accuracy_query = db_session.query(
                    func.avg(LLMOutputValidationResult.overall_accuracy).label('avg_overall'),
                    func.avg(LLMOutputValidationResult.required_fields_accuracy).label('avg_required'),
                    func.avg(LLMOutputValidationResult.weighted_accuracy).label('avg_weighted'),
                ).filter(
                    LLMOutputValidationResult.test_run_id == test_run.id
                )
                
                accuracy_result = accuracy_query.first()
                
                history.append({
                    'test_run_id': test_run.id,
                    'test_name': test_run.test_name,
                    'company_name': test_run.company_name,
                    'test_suite_name': test_run.test_suite_name,
                    'prompt_name': test_run.prompt_name,
                    'prompt_version': test_run.prompt_version,
                    'description': test_run.description,
                    'executed_by': test_run.executed_by,
                    'created_at': test_run.created_at,
                    'outputs_count': outputs_count,
                    'grading_results_count': grading_results_count,
                    'average_overall_accuracy': float(accuracy_result.avg_overall) if accuracy_result and accuracy_result.avg_overall else None,
                    'average_required_fields_accuracy': float(accuracy_result.avg_required) if accuracy_result and accuracy_result.avg_required else None,
                    'average_weighted_accuracy': float(accuracy_result.avg_weighted) if accuracy_result and accuracy_result.avg_weighted else None,
                })
            
            return history
            
        finally:
            if should_close:
                db_session.close()
    
    @staticmethod
    def get_version_stats_by_company(
        prompt_name: str,
        prompt_version: str,
        session: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Get accuracy statistics by company for a specific prompt version.
        
        Educational: This function shows how a prompt version performs across
        different companies, which can reveal if certain prompts work better
        for specific types of companies.
        
        Args:
            prompt_name: Name of the prompt
            prompt_version: Specific version to analyze
            session: Optional database session
        
        Returns:
            List of dicts, each containing company statistics:
                - company_name: Name of the company
                - test_runs_count: Number of test runs for this company
                - average_overall_accuracy: Average overall accuracy
                - average_required_fields_accuracy: Average required fields accuracy
                - average_weighted_accuracy: Average weighted accuracy
                - latest_test_run: Date of most recent test
        """
        db_session, should_close = _resolve_session(session)
        
        try:
            query = db_session.query(
                TestRun.company_name,
                func.count(TestRun.id).label('test_runs_count'),
                func.avg(LLMOutputValidationResult.overall_accuracy).label('avg_overall'),
                func.avg(LLMOutputValidationResult.required_fields_accuracy).label('avg_required'),
                func.avg(LLMOutputValidationResult.weighted_accuracy).label('avg_weighted'),
                func.max(TestRun.created_at).label('latest_test_run'),
            ).join(
                LLMOutputValidationResult,
                TestRun.id == LLMOutputValidationResult.test_run_id
            ).filter(
                TestRun.prompt_name == prompt_name,
                TestRun.prompt_version == prompt_version
            ).group_by(
                TestRun.company_name
            ).order_by(
                func.avg(LLMOutputValidationResult.overall_accuracy).desc()
            )
            
            results = query.all()
            
            return [
                {
                    'company_name': result.company_name,
                    'test_runs_count': result.test_runs_count,
                    'average_overall_accuracy': float(result.avg_overall) if result.avg_overall else None,
                    'average_required_fields_accuracy': float(result.avg_required) if result.avg_required else None,
                    'average_weighted_accuracy': float(result.avg_weighted) if result.avg_weighted else None,
                    'latest_test_run': result.latest_test_run,
                }
                for result in results
            ]
            
        finally:
            if should_close:
                db_session.close()
    
    @staticmethod
    def get_cost_analysis(
        prompt_name: Optional[str] = None,
        company_name: Optional[str] = None,
        prompt_version: Optional[str] = None,
        test_suite_name: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive cost analysis for test runs.
        
        Educational: This function aggregates costs across all test runs, breaking them
        down by agent execution costs (running models) and grading costs (Gemini Flash
        grading). This enables cost tracking and optimization of the testing process.
        
        Args:
            prompt_name: Optional filter by prompt name
            company_name: Optional filter by company name
            prompt_version: Optional filter by prompt version
            test_suite_name: Optional filter by test suite name
            session: Optional database session
        
        Returns:
            Dict containing:
                - total: Overall totals (total_cost, agent_cost, grading_cost, total_tokens, etc.)
                - by_prompt_version: Breakdown by prompt version (if prompt_name provided)
                - by_company: Breakdown by company
                - by_model: Breakdown by model
        """
        db_session, should_close = _resolve_session(session)
        
        try:
            # Build base query for outputs (agent costs)
            outputs_query = db_session.query(
                TestRun.prompt_name,
                TestRun.prompt_version,
                TestRun.company_name,
                LLMOutputValidation.model_name,
                LLMOutputValidation.model_provider,
                func.sum(LLMOutputValidation.input_tokens).label('total_input_tokens'),
                func.sum(LLMOutputValidation.output_tokens).label('total_output_tokens'),
                func.sum(LLMOutputValidation.total_tokens).label('total_tokens'),
                func.sum(LLMOutputValidation.estimated_cost_usd).label('total_cost'),
                func.count(LLMOutputValidation.id).label('outputs_count'),
            ).join(
                LLMOutputValidation,
                TestRun.id == LLMOutputValidation.test_run_id
            )
            
            # Build base query for grading results (grading costs)
            grading_query = db_session.query(
                TestRun.prompt_name,
                TestRun.prompt_version,
                TestRun.company_name,
                LLMOutputValidationResult.model_name,
                func.sum(LLMOutputValidationResult.grading_input_tokens).label('total_input_tokens'),
                func.sum(LLMOutputValidationResult.grading_output_tokens).label('total_output_tokens'),
                func.sum(LLMOutputValidationResult.grading_total_tokens).label('total_tokens'),
                func.sum(LLMOutputValidationResult.grading_cost_usd).label('total_cost'),
                func.count(LLMOutputValidationResult.id).label('grading_count'),
            ).join(
                LLMOutputValidationResult,
                TestRun.id == LLMOutputValidationResult.test_run_id
            ).join(
                LLMOutputValidation,
                LLMOutputValidationResult.output_id == LLMOutputValidation.id
            )
            
            # Apply filters to both queries
            filters = []
            if prompt_name:
                filters.append(TestRun.prompt_name == prompt_name)
            if company_name:
                filters.append(TestRun.company_name == company_name)
            if prompt_version:
                filters.append(TestRun.prompt_version == prompt_version)
            if test_suite_name:
                filters.append(TestRun.test_suite_name == test_suite_name)
            
            if filters:
                for f in filters:
                    outputs_query = outputs_query.filter(f)
                    grading_query = grading_query.filter(f)
            
            # Get agent costs
            agent_results = outputs_query.group_by(
                TestRun.prompt_name,
                TestRun.prompt_version,
                TestRun.company_name,
                LLMOutputValidation.model_name,
                LLMOutputValidation.model_provider,
            ).all()
            
            # Get grading costs
            grading_results = grading_query.group_by(
                TestRun.prompt_name,
                TestRun.prompt_version,
                TestRun.company_name,
                LLMOutputValidationResult.model_name,
            ).all()
            
            # Calculate totals
            total_agent_cost = sum(r.total_cost or 0 for r in agent_results)
            total_grading_cost = sum(r.total_cost or 0 for r in grading_results)
            total_cost = total_agent_cost + total_grading_cost
            
            total_agent_tokens = sum(r.total_tokens or 0 for r in agent_results)
            total_grading_tokens = sum(r.total_tokens or 0 for r in grading_results)
            total_tokens = total_agent_tokens + total_grading_tokens
            
            # Aggregate by prompt version
            by_prompt_version = {}
            for result in agent_results:
                key = f"{result.prompt_name}@{result.prompt_version}"
                if key not in by_prompt_version:
                    by_prompt_version[key] = {
                        'agent_cost': 0,
                        'agent_tokens': 0,
                        'grading_cost': 0,
                        'grading_tokens': 0,
                        'outputs_count': 0,
                        'grading_count': 0,
                    }
                by_prompt_version[key]['agent_cost'] += result.total_cost or 0
                by_prompt_version[key]['agent_tokens'] += result.total_tokens or 0
                by_prompt_version[key]['outputs_count'] += result.outputs_count or 0
            
            for result in grading_results:
                key = f"{result.prompt_name}@{result.prompt_version}"
                if key not in by_prompt_version:
                    by_prompt_version[key] = {
                        'agent_cost': 0,
                        'agent_tokens': 0,
                        'grading_cost': 0,
                        'grading_tokens': 0,
                        'outputs_count': 0,
                        'grading_count': 0,
                    }
                by_prompt_version[key]['grading_cost'] += result.total_cost or 0
                by_prompt_version[key]['grading_tokens'] += result.total_tokens or 0
                by_prompt_version[key]['grading_count'] += result.grading_count or 0
            
            # Aggregate by company
            by_company = {}
            for result in agent_results:
                company = result.company_name
                if company not in by_company:
                    by_company[company] = {
                        'agent_cost': 0,
                        'agent_tokens': 0,
                        'grading_cost': 0,
                        'grading_tokens': 0,
                        'outputs_count': 0,
                        'grading_count': 0,
                    }
                by_company[company]['agent_cost'] += result.total_cost or 0
                by_company[company]['agent_tokens'] += result.total_tokens or 0
                by_company[company]['outputs_count'] += result.outputs_count or 0
            
            for result in grading_results:
                company = result.company_name
                if company not in by_company:
                    by_company[company] = {
                        'agent_cost': 0,
                        'agent_tokens': 0,
                        'grading_cost': 0,
                        'grading_tokens': 0,
                        'outputs_count': 0,
                        'grading_count': 0,
                    }
                by_company[company]['grading_cost'] += result.total_cost or 0
                by_company[company]['grading_tokens'] += result.total_tokens or 0
                by_company[company]['grading_count'] += result.grading_count or 0
            
            # Aggregate by model
            by_model = {}
            for result in agent_results:
                model_key = f"{result.model_provider}:{result.model_name}"
                if model_key not in by_model:
                    by_model[model_key] = {
                        'agent_cost': 0,
                        'agent_tokens': 0,
                        'outputs_count': 0,
                        'provider': result.model_provider,
                        'model_name': result.model_name,
                    }
                by_model[model_key]['agent_cost'] += result.total_cost or 0
                by_model[model_key]['agent_tokens'] += result.total_tokens or 0
                by_model[model_key]['outputs_count'] += result.outputs_count or 0
            
            return {
                'total': {
                    'total_cost': total_cost,
                    'agent_cost': total_agent_cost,
                    'grading_cost': total_grading_cost,
                    'total_tokens': total_tokens,
                    'agent_tokens': total_agent_tokens,
                    'grading_tokens': total_grading_tokens,
                    'outputs_count': sum(r.outputs_count or 0 for r in agent_results),
                    'grading_count': sum(r.grading_count or 0 for r in grading_results),
                },
                'by_prompt_version': by_prompt_version,
                'by_company': by_company,
                'by_model': by_model,
            }
            
        finally:
            if should_close:
                db_session.close()


def _resolve_session(session: Optional[Session]) -> Tuple[Session, bool]:
    """
    Resolve database session - return existing or create new one.
    
    Educational: This helper function ensures we properly manage database sessions.
    If a session is provided, we use it (and don't close it). If not, we create
    a new one and mark it for closing.
    """
    if session:
        return session, False
    else:
        return get_session(), True

