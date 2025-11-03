#!/usr/bin/env python3
"""
BitMovin company research baseline definition.

This baseline defines expected values and validation rules for testing
the research agent's ability to extract BitMovin company information.

Educational Focus:
- Shows how to define comprehensive test expectations
- Demonstrates different matching strategies (exact, keyword, fuzzy)
- Separates required fields (must pass) from optional fields (nice to have)
"""

from src.testing.baseline import TestBaseline, FieldExpectation, MatchType


BITMOVIN_BASELINE = TestBaseline(
    test_name="bitmovin_research",
    company_name="BitMovin",
    description="BitMovin company research baseline - video streaming infrastructure",
    
    required_fields=[
        FieldExpectation(
            field_name="company_name",
            expected_value="Bitmovin",
            match_type=MatchType.KEYWORD,
            keywords=["bitmovin"],
            required=True,
            description="Company name should contain 'bitmovin' (case-insensitive)"
        ),
        FieldExpectation(
            field_name="industry",
            expected_value="Video Technology / SaaS",
            match_type=MatchType.KEYWORD,
            keywords=["video", "streaming"],
            required=True,
            description="Industry should relate to video/streaming"
        ),
        FieldExpectation(
            field_name="company_size",
            expected_value="51-200 employees",
            match_type=MatchType.FUZZY,
            fuzzy_tolerance=0.3,  # Allow ±30% variation
            required=True,
            description="Company size should be in 51-200 range (fuzzy match)"
        ),
        FieldExpectation(
            field_name="headquarters",
            expected_value="San Francisco, California",
            match_type=MatchType.KEYWORD,
            keywords=["san francisco", "california", "sf"],
            required=True,
            description="Headquarters should be in San Francisco area"
        ),
        FieldExpectation(
            field_name="founded",
            expected_value=2013,
            match_type=MatchType.EXACT,
            required=True,
            description="Founded year must be exactly 2013"
        ),
    ],
    
    optional_fields=[
        FieldExpectation(
            field_name="growth_stage",
            expected_value=None,
            match_type=MatchType.KEYWORD,
            keywords=["scale-up", "scaleup", "startup", "mature"],
            required=False,
            description="Growth stage classification"
        ),
        FieldExpectation(
            field_name="industry_vertical",
            expected_value=None,
            match_type=MatchType.KEYWORD,
            keywords=["media", "entertainment", "technology"],
            required=False,
            description="Industry vertical classification"
        ),
        FieldExpectation(
            field_name="sub_industry_vertical",
            expected_value=None,
            match_type=MatchType.KEYWORD,
            keywords=["media saas", "video", "streaming"],
            required=False,
            description="Sub-industry vertical classification"
        ),
        FieldExpectation(
            field_name="financial_health",
            expected_value=None,
            match_type=MatchType.KEYWORD,
            keywords=["vc-funded", "funded", "venture", "capital"],
            required=False,
            description="Financial health classification"
        ),
        FieldExpectation(
            field_name="business_and_technology_adoption",
            expected_value=None,
            match_type=MatchType.KEYWORD,
            keywords=["digital-native", "digital", "native", "transforming"],
            required=False,
            description="Business and technology adoption classification"
        ),
        FieldExpectation(
            field_name="primary_workload_philosophy",
            expected_value=None,
            match_type=MatchType.KEYWORD,
            keywords=["performance", "distributed", "edge", "reliability"],
            required=False,
            description="Primary workload philosophy classification"
        ),
        FieldExpectation(
            field_name="buyer_journey",
            expected_value=None,
            match_type=MatchType.KEYWORD,
            keywords=["practitioner", "organization", "partner", "hybrid"],
            required=False,
            description="Buyer journey motion classification"
        ),
        FieldExpectation(
            field_name="budget_maturity",
            expected_value=None,
            match_type=MatchType.KEYWORD,
            keywords=["central", "department", "project", "budget"],
            required=False,
            description="Budget maturity classification"
        ),
        FieldExpectation(
            field_name="cloud_spend_capacity",
            expected_value=None,
            match_type=MatchType.FUZZY,
            fuzzy_tolerance=0.4,  # Allow wide variation for ranges
            required=False,
            description="Cloud spend capacity range"
        ),
        FieldExpectation(
            field_name="procurement_process",
            expected_value=None,
            match_type=MatchType.KEYWORD,
            keywords=["formal", "informal", "review", "process"],
            required=False,
            description="Procurement process classification"
        ),
    ],
    
    metadata={
        "company_type": "SaaS",
        "domain": "video_technology",
        "difficulty": "medium",
        "notes": (
            "BitMovin is a well-known video streaming technology company. "
            "The fuzzy matching for company_size handles variations like "
            "'100-250 employees' matching '51-200 employees' due to range overlap."
        )
    }
)

