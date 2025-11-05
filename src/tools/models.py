"""
Pydantic models for structured company information extraction.

These models define the schema for company data that the agent will extract
using LLM-based structured output parsing.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class CompanyInfo(BaseModel):
    """Structured company and GTM profile extracted by the research agent."""

    # ------------------------------------------------------------------
    # Core company information
    # ------------------------------------------------------------------
    company_name: str = Field(
        description="Official company name as listed in primary sources."
    )

    company_size: str = Field(
        description=(
            "Number of employees, ideally as a range (e.g., '201-500 employees')."
        )
    )

    headquarters: str = Field(
        description="Primary headquarters location (city, region, country)."
    )

    founded: Optional[int] = Field(
        default=None,
        description="The year the company was founded if available."
    )

    description: Optional[str] = Field(
        default=None,
        description="Concise narrative describing what the company does."
    )

    website: Optional[str] = Field(
        default=None,
        description="Official website URL."
    )

    revenue: Optional[str] = Field(
        default=None,
        description="Annual revenue range or specific value when reported."
    )

    funding_stage: Optional[str] = Field(
        default=None,
        description="Funding stage or ownership status (e.g., 'Series C')."
    )

    # ------------------------------------------------------------------
    # GTM profiling classifications (Company Profiling Guide)
    # ------------------------------------------------------------------
    growth_stage: Optional[str] = Field(
        default=None,
        description=(
            "Growth stage classification (Pre-Seed/Idea, Startup, Scale-Up, or Mature/Enterprise)."
        )
    )

    industry_vertical: Optional[str] = Field(
        default=None,
        description=(
            "Industry vertical label from the profiling guide (e.g., 'Media & Entertainment')."
        )
    )

    sub_industry_vertical: Optional[str] = Field(
        default=None,
        description=(
            "More specific sub-vertical from the profiling guide (e.g., 'Media SaaS')."
        )
    )

    business_and_technology_adoption: Optional[str] = Field(
        default=None,
        description=(
            "Adoption spectrum label (e.g., 'Digitally-Transforming', 'Digital-Native (SMB/Scale)')."
        )
    )

    buyer_journey: Optional[str] = Field(
        default=None,
        description=(
            "Buyer journey motion (Practitioner-Led, Organization-Led, Partner-Led, or Hybrid)."
        )
    )

    cloud_spend_capacity: Optional[str] = Field(
        default=None,
        description=(
            "Estimated cloud spend capacity (<$5K/month, $5K-$50K/month, "
            "$50K-$250K/month, or $250K+/month)."
        )
    )

    class Config:
        """Pydantic configuration with educational example."""

        json_schema_extra = {
            "example": {
                "company_name": "Bitmovin",
                "company_size": "201-500 employees",
                "headquarters": "Vienna, Austria",
                "founded": 2013,
                "description": (
                    "Video streaming technology company providing encoding, player, and analytics platforms."
                ),
                "website": "https://bitmovin.com",
                "revenue": "$10M - $50M",
                "funding_stage": "Series C",
                "growth_stage": "Scale-Up",
                "industry_vertical": "Media & Entertainment",
                "sub_industry_vertical": "Media SaaS",
                "business_and_technology_adoption": "Digital-Native (Enterprise Scale)",
                "buyer_journey": "Hybrid",
                "cloud_spend_capacity": "$50K-$250K/month"
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


