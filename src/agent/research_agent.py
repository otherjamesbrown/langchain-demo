"""
Main research agent for gathering company information.

This module implements a ReAct-style agent that orchestrates web searches
and structured information extraction using LangChain.
"""

import os
import time
from typing import Optional
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from src.models.model_factory import get_llm
from src.tools.web_search import web_search_tool, TOOLS
from src.tools.models import CompanyInfo, AgentResult
from src.database.operations import save_company_info, save_agent_execution


class ResearchAgent:
    """
    Research agent that gathers structured company information using web search.
    
    Uses the ReAct pattern: Reasoning → Acting → Observing, iteratively
    gathering information until complete company data is assembled.
    """
    
    # System prompt for the agent
    SYSTEM_PROMPT = """You are a company research agent. Your task is to gather comprehensive 
information about companies from web searches.

For each company, you need to extract the following information:
1. Industry - What industry/sector (e.g., "Software/Video Technology")
2. Company Size - Employee count range (e.g., "201-500 employees")
3. Revenue - Annual revenue if available (e.g., "$10M - $50M")
4. Founded - Year the company was founded (e.g., 2013)
5. Headquarters - Main office location (e.g., "Vienna, Austria")
6. Products - List of main products or services offered
7. Funding - Funding stage or ownership (e.g., "Series C" or "Privately held")
8. Competitors - List of 3-5 main competitors in the market

Workflow:
1. Use the web_search_tool to search for general company information
2. Search for specific facts like company size, revenue, competitors
3. Gather information from multiple sources when possible
4. Synthesize the information into a comprehensive answer
5. If you don't find specific information, acknowledge what's missing

Always be thorough and provide accurate information. When you're done gathering
all available information, provide a final comprehensive answer.
"""
    
    def __init__(
        self,
        llm=None,
        model_type: Optional[str] = None,
        temperature: float = 0.7,
        max_iterations: int = 10,
        verbose: bool = True,
        use_database: bool = True
    ):
        """
        Initialize the research agent.
        
        Args:
            llm: Pre-initialized LLM instance. If None, creates one based on model_type
            model_type: Type of LLM to use ('local', 'openai', 'anthropic')
            temperature: Sampling temperature for LLM
            max_iterations: Maximum agent iterations before stopping
            verbose: Whether to print agent reasoning steps
            use_database: Whether to save results to database
        """
        self.use_database = use_database
        self.max_iterations = max_iterations
        self.verbose = verbose
        
        # Initialize LLM
        if llm is None:
            self.llm = get_llm(model_type=model_type, temperature=temperature)
            self.model_type = model_type or os.getenv("MODEL_TYPE", "local")
        else:
            self.llm = llm
            self.model_type = getattr(llm, "model_type", "unknown")
        
        # Create agent with ReAct pattern
        self.agent = self._create_agent()
        self.agent_executor = self._create_executor()
    
    def _create_agent(self):
        """Create the ReAct agent with prompt and tools."""
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("user", "{input}"),
            ("assistant", "{agent_scratchpad}")
        ])
        
        # Create ReAct agent
        agent = create_react_agent(
            llm=self.llm,
            tools=TOOLS,
            prompt=prompt
        )
        
        return agent
    
    def _create_executor(self):
        """Create agent executor with configuration."""
        executor = AgentExecutor(
            agent=self.agent,
            tools=TOOLS,
            max_iterations=self.max_iterations,
            verbose=self.verbose,
            return_intermediate_steps=True,
            handle_parsing_errors=True
        )
        
        return executor
    
    def research_company(self, company_name: str) -> AgentResult:
        """
        Research a single company and extract structured information.
        
        Args:
            company_name: Name of the company to research
            
        Returns:
            AgentResult with company information and execution details
            
        Raises:
            Exception: If agent execution fails
        """
        start_time = time.time()
        
        # Create research task prompt
        task = f"Research the company: {company_name}. Find comprehensive information including industry, company size, revenue, founding year, headquarters, products/services, funding stage, and competitors."
        
        try:
            # Execute agent
            result = self.agent_executor.invoke({"input": task})
            
            # Extract information
            final_answer = result.get("output", "")
            intermediate_steps = result.get("intermediate_steps", [])
            
            execution_time = time.time() - start_time
            
            # Parse structured output if possible
            company_info = self._parse_output(company_name, final_answer)
            
            # Save to database if enabled
            if self.use_database:
                try:
                    save_company_info(company_info)
                    save_agent_execution(
                        company_name=company_name,
                        agent_type="react_agent",
                        model_type=self.model_type,
                        success=True,
                        execution_time_seconds=execution_time,
                        num_tool_calls=len(intermediate_steps),
                        final_answer=company_info.model_dump(),
                        intermediate_steps=[step for step in intermediate_steps]
                    )
                except Exception as e:
                    print(f"Warning: Failed to save to database: {e}")
            
            return AgentResult(
                company_name=company_name,
                final_answer=company_info,
                intermediate_steps=intermediate_steps,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Save failed execution if enabled
            if self.use_database:
                try:
                    save_agent_execution(
                        company_name=company_name,
                        agent_type="react_agent",
                        model_type=self.model_type,
                        success=False,
                        execution_time_seconds=execution_time,
                        error_message=str(e)
                    )
                except:
                    pass
            
            raise Exception(f"Agent execution failed: {str(e)}")
    
    def _parse_output(self, company_name: str, output: str) -> CompanyInfo:
        """
        Parse agent output into structured CompanyInfo.
        
        Args:
            company_name: Name of the company
            output: Raw agent output string
            
        Returns:
            CompanyInfo Pydantic model
        """
        # Try to use Pydantic output parser
        try:
            parser = PydanticOutputParser(pydantic_object=CompanyInfo)
            # For better results, we could use an LLM to reformat the output
            # For now, create a basic parser
            return self._extract_info_from_text(company_name, output)
        except:
            return self._extract_info_from_text(company_name, output)
    
    def _extract_info_from_text(self, company_name: str, text: str) -> CompanyInfo:
        """
        Extract structured information from unstructured text.
        
        This is a basic implementation. For production, you might want to
        use an LLM call with a structured output parser to extract the data.
        
        Args:
            company_name: Name of the company
            text: Unstructured text with company information
            
        Returns:
            CompanyInfo with extracted data
        """
        # Basic extraction (this could be improved with an LLM call)
        # For now, create a minimal CompanyInfo
        return CompanyInfo(
            company_name=company_name,
            industry=self._find_field(text, ["industry", "sector", "vertical"]),
            company_size=self._find_field(text, ["employees", "company size", "headcount"]),
            revenue=None,
            founded=None,
            headquarters=self._find_field(text, ["headquarters", "based in", "located in"]),
            products=[],
            funding_stage=None,
            competitors=[],
            description=text[:500] if len(text) > 500 else text
        )
    
    def _find_field(self, text: str, keywords: list[str]) -> str:
        """Find a field in text using keywords."""
        text_lower = text.lower()
        for keyword in keywords:
            idx = text_lower.find(keyword)
            if idx != -1:
                # Extract surrounding context
                start = max(0, idx - 50)
                end = min(len(text), idx + 200)
                return text[start:end].strip()
        return ""
    
    def batch_research(self, company_names: list[str]) -> list[AgentResult]:
        """
        Research multiple companies in batch.
        
        Args:
            company_names: List of company names to research
            
        Returns:
            List of AgentResult objects
        """
        results = []
        for company_name in company_names:
            try:
                result = self.research_company(company_name)
                results.append(result)
            except Exception as e:
                print(f"Failed to research {company_name}: {e}")
                continue
        return results


# Main entry point for command-line usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Research company information")
    parser.add_argument("company", help="Company name to research")
    parser.add_argument("--model-type", choices=["local", "openai", "anthropic"], default="local")
    parser.add_argument("--verbose", action="store_true", default=True)
    parser.add_argument("--no-db", action="store_true", help="Don't save to database")
    
    args = parser.parse_args()
    
    # Create agent
    agent = ResearchAgent(
        model_type=args.model_type,
        verbose=args.verbose,
        use_database=not args.no_db
    )
    
    # Research company
    print(f"\nResearching {args.company}...\n")
    result = agent.research_company(args.company)
    
    # Display results
    print("\n" + "="*60)
    print("Research Results")
    print("="*60)
    print(f"\nCompany: {result.company_name}")
    print(f"Execution time: {result.execution_time:.2f}s")
    print(f"\n{result.final_answer.model_dump_json(indent=2)}")

