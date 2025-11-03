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
from sqlalchemy import not_, and_

from src.agent.research_agent import ResearchAgent, ResearchAgentResult
from src.database.schema import (
    LLMOutputValidation,
    TestRun,
    ModelConfiguration,
    PromptVersion,
    LLMOutputValidationResult,
    GradingPromptVersion,
    get_session,
)
from src.prompts.prompt_manager import PromptManager
from src.prompts.grading_prompt_manager import GradingPromptManager


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
        # Use actual Gemini Pro model identifier from database
        # If not found in DB, fall back to default
        self.gemini_pro_model_name = self._get_gemini_pro_model_name()
        self.gemini_flash_model_name = "gemini-flash-latest"
        
        # Prompt version management
        self.prompt_version_id = prompt_version_id
        self.prompt_name = prompt_name
        self.prompt_version = prompt_version
        self.test_run_description = test_run_description
        
        # Validate and resolve prompt version
        self._resolved_prompt_version = self._resolve_prompt_version()
    
    def _get_gemini_pro_model_name(self) -> str:
        """
        Get the Gemini Pro model identifier from database.
        
        Educational: This looks up the actual Gemini Pro model from the database
        instead of hardcoding a placeholder. This ensures we use the correct,
        high-quality model as ground truth.
        
        Returns:
            API identifier for Gemini Pro model (e.g., "gemini-2.5-pro")
            Falls back to "gemini-2.5-pro" if not found in database
        """
        try:
            from src.database.schema import get_session, ModelConfiguration
            session = get_session()
            try:
                # Look for Gemini Pro model in database
                gemini_pro = (
                    session.query(ModelConfiguration)
                    .filter(
                        ModelConfiguration.provider == "gemini",
                        ModelConfiguration.is_active == True,
                        ModelConfiguration.name.ilike("%pro%")
                    )
                    .first()
                )
                
                if gemini_pro and gemini_pro.api_identifier:
                    return gemini_pro.api_identifier
            finally:
                session.close()
        except Exception:
            pass
        
        # Fallback to default Gemini Pro identifier
        return "gemini-2.5-pro"
    
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
    
    def _get_other_models(self, session: Session) -> List[ModelConfiguration]:
        """
        Get all active models except Gemini Pro.
        
        Educational: This retrieves all active model configurations from the database
        that can be tested. We exclude Gemini Pro since it's used as ground truth.
        """
        return (
            session.query(ModelConfiguration)
            .filter(ModelConfiguration.is_active == True)
            .all()
        )
    
    def _delete_other_model_outputs(
        self,
        session: Session,
        company_name: str,
        test_run_id: int,
    ) -> None:
        """
        Delete outputs from other models for this test run.
        
        Educational: This ensures clean test runs - if we re-run a test, we remove
        old outputs from other models (but keep Gemini Pro ground truth) to avoid
        duplicate results.
        """
        (
            session.query(LLMOutputValidation)
            .filter(
                LLMOutputValidation.test_name == self.test_name,
                LLMOutputValidation.company_name == company_name,
                not_(
                    and_(
                        LLMOutputValidation.model_provider == "gemini",
                        LLMOutputValidation.model_name == self.gemini_pro_model_name
                    )
                ),
                LLMOutputValidation.test_run_id == test_run_id,
            )
            .delete()
        )
        session.commit()
    
    def _run_model_and_store(
        self,
        session: Session,
        company_name: str,
        test_run_id: int,
        model_config: ModelConfiguration,
        max_iterations: int,
    ) -> Optional[LLMOutputValidation]:
        """
        Run agent for a model and store output.
        
        Educational: This demonstrates how to run the ResearchAgent with different
        models and store their outputs. Each model gets the same prompt version
        to ensure fair comparison.
        """
        try:
            # Build agent kwargs based on model type
            agent_kwargs = {
                "model_type": model_config.provider,
                "max_iterations": max_iterations,
                "verbose": False,
            }
            
            # Use same prompt version as test run
            if self.prompt_version_id:
                agent_kwargs["prompt_version_id"] = self.prompt_version_id
            elif self.prompt_name:
                agent_kwargs["prompt_name"] = self.prompt_name
                if self.prompt_version:
                    agent_kwargs["prompt_version"] = self.prompt_version
            
            # Configure model-specific parameters
            if model_config.provider == "local":
                if model_config.model_path:
                    agent_kwargs["model_path"] = model_config.model_path
                if model_config.model_key:
                    agent_kwargs["local_model"] = model_config.model_key
            else:
                # API-based models
                model_kwargs = {}
                if model_config.api_identifier:
                    model_kwargs["model_name"] = model_config.api_identifier
                if model_kwargs:
                    agent_kwargs["model_kwargs"] = model_kwargs
            
            # Run agent
            agent = ResearchAgent(**agent_kwargs)
            result: ResearchAgentResult = agent.research_company(company_name)
            
            if not result.success or not result.company_info:
                return None
            
            # Store in database
            output = self._store_output(
                session=session,
                company_name=company_name,
                result=result,
                model_name=model_config.name,
                model_provider=model_config.provider,
                model_config_id=model_config.id,
                test_run_id=test_run_id,
            )
            
            session.commit()
            return output
            
        except Exception as e:
            session.rollback()
            print(f"Error running model {model_config.name}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_fields_to_grade(self) -> List[str]:
        """
        Get list of all CompanyInfo fields to grade.
        
        Educational: This returns all fields from the CompanyInfo schema that
        should be evaluated. Required fields (company_name, industry, etc.) are
        typically weighted more heavily in accuracy calculations.
        """
        return [
            "company_name_field",  # Note: stored as company_name_field in DB
            "industry",
            "company_size",
            "headquarters",
            "founded",
            "description",
            "website",
            "products",
            "competitors",
            "revenue",
            "funding_stage",
            "growth_stage",
            "industry_vertical",
            "sub_industry_vertical",
            "financial_health",
            "business_and_technology_adoption",
            "primary_workload_philosophy",
            "buyer_journey",
            "budget_maturity",
            "cloud_spend_capacity",
            "procurement_process",
            "key_personas",
        ]
    
    def _grade_field(
        self,
        flash_model: Any,
        field_name: str,
        correct_value: Any,
        actual_value: Any,
        grading_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Grade a single field using Gemini Flash.
        
        Educational: This demonstrates how to use an LLM (Gemini Flash) to grade
        another LLM's output. The grading prompt asks for structured output with
        score, match type, confidence, and explanation.
        
        Args:
            flash_model: Initialized Gemini Flash chat model
            field_name: Name of the field being graded
            correct_value: Value from Gemini Pro (ground truth)
            actual_value: Value from the model being graded
            grading_prompt: Optional custom grading prompt (uses active version if not provided)
            
        Returns:
            Dict with keys: score, match_type, confidence, explanation, grading_response
        """
        from langchain_core.messages import HumanMessage
        import re
        
        # Handle None values
        if correct_value is None:
            correct_value_str = "None"
        elif isinstance(correct_value, list):
            correct_value_str = ", ".join(str(v) for v in correct_value) if correct_value else "None"
        else:
            correct_value_str = str(correct_value)
        
        if actual_value is None:
            actual_value_str = "None"
        elif isinstance(actual_value, list):
            actual_value_str = ", ".join(str(v) for v in actual_value) if actual_value else "None"
        else:
            actual_value_str = str(actual_value)
        
        # Load grading prompt from database if not provided
        if not grading_prompt:
            grading_prompt_version = GradingPromptManager.get_active_version()
            if not grading_prompt_version:
                raise ValueError("No active grading prompt version found. Initialize using initialize_prompts.py")
            grading_prompt = grading_prompt_version.prompt_template
        
        # Format the prompt with field values
        formatted_prompt = grading_prompt.format(
            field_name=field_name,
            correct_value=correct_value_str,
            actual_value=actual_value_str,
        )
        
        try:
            # Call Gemini Flash
            response = flash_model.invoke([HumanMessage(content=formatted_prompt)])
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse structured response
            score_match = re.search(r'SCORE:\s*(\d+(?:\.\d+)?)', response_text, re.IGNORECASE)
            match_type_match = re.search(r'MATCH_TYPE:\s*(exact|semantic|partial|none)', response_text, re.IGNORECASE)
            confidence_match = re.search(r'CONFIDENCE:\s*([01]\.?\d*)', response_text, re.IGNORECASE)
            explanation_match = re.search(r'EXPLANATION:\s*(.+?)(?:\n|$)', response_text, re.IGNORECASE | re.DOTALL)
            
            score = float(score_match.group(1)) if score_match else 0.0
            match_type = match_type_match.group(1).lower() if match_type_match else "none"
            confidence = float(confidence_match.group(1)) if confidence_match else 0.5
            explanation = explanation_match.group(1).strip() if explanation_match else "Could not parse explanation"
            
            # Clamp values to valid ranges
            score = max(0.0, min(100.0, score))
            confidence = max(0.0, min(1.0, confidence))
            
            return {
                "score": score,
                "match_type": match_type,
                "confidence": confidence,
                "explanation": explanation,
                "grading_response": response_text,
            }
            
        except Exception as e:
            # Handle parse errors or API errors
            return {
                "score": 0.0,
                "match_type": "none",
                "confidence": 0.0,
                "explanation": f"Error grading field: {str(e)}",
                "grading_response": "",
            }
    
    def _grade_output_with_flash(
        self,
        session: Session,
        gemini_pro_output: LLMOutputValidation,
        other_output: LLMOutputValidation,
        company_name: str,
        test_run_id: int,
    ) -> Optional[LLMOutputValidationResult]:
        """
        Grade another model's output using Gemini Flash field-by-field.
        
        Educational: This demonstrates the complete grading workflow:
        1. Load grading prompt from database (versioned)
        2. Grade each field individually
        3. Calculate aggregate scores (overall, required fields, weighted)
        4. Store results in database with full metadata
        
        Args:
            session: Database session
            gemini_pro_output: Ground truth output from Gemini Pro
            other_output: Output from model being graded
            company_name: Company name for this test
            test_run_id: Test run ID
            
        Returns:
            LLMOutputValidationResult object if successful, None otherwise
        """
        from src.models.model_factory import get_chat_model
        
        try:
            # Get fields to grade
            fields_to_grade = self._get_fields_to_grade()
            
            # Initialize Gemini Flash model
            flash_model = get_chat_model(
                model_type="gemini",
                model_kwargs={"model_name": self.gemini_flash_model_name},
            )
            
            # Load grading prompt version
            grading_prompt_version = GradingPromptManager.get_active_version(session=session)
            if not grading_prompt_version:
                raise ValueError("No active grading prompt version found")
            
            grading_prompt_template = grading_prompt_version.prompt_template
            
            # Grade each field
            field_scores = {}
            grading_responses = []
            total_grading_input_tokens = 0
            total_grading_output_tokens = 0
            
            for field_name in fields_to_grade:
                correct_value = getattr(gemini_pro_output, field_name, None)
                actual_value = getattr(other_output, field_name, None)
                
                field_result = self._grade_field(
                    flash_model=flash_model,
                    field_name=field_name,
                    correct_value=correct_value,
                    actual_value=actual_value,
                    grading_prompt=grading_prompt_template,
                )
                
                # Store field result
                field_scores[field_name] = {
                    "score": field_result["score"],
                    "match_type": field_result["match_type"],
                    "explanation": field_result["explanation"],
                    "confidence": field_result["confidence"],
                }
                
                grading_responses.append({
                    "field": field_name,
                    "response": field_result["grading_response"],
                })
                
                # Try to extract token usage from response metadata
                # This is provider-dependent and may not always be available
                if hasattr(flash_model, 'get_num_tokens_from_messages'):
                    try:
                        # Estimate tokens (rough approximation)
                        response_text = field_result["grading_response"]
                        total_grading_output_tokens += len(response_text.split()) * 1.3  # Rough estimate
                        total_grading_input_tokens += len(grading_prompt_template.split()) * 1.3
                    except:
                        pass
            
            # Calculate aggregate scores
            all_scores = [r["score"] for r in field_scores.values()]
            overall_accuracy = sum(all_scores) / len(all_scores) if all_scores else 0.0
            
            # Required fields (core company info)
            required_fields = ["company_name_field", "industry", "company_size", "headquarters", "founded"]
            required_scores = [field_scores[f]["score"] for f in required_fields if f in field_scores]
            required_fields_accuracy = sum(required_scores) / len(required_scores) if required_scores else 0.0
            
            # Optional fields (all others)
            optional_fields = [f for f in fields_to_grade if f not in required_fields]
            optional_scores = [field_scores[f]["score"] for f in optional_fields if f in field_scores]
            optional_fields_accuracy = sum(optional_scores) / len(optional_scores) if optional_scores else 0.0
            
            # Weighted accuracy (critical fields count 2x)
            critical_fields = ["industry", "company_size", "headquarters"]
            weighted_scores = []
            for field_name, result in field_scores.items():
                weight = 2.0 if field_name in critical_fields else 1.0
                weighted_scores.extend([result["score"]] * int(weight))
            weighted_accuracy = sum(weighted_scores) / len(weighted_scores) if weighted_scores else 0.0
            
            # Calculate grading cost
            total_grading_tokens = total_grading_input_tokens + total_grading_output_tokens
            grading_cost = self._calculate_cost(
                model_provider="gemini",
                model_name=self.gemini_flash_model_name,
                input_tokens=int(total_grading_input_tokens),
                output_tokens=int(total_grading_output_tokens),
            ) if total_grading_input_tokens and total_grading_output_tokens else None
            
            # Store result
            validation_result = LLMOutputValidationResult(
                output_id=other_output.id,
                test_run_id=test_run_id,
                test_name=self.test_name,
                company_name=company_name,
                model_name=other_output.model_name,
                model_provider=other_output.model_provider,
                field_accuracy_scores=field_scores,
                overall_accuracy=overall_accuracy,
                required_fields_accuracy=required_fields_accuracy,
                optional_fields_accuracy=optional_fields_accuracy,
                weighted_accuracy=weighted_accuracy,
                graded_by_model=self.gemini_flash_model_name,
                grading_prompt_version_id=grading_prompt_version.id,
                grading_prompt=grading_prompt_template,
                grading_response=str(grading_responses),
                grading_input_tokens=int(total_grading_input_tokens) if total_grading_input_tokens else None,
                grading_output_tokens=int(total_grading_output_tokens) if total_grading_output_tokens else None,
                grading_total_tokens=int(total_grading_tokens) if total_grading_tokens else None,
                grading_cost_usd=grading_cost,
            )
            
            session.add(validation_result)
            session.commit()
            
            return validation_result
            
        except Exception as e:
            session.rollback()
            print(f"Error grading output: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run_test(
        self,
        company_name: str,
        other_models: Optional[List[ModelConfiguration]] = None,
        force_refresh: bool = False,
        max_iterations: int = 10,
        test_suite_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run the complete LLM output validation test workflow.
        
        Educational: This demonstrates the complete testing workflow:
        1. Create test run record with prompt version
        2. Ensure Gemini Pro ground truth exists (with 24-hour caching)
        3. Run other models with the same prompt version
        4. Grade all outputs using Gemini Flash field-by-field
        5. Calculate aggregate accuracy scores
        6. Store all results in database
        
        Workflow:
        1. Create test run record with prompt version
        2. Check if Gemini Pro output exists and is fresh (<24hrs) for this test run
        3. If not, run agent with Gemini Pro to get ground truth
        4. Store ground truth in database
        5. Run other models (excludes Gemini Pro)
        6. Store all model outputs
        7. Grade each output using Gemini Flash
        8. Calculate aggregate statistics
        
        Args:
            company_name: Company to research
            other_models: List of model configs to test (excludes Gemini Pro). 
                         If None, uses all active models from database.
            force_refresh: Force refresh even if Gemini Pro data is fresh (<24hrs)
            max_iterations: Max agent iterations
            test_suite_name: Optional name to group multiple company tests together
            
        Returns:
            Dict with test results summary including:
            - test_run_id: ID of the test run record
            - gemini_pro_output_id: ID of ground truth output
            - other_outputs_count: Number of other models tested
            - grading_results_count: Number of outputs graded
            - aggregate_stats: Average accuracy scores and costs
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
            
            # Step 3: Run other models (Stage 9)
            other_outputs = []
            other_models_to_test = other_models or self._get_other_models(session=session)
            
            # Clean up old outputs for this test run (excluding Gemini Pro)
            self._delete_other_model_outputs(
                session=session,
                company_name=company_name,
                test_run_id=test_run.id,
            )
            
            # Run each model
            for model_config in other_models_to_test:
                # Skip Gemini Pro (it's already ground truth)
                if (model_config.provider == "gemini" and 
                    model_config.api_identifier == self.gemini_pro_model_name):
                    continue
                
                output = self._run_model_and_store(
                    session=session,
                    company_name=company_name,
                    test_run_id=test_run.id,
                    model_config=model_config,
                    max_iterations=max_iterations,
                )
                
                if output:
                    other_outputs.append(output)
            
            session.commit()
            
            # Step 4: Grade all outputs using Gemini Flash (Stage 10-11)
            grading_results = []
            for other_output in other_outputs:
                grading_result = self._grade_output_with_flash(
                    session=session,
                    gemini_pro_output=gemini_pro_output,
                    other_output=other_output,
                    company_name=company_name,
                    test_run_id=test_run.id,
                )
                
                if grading_result:
                    grading_results.append(grading_result)
            
            session.commit()
            
            # Calculate aggregate statistics from grading results
            aggregate_stats = {}
            if grading_results:
                # Calculate averages, handling None values
                overall_accuracies = [r.overall_accuracy for r in grading_results]
                required_accuracies = [r.required_fields_accuracy for r in grading_results if r.required_fields_accuracy is not None]
                weighted_accuracies = [r.weighted_accuracy for r in grading_results if r.weighted_accuracy is not None]
                grading_costs = [r.grading_cost_usd for r in grading_results if r.grading_cost_usd is not None]
                
                aggregate_stats = {
                    "average_overall_accuracy": sum(overall_accuracies) / len(overall_accuracies) if overall_accuracies else 0.0,
                    "average_required_fields_accuracy": sum(required_accuracies) / len(required_accuracies) if required_accuracies else None,
                    "average_weighted_accuracy": sum(weighted_accuracies) / len(weighted_accuracies) if weighted_accuracies else None,
                    "total_grading_cost": sum(grading_costs) if grading_costs else 0.0,
                }
            
            return {
                "success": True,
                "test_run_id": test_run.id,
                "prompt_version": self._resolved_prompt_version.version,
                "company_name": company_name,
                "gemini_pro_output_id": gemini_pro_output.id,
                "ground_truth_status": gemini_pro_output.ground_truth_status,
                "other_outputs_count": len(other_outputs),
                "other_output_ids": [o.id for o in other_outputs],
                "grading_results_count": len(grading_results),
                "grading_result_ids": [r.id for r in grading_results],
                "aggregate_stats": aggregate_stats,
            }
            
        finally:
            session.close()

