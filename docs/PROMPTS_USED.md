# Prompts Currently Used in the Application

This document outlines all prompts that are passed to the LLM model during agent execution.

## Overview

The application uses a **two-part prompt structure**:
1. **System Prompt** - Long, detailed instructions (sent once per conversation)
2. **User Prompt** - Short task-specific message (sent per company research request)

## 1. System Prompt

**Location**: `src/agent/research_agent.py::_build_system_prompt()`

The system prompt is built dynamically and includes:

### Base Instructions
```
You are a focused company research analyst following the ReAct pattern. 
Think step-by-step, decide whether a web search is required, and only 
produce answers grounded in retrieved evidence.
```

### Research Instructions Summary
Loaded from `prompts/gtm.md` and summarized (first 28 bullet points/numbered lines):
- Extracted from: `prompts/gtm.md` (74 lines)
- Summary includes bullet points like:
  - "Detailed company profiling and precise categorization"
  - "Strategic market positioning"
  - Growth Stage classifications
  - Company Size classifications
  - Industry Vertical classifications
  - Financial Health classifications
  - etc.

### Classification Reference
Loaded from `prompts/company-profiling-guide.md` and compiled into:
```
- Growth Stage: Pre-Seed/Idea | Startup | Scale-Up | Mature/Enterprise
- Company Size: Micro/Small (<50) | SMB (50-500) | Mid-Market (500-1000) | Enterprise (>1000)
- Industry Vertical: SaaS (SMB/Scale) | SaaS (Enterprise Scale) | Media & Entertainment | Gaming | ...
- Financial Health: Bootstrapped/Indie | VC-Funded (Early) | VC-Funded (Growth) | PE-Backed | ...
- Budget Maturity: Ad Hoc Spend | Team Budget | Central IT Budget | CCoE/Governance
- Cloud Spend Capacity: < $5K/mo | $5K-$50K/mo | $50K-$250K/mo | $250K+/mo
- Procurement Process: Minimal/Self-Service | Lightweight Review | Formal Review | Enterprise Procurement
- Business & Technology Adoption: Digital Laggards | Digitally-Adopting | Digitally-Transforming | ...
- Buyer Journey: Practitioner-Led | Organization-Led | Partner-Led | Hybrid
- Primary Workload Philosophy: Performance-Intensive | Distributed & Edge-Native | ...
- Key Personas: Deciders | Approvers/Influencers | Users/Practitioners | Partners
- Always accompany each classification with a *_reason field citing evidence
```

### Formatting Requirements
```
- Return a final answer as JSON matching the CompanyInfo schema.
- If data is unavailable, use null or an empty list rather than guessing.
- Include concise text in the description summarising the findings.
- Cite URLs inline when referencing specific claims.
- For every GTM classification (growth_stage, company_size, industry_vertical, 
  sub_industry_vertical, financial_health, business_and_technology_adoption, 
  primary_workload_philosophy, buyer_journey, budget_maturity, 
  cloud_spend_capacity, procurement_process, key_personas), provide a 
  corresponding *_reason field that explains the evidence used.
```

### Schema Information
Lists all CompanyInfo model fields (approximately 30+ fields including all GTM classifications and reason fields)

**Estimated Total Length**: ~2000-3000 tokens

## 2. User Prompt

**Location**: `src/agent/research_agent.py::_build_user_prompt()`

Simple template that gets formatted with the company name:

```
Research the organisation named {company_name}.
Follow the provided instructions, deliberate about missing data, and 
call the web_search_tool whenever you need fresh context.
```

**Example for "BitMovin"**:
```
Research the organisation named BitMovin.
Follow the provided instructions, deliberate about missing data, and 
call the web_search_tool whenever you need fresh context.
```

## 3. Source Files

### `prompts/gtm.md`
**Size**: 74 lines
**Content**: Comprehensive GTM strategy instructions including:
- System prompt instructions for being a GTM expert
- Analysis framework (Step 1, Step 2, Step 3)
- Firmographic essentials
- Economic indicators
- Strategic alignment
- Buyer behavior
- Technical needs
- Evidence-based classification requirements
- Output expectations

### `prompts/company-profiling-guide.md`
**Size**: ~100 lines
**Content**: Detailed classification guide with:
- Growth Stage definitions and examples
- Company Size ranges
- Industry Vertical categories (15+ categories)
- Budget Maturity levels
- Cloud Spend Capacity ranges
- Financial Health classifications
- Procurement Process sophistication
- Business & Technology Adoption spectrum
- Buyer Journey types
- Primary Workload Philosophy types
- Key Personas

### `examples/instructions/research_instructions.md`
**Size**: 46 lines
**Status**: ⚠️ **NOT CURRENTLY USED** - The agent uses `prompts/gtm.md` instead
**Content**: Simpler research instructions (required/optional info, methodology, quality standards)

## Current Complexity Issues

1. **Very Long System Prompt**: ~2000-3000 tokens just for the system prompt
2. **Duplicate Information**: Both `gtm.md` and `company-profiling-guide.md` contain classification info
3. **Complex Instructions**: The GTM prompt has multiple steps and frameworks
4. **Many Required Fields**: ~13 GTM classifications, each requiring a reason field
5. **Summarization Loss**: The `_summarise_markdown()` function only takes first 28 lines from gtm.md, potentially losing important context

## Simplification Opportunities

1. **Reduce System Prompt Length**: 
   - Remove or consolidate classification reference
   - Simplify formatting requirements
   - Use shorter, more direct language

2. **Simplify Instructions**:
   - Replace complex GTM framework with basic company research
   - Remove unnecessary classification categories
   - Focus on core information needed

3. **Consolidate Source Files**:
   - Merge or eliminate redundant information
   - Choose one instruction source instead of combining two

4. **Simplify Output Schema**:
   - Reduce number of required GTM fields
   - Remove reason fields if not essential
   - Focus on basic company information

## Files to Modify for Simplification

1. **`src/agent/research_agent.py`**:
   - `_build_system_prompt()` method (lines 334-358)
   - `_build_user_prompt()` method (lines 360-368)
   - `_summarise_markdown()` function (lines 557-582)
   - `_build_classification_reference()` function (lines 585-625)

2. **`prompts/gtm.md`** - Simplify or replace with basic instructions

3. **`prompts/company-profiling-guide.md`** - Reduce categories or make optional

4. **`src/tools/models.py`** - Simplify CompanyInfo schema to reduce required fields

