# Fuzzy Matching Logic - Examples & Reference

## Overview

Fuzzy matching allows flexible validation of field values that may vary slightly while still being "correct". This document shows concrete examples of how fuzzy matching works.

---

## Employee Range Matching

### Example 1: Exact Overlap
**Expected**: `"51-200 employees"`  
**Actual**: `"100-200 employees"`  
**Algorithm**:
1. Extract numbers: Expected `[51, 200]`, Actual `[100, 200]`
2. Expected range: `51-200` (149 employees range)
3. Tolerance (30%): `149 * 0.3 = 44.7` → ~45 employees
4. Expanded expected: `51-45` to `200+45` = `6-245`
5. Actual range: `100-200`
6. Overlap: `100-200` (100 employees overlap)
7. Confidence: `100/149 = 0.67` (67%)

**Result**: ✅ **MATCH** (confidence: 67%)

### Example 2: Partial Overlap
**Expected**: `"51-200 employees"`  
**Actual**: `"250-500 employees"`  
**Algorithm**:
1. Extract numbers: Expected `[51, 200]`, Actual `[250, 500]`
2. Expanded expected (with tolerance): `6-245`
3. Actual range: `250-500`
4. Overlap check: `250` > `245` → **NO OVERLAP**

**Result**: ❌ **NO MATCH**

### Example 3: Equivalent Ranges
**Expected**: `"200-500 employees"`  
**Actual**: `"250-500 employees"`  
**Algorithm**:
1. Extract numbers: Expected `[200, 500]`, Actual `[250, 500]`
2. Expected range: `200-500` (300 employees range)
3. Tolerance (30%): `300 * 0.3 = 90`
4. Expanded expected: `200-90` to `500+90` = `110-590`
5. Actual range: `250-500`
6. Overlap: `250-500` (250 employees overlap)
7. Confidence: `250/300 = 0.83` (83%)

**Result**: ✅ **MATCH** (confidence: 83%)

### Example 4: Different Formats
**Expected**: `"51-200 employees"`  
**Actual**: `"51 to 200 employees"`  
**Algorithm**:
1. Extract numbers: Both `[51, 200]` (format doesn't matter)
2. Exact match of numbers

**Result**: ✅ **MATCH** (confidence: 100%)

### Example 5: Single Number vs Range
**Expected**: `"200-500 employees"`  
**Actual**: `"300 employees"`  
**Algorithm**:
1. Extract numbers: Expected `[200, 500]`, Actual `[300]`
2. Treat single number as range: `300-300`
3. Check if `300` falls within expanded range `110-590`
4. `300` is within range ✅

**Result**: ✅ **MATCH** (confidence: ~90% - single number in middle of range)

---

## Keyword Matching

### Example 1: Single Keyword Match
**Field**: `industry`  
**Expected Keywords**: `["video", "streaming"]`  
**Actual**: `"Video Technology Company"`  
**Algorithm**:
- Normalize to lowercase: `"video technology company"`
- Check keywords: Contains `"video"` ✅
- Confidence: `1/2 = 0.5` (1 of 2 keywords found)

**Result**: ✅ **MATCH** (confidence: 50%)

### Example 2: Multiple Keywords Match
**Field**: `industry`  
**Expected Keywords**: `["video", "streaming"]`  
**Actual**: `"Video Streaming Infrastructure"`  
**Algorithm**:
- Contains both `"video"` and `"streaming"` ✅
- Confidence: `2/2 = 1.0` (both keywords found)

**Result**: ✅ **MATCH** (confidence: 100%)

### Example 3: No Match
**Field**: `industry`  
**Expected Keywords**: `["video", "streaming"]`  
**Actual**: `"Software Development"`  
**Algorithm**:
- No keywords found ❌

**Result**: ❌ **NO MATCH**

---

## Location Matching (Keyword-based)

### Example 1: Exact Match
**Expected**: `"San Francisco, California"`  
**Expected Keywords**: `["san francisco", "california", "sf"]`  
**Actual**: `"San Francisco, CA, United States"`  
**Algorithm**:
- Contains `"san francisco"` ✅
- Contains `"california"` (via "CA") ✅
- Confidence: `2/3 = 0.67`

**Result**: ✅ **MATCH** (confidence: 67%)

### Example 2: Abbreviation Match
**Expected**: `"San Francisco, California"`  
**Expected Keywords**: `["san francisco", "california", "sf"]`  
**Actual**: `"SF, CA"`  
**Algorithm**:
- Contains `"sf"` ✅
- Contains `"ca"` (California abbreviation) - might need custom logic
- Confidence: `1/3 = 0.33` (if CA not recognized as California)

**Result**: ✅ **MATCH** (confidence: 33%) - Could improve with abbreviation mapping

---

## String Similarity Matching

### Example 1: Similar Strings
**Expected**: `"Bitmovin"`  
**Actual**: `"BitMovin"`  
**Algorithm** (Jaccard similarity on bigrams):
- Bigrams: Similar character pairs
- High overlap → High similarity

**Result**: ✅ **MATCH** (confidence: ~95%)

### Example 2: Different but Similar
**Expected**: `"Video Streaming Platform"`  
**Actual**: `"Video Stream Platform"`  
**Algorithm**:
- Many shared bigrams
- Similarity: ~85%

**Result**: ✅ **MATCH** (confidence: 85%)

---

## Tolerance Settings

### Configurable Tolerance per Field

```python
FieldExpectation(
    field_name="company_size",
    match_type=MatchType.FUZZY,
    fuzzy_tolerance=0.3,  # 30% tolerance
    # ...
)

FieldExpectation(
    field_name="revenue",
    match_type=MatchType.FUZZY,
    fuzzy_tolerance=0.5,  # 50% tolerance (revenue often varies more)
    # ...
)
```

**Recommendations**:
- **Company Size**: 30% tolerance (allows "200-500" ≈ "250-500")
- **Revenue**: 50% tolerance (revenue ranges vary widely)
- **Headcount**: 20% tolerance (more precise)
- **Founded Year**: 0% tolerance (exact match only)

---

## Confidence Score Interpretation

| Confidence | Interpretation | Visual Indicator |
|------------|----------------|------------------|
| **0.9 - 1.0** | Excellent match | ✅ Green, solid |
| **0.7 - 0.9** | Good match | ✅ Green, partial |
| **0.5 - 0.7** | Acceptable match | ⚠️ Yellow |
| **0.3 - 0.5** | Weak match | ⚠️ Orange |
| **0.0 - 0.3** | Poor/no match | ❌ Red |

---

## Matching Strategy Selection Guide

### Use EXACT when:
- Values must be identical (e.g., founded year, specific IDs)
- Precision is critical
- Example: `founded = 2013` (must be exactly 2013)

### Use KEYWORD when:
- Value must contain specific terms
- Order/structure doesn't matter
- Example: `industry` must contain "video" or "streaming"

### Use FUZZY when:
- Numeric ranges that may vary slightly
- Approximate values are acceptable
- Example: `company_size = "200-500"` ≈ `"250-500"`

### Use REGEX when:
- Complex pattern matching needed
- Format validation (e.g., URLs, emails)
- Example: Website URL validation

### Use CUSTOM when:
- Complex business logic
- Multi-field dependencies
- Example: Validate revenue makes sense for company_size

---

## Edge Cases

### Empty/None Values
- **Required fields**: Always fail if None/empty
- **Optional fields**: Always pass if None/empty (confidence: 0.0)

### Type Mismatches
- String `"2013"` vs Integer `2013` → Automatic type coercion
- Lists vs Strings → Try to convert appropriately

### Multiple Formats
- "51-200 employees" vs "51 to 200 employees" vs "51–200" (em dash)
- All handled via number extraction (format-agnostic)

---

**Last Updated**: 2025-01-XX  
**Related Docs**: `docs/TESTING_FRAMEWORK_PLAN.md`

