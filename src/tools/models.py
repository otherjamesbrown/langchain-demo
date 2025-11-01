"""
Pydantic models for structured company information extraction.

These models define the schema for company data that the agent will extract
using LLM-based structured output parsing.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class CompanyInfo(BaseModel):
    """
    Structured company information extracted by the research agent.
    
    This model defines all fields that should be gathered for each company,
    providing validation and type safety for the extracted data.
    """
    
    # Basic company information
    company_name: str = Field(
        description="The official company name"
    )
    
    industry: str = Field(
        description="Primary industry or sector (e.g., 'Video Technology / SaaS')"
    )
    
    company_size: str = Field(
        description="Number of employees as a range (e.g., '201-500 employees')"
    )
    
    # Financial information
    revenue: Optional[str] = Field(
        default=None,
        description="Annual revenue range if publicly available (e.g., '$10M - $50M')"
    )
    
    funding_stage: Optional[str] = Field(
        default=None,
        description="Funding stage or ownership status (e.g., 'Series C', 'Privately held')"
    )
    
    # Company history
    founded: Optional[int] = Field(
        default=None,
        description="Year the company was founded"
    )
    
    headquarters: str = Field(
        description="Main office location (city, state/region, country)"
    )
    
    # Products and services
    products: List[str] = Field(
        default_factory=list,
        description="List of main products or services offered"
    )
    
    # Market position
    competitors: List[str] = Field(
        default_factory=list,
        description="List of 3-5 main competitors in the market"
    )
    
    # Additional context
    description: Optional[str] = Field(
        default=None,
        description="Brief company description or tagline"
    )
    
    website: Optional[str] = Field(
        default=None,
        description="Company website URL"
    )
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "company_name": "BitMovin",
                "industry": "Video Technology / SaaS",
                "company_size": "201-500 employees",
                "revenue": "$10M - $50M",
                "funding_stage": "Series C",
                "founded": 2013,
                "headquarters": "Vienna, Austria",
                "products": [
                    "Bitmovin Player",
                    "Bitmovin Encoding",
                    "Bitmovin Analytics"
                ],
                "competitors": [
                    "Brightcove",
                    "JW Player",
                    "Mux",
                    "Video.js"
                ],
                "description": "Video streaming technology company providing encoding, player, and analytics solutions",
                "website": "https://bitmovin.com"
            }
        }


class SearchResult(BaseModel):
    """
    Structured result from web search operations.
    
    Used to standardize search API responses and provide
    consistent data to the agent.
    """
    
    title: str = Field(description="Title of the search result")
    url: str = Field(description="URL of the search result")
    content: str = Field(description="Text content or summary")
    relevance_score: Optional[float] = Field(
        default=None,
        description="Relevance score if provided by search API"
    )


class AgentResult(BaseModel):
    """
    Result from agent execution including both final output
    and intermediate steps for debugging.
    """
    
    company_name: str
    final_answer: CompanyInfo
    intermediate_steps: List[dict] = Field(
        default_factory=list,
        description="List of agent thoughts, actions, and observations"
    )
    execution_time: Optional[float] = Field(
        default=None,
        description="Total execution time in seconds"
    )

