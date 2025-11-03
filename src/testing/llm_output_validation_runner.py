"""
LLM Output Validation Runner - Testing Framework Core.

Educational: This demonstrates a different testing approach where:
- One model's output (Gemini Pro) is treated as ground truth
- Another model (Gemini Flash) is used to grade other models' outputs
- Results are stored in database for comparison over time
- Prompt versions are tracked to enable prompt engineering experiments
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from src.agent.research_agent import ResearchAgent, ResearchAgentResult
from src.database.schema import (
    LLMOutputValidation,
    TestRun,
    ModelConfiguration,
    PromptVersion,
    get_session,
)
from src.prompts.prompt_manager import PromptManager


class LLMOutputValidationRunner:
    """
    Test runner that uses Gemini Pro as ground truth and Gemini Flash for grading.
    
    Educational: This demonstrates a different testing approach where:
    - One model's output is treated as ground truth
    - Another model is used to grade other models' outputs
    - Results are stored in database for comparison over time
    - Prompt versions are tracked to enable prompt engineering experiments
    """
    
    def __init__(
        self, 
        test_name: str = "llm-output-validation",
        prompt_version_id: Optional[int] = None,
        prompt_name: Optional[str] = None,
        prompt_version: Optional[str] = None,
        test_run_description: Optional[str] = None,
    ):
        """
        Initialize the test runner.
        
        Args:
            test_name: Name identifier for this test type
            prompt_version_id: Use specific prompt version by ID
            prompt_name: Use active version of named prompt (or specific version)
            prompt_version: Specific version string (requires prompt_name)
            test_run_description: Optional description for test run
        """
        self.test_name = test_name
        # Note: Update to actual Gemini 2.5 Pro identifier when available
        # Using Flash for now as placeholder
        self.gemini_pro_model_name = "gemini-2.0-flash-exp"
        self.gemini_flash_model_name = "gemini-flash-latest"
        
        # Prompt version management
        self.prompt_version_id = prompt_version_id
        self.prompt_name = prompt_name
        self.prompt_version = prompt_version
        self.test_run_description = test_run_description
        
        # Validate and resolve prompt version
        self._resolved_prompt_version = self._resolve_prompt_version()
    
    def _resolve_prompt_version(self) -> Optional[PromptVersion]:
        """Resolve the prompt version to use."""
        if self.prompt_version_id:
            pv = PromptManager.get_version_by_id(self.prompt_version_id)
            if not pv:
                raise ValueError(f"Prompt version ID {self.prompt_version_id} not found")
            return pv
        elif self.prompt_name:
            if self.prompt_version:
                pv = PromptManager.get_version(self.prompt_name, self.prompt_version)
            else:
                pv = PromptManager.get_active_version(self.prompt_name)
            
            if not pv:
                raise ValueError(f"Prompt '{self.prompt_name}' (version: {self.prompt_version or 'active'}) not found")
            
            self.prompt_version_id = pv.id
            return pv
        else:
            # Use active version of default prompt
            pv = PromptManager.get_active_version("research-agent-prompt")
            if pv:
                self.prompt_version_id = pv.id
                return pv
            else:
                # Fallback: allow running without prompt version (will use file-based)
                return None
    
    def _ensure_gemini_pro_output(
        self,
        session: Session,
        company_name: str,
        test_run_id: int,
        force_refresh: bool,
        max_iterations: int,
    ) -> Optional[LLMOutputValidation]:
        """
        Ensure Gemini Pro output exists and is fresh.
        
        Checks for existing output from this test run first, then checks for
        cached output from same prompt version (<24hrs old) that can be reused.
        If no valid cache exists, runs agent with Gemini Pro to generate ground truth.
        """
        # Check for existing output from THIS test run
        existing = (
            session.query(LLMOutputValidation)
            .filter(
                LLMOutputValidation.test_name == self.test_name,
                LLMOutputValidation.company_name == company_name,
                LLMOutputValidation.model_provider == "gemini",
                LLMOutputValidation.model_name == self.gemini_pro_model_name,
                LLMOutputValidation.test_run_id == test_run_id,
            )
            .first()
        )
        
        if existing:
            return existing
        
        # Check if we can reuse from a different test run (same prompt version, <24hrs old)
        if not force_refresh:
            hours_threshold = 24
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_threshold)
            
            # Get prompt version for this test run
            test_run = session.query(TestRun).filter(TestRun.id == test_run_id).first()
            if test_run and self.prompt_version_id:
                recent_output = (
                    session.query(LLMOutputValidation)
                    .join(TestRun)
                    .filter(
                        LLMOutputValidation.test_name == self.test_name,
                        LLMOutputValidation.company_name == company_name,
                        LLMOutputValidation.model_provider == "gemini",
                        LLMOutputValidation.model_name == self.gemini_pro_model_name,
                        TestRun.prompt_version_id == test_run.prompt_version_id,
                        LLMOutputValidation.created_at >= cutoff_time,
                    )
                    .order_by(LLMOutputValidation.created_at.desc())
                    .first()
                )
                
                if recent_output:
                    # Copy to this test run
                    copied_output = self._copy_output_to_test_run(
                        session=session,
                        source_output=recent_output,
                        target_test_run_id=test_run_id,
                    )
                    if copied_output:
                        return copied_output
        
        # Need to refresh - run agent with Gemini Pro
        return self._run_gemini_pro_and_store(
            session=session,
            company_name=company_name,
            test_run_id=test_run_id,
            max_iterations=max_iterations,
        )
    
    def _run_gemini_pro_and_store(
        self,
        session: Session,
        company_name: str,
        test_run_id: int,
        max_iterations: int,
    ) -> Optional[LLMOutputValidation]:
        """Run agent with Gemini Pro and store result."""
        try:
            # Initialize agent with prompt version
            agent_kwargs = {
                "model_type": "gemini",
                "model_kwargs": {"model_name": self.gemini_pro_model_name},
                "max_iterations": max_iterations,
                "verbose": False,
            }
            
            if self.prompt_version_id:
                agent_kwargs["prompt_version_id"] = self.prompt_version_id
            elif self.prompt_name:
                agent_kwargs["prompt_name"] = self.prompt_name
                if self.prompt_version:
                    agent_kwargs["prompt_version"] = self.prompt_version
            
            agent = ResearchAgent(**agent_kwargs)
            result: ResearchAgentResult = agent.research_company(company_name)
            
            if not result.success or not result.company_info:
                return None
            
            # Store in database with test_run_id
            output = self._store_output(
                session=session,
                company_name=company_name,
                result=result,
                model_name=self.gemini_pro_model_name,
                model_provider="gemini",
                model_config_id=None,
                test_run_id=test_run_id,
            )
            
            session.commit()
            return output
            
        except Exception as e:
            session.rollback()
            print(f"Error running Gemini Pro: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _store_output(
        self,
        session: Session,
        company_name: str,
        result: ResearchAgentResult,
        model_name: str,
        model_provider: str,
        model_config_id: Optional[int],
        test_run_id: int,
    ) -> LLMOutputValidation:
        """
        Store agent result in LLMOutputValidation table.
        
        Educational: This shows how to persist model outputs with full metadata
        including token usage and cost tracking for cost analysis.
        """
        company_info = result.company_info
        
        # Calculate token usage and cost
        # Note: ResearchAgentResult doesn't currently track tokens, so we estimate
        # or extract from model response metadata if available
        input_tokens = None
        output_tokens = None
        total_tokens = None
        estimated_cost = None
        
        # Try to extract token usage from model response metadata
        # This depends on the model provider's response format
        if hasattr(result, 'model_input') and result.model_input:
            # Try to extract from LangChain response metadata if available
            # This is provider-dependent
            pass
        
        # Calculate cost if we have token counts
        if input_tokens and output_tokens:
            total_tokens = input_tokens + output_tokens
            estimated_cost = self._calculate_cost(
                model_provider=model_provider,
                model_name=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        
        output = LLMOutputValidation(
            test_run_id=test_run_id,
            test_name=self.test_name,
            company_name=company_name,
            model_configuration_id=model_config_id,
            model_name=model_name,
            model_provider=model_provider,
            company_name_field=company_info.company_name,
            industry=company_info.industry,
            company_size=company_info.company_size,
            headquarters=company_info.headquarters,
            founded=company_info.founded,
            description=company_info.description,
            website=company_info.website,
            products=company_info.products or [],
            competitors=company_info.competitors or [],
            revenue=company_info.revenue,
            funding_stage=company_info.funding_stage,
            growth_stage=company_info.growth_stage,
            industry_vertical=company_info.industry_vertical,
            sub_industry_vertical=company_info.sub_industry_vertical,
            financial_health=company_info.financial_health,
            business_and_technology_adoption=company_info.business_and_technology_adoption,
            primary_workload_philosophy=company_info.primary_workload_philosophy,
            buyer_journey=company_info.buyer_journey,
            budget_maturity=company_info.budget_maturity,
            cloud_spend_capacity=company_info.cloud_spend_capacity,
            procurement_process=company_info.procurement_process,
            key_personas=company_info.key_personas or [],
            execution_time_seconds=result.execution_time_seconds,
            iterations=result.iterations,
            success=result.success,
            raw_output=result.raw_output,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
            ground_truth_status="unvalidated",  # New ground truth starts as unvalidated
        )
        
        session.add(output)
        return output
    
    def _calculate_cost(
        self,
        model_provider: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        Calculate estimated cost in USD based on model pricing.
        
        Educational: This demonstrates cost tracking for API-based models,
        enabling cost analysis and budget forecasting for test runs.
        """
        # Pricing per 1M tokens (as of 2025)
        pricing = {
            "gemini": {
                "gemini-2.0-flash-exp": {"input": 0.15, "output": 0.60},  # Flash pricing (placeholder)
                "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
                "gemini-flash-latest": {"input": 0.075, "output": 0.30},
            },
            "openai": {
                "gpt-4o": {"input": 2.50, "output": 10.00},
                "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            },
            "anthropic": {
                "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
                "claude-3-haiku": {"input": 0.25, "output": 1.25},
            },
        }
        
        provider_pricing = pricing.get(model_provider, {})
        model_pricing = provider_pricing.get(model_name, {"input": 0, "output": 0})
        
        input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (output_tokens / 1_000_000) * model_pricing["output"]
        
        return round(input_cost + output_cost, 6)  # 6 decimal places for precision
    
    def _copy_output_to_test_run(
        self,
        session: Session,
        source_output: LLMOutputValidation,
        target_test_run_id: int,
    ) -> LLMOutputValidation:
        """
        Copy an existing output to a new test run.
        
        Educational: This enables reusing cached ground truth across test runs,
        reducing API costs when testing the same company with different prompt versions.
        """
        # Create a new output record with same data but new test_run_id
        copied = LLMOutputValidation(
            test_run_id=target_test_run_id,
            test_name=source_output.test_name,
            company_name=source_output.company_name,
            model_configuration_id=source_output.model_configuration_id,
            model_name=source_output.model_name,
            model_provider=source_output.model_provider,
            company_name_field=source_output.company_name_field,
            industry=source_output.industry,
            company_size=source_output.company_size,
            headquarters=source_output.headquarters,
            founded=source_output.founded,
            description=source_output.description,
            website=source_output.website,
            products=source_output.products,
            competitors=source_output.competitors,
            revenue=source_output.revenue,
            funding_stage=source_output.funding_stage,
            growth_stage=source_output.growth_stage,
            industry_vertical=source_output.industry_vertical,
            sub_industry_vertical=source_output.sub_industry_vertical,
            financial_health=source_output.financial_health,
            business_and_technology_adoption=source_output.business_and_technology_adoption,
            primary_workload_philosophy=source_output.primary_workload_philosophy,
            buyer_journey=source_output.buyer_journey,
            budget_maturity=source_output.budget_maturity,
            cloud_spend_capacity=source_output.cloud_spend_capacity,
            procurement_process=source_output.procurement_process,
            key_personas=source_output.key_personas,
            execution_time_seconds=source_output.execution_time_seconds,
            iterations=source_output.iterations,
            success=source_output.success,
            raw_output=source_output.raw_output,
            input_tokens=source_output.input_tokens,
            output_tokens=source_output.output_tokens,
            total_tokens=source_output.total_tokens,
            estimated_cost_usd=source_output.estimated_cost_usd,
            ground_truth_status=source_output.ground_truth_status,
        )
        
        session.add(copied)
        session.commit()
        return copied
    
    def run_test(
        self,
        company_name: str,
        other_models: Optional[List[ModelConfiguration]] = None,
        force_refresh: bool = False,
        max_iterations: int = 10,
        test_suite_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run the LLM output validation test.
        
        Workflow:
        1. Create test run record with prompt version
        2. Check if Gemini Pro output exists and is fresh (<24hrs) for this test run
        3. If not, run agent with Gemini Pro to get ground truth
        4. Store ground truth in database
        
        Args:
            company_name: Company to research
            other_models: List of model configs to test (excludes Gemini Pro) - not used in Stage 8
            force_refresh: Force refresh even if Gemini Pro data is fresh
            max_iterations: Max agent iterations
            test_suite_name: Optional name to group multiple company tests together
            
        Returns:
            Dict with test results summary
        """
        session = get_session()
        try:
            # Step 1: Create test run record
            if not self._resolved_prompt_version:
                raise ValueError("No prompt version available. Initialize prompts first using initialize_prompts.py")
            
            test_run = TestRun(
                test_name=self.test_name,
                company_name=company_name,
                test_suite_name=test_suite_name,
                prompt_version_id=self.prompt_version_id,
                prompt_name=self._resolved_prompt_version.prompt_name,
                prompt_version=self._resolved_prompt_version.version,
                description=self.test_run_description,
            )
            session.add(test_run)
            session.commit()
            
            # Step 2: Check/refresh Gemini Pro output (ground truth)
            gemini_pro_output = self._ensure_gemini_pro_output(
                session=session,
                company_name=company_name,
                test_run_id=test_run.id,
                force_refresh=force_refresh,
                max_iterations=max_iterations,
            )
            
            if not gemini_pro_output:
                return {
                    "success": False,
                    "error": "Failed to get Gemini Pro ground truth output",
                    "test_run_id": test_run.id,
                }
            
            return {
                "success": True,
                "test_run_id": test_run.id,
                "prompt_version": self._resolved_prompt_version.version,
                "company_name": company_name,
                "gemini_pro_output_id": gemini_pro_output.id,
                "ground_truth_status": gemini_pro_output.ground_truth_status,
            }
            
        finally:
            session.close()

