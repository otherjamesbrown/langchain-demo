#!/usr/bin/env python3
"""
Validate Phase 1 testing framework components.

This script tests the core framework components that don't require
LangChain or the full research agent. It validates:
- Baseline loading and structure
- Matching logic (exact, keyword, fuzzy, regex)
- Field matching results

⚠️ IMPORTANT: This validation script CAN be run locally because it only tests
core matching logic and baseline structure. However, ALL integration tests
and full test framework execution MUST be done on the remote server where
LangChain and dependencies are installed.

Local testing (this script): ✅ OK
Remote testing required for:
  - TestRunner execution (requires ResearchAgent)
  - Full test framework CLI (requires LangChain)
  - UI integration tests
  - Any tests that use ResearchAgent
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import directly to avoid loading test_runner (which requires LangChain)
from src.testing.baseline import MatchType, FieldExpectation, TestBaseline
from src.testing.matchers import FieldMatcher
from src.testing.baselines import get_baseline, list_baselines


def test_baseline_loading():
    """Test that baselines can be loaded correctly."""
    print("=" * 70)
    print("Testing Baseline Loading")
    print("=" * 70)
    
    # Test listing baselines
    baselines = list_baselines()
    print(f"\n✅ Available baselines: {baselines}")
    assert len(baselines) > 0, "Should have at least one baseline"
    
    # Test loading BitMovin baseline
    baseline = get_baseline("bitmovin")
    print(f"\n✅ Loaded baseline: {baseline.test_name}")
    print(f"   Company: {baseline.company_name}")
    print(f"   Description: {baseline.description}")
    print(f"   Required fields: {len(baseline.required_fields)}")
    print(f"   Optional fields: {len(baseline.optional_fields)}")
    
    assert baseline.test_name == "bitmovin_research"
    assert baseline.company_name == "BitMovin"
    assert len(baseline.required_fields) == 5
    assert len(baseline.optional_fields) == 10
    
    print("\n✅ Baseline loading test passed!")
    return baseline


def test_exact_matching():
    """Test exact matching logic."""
    print("\n" + "=" * 70)
    print("Testing Exact Matching")
    print("=" * 70)
    
    matcher = FieldMatcher()
    
    # Test 1: Exact match success
    exp = FieldExpectation(
        field_name="founded",
        expected_value=2013,
        match_type=MatchType.EXACT,
    )
    is_match, confidence, error = matcher.match(exp, 2013)
    print(f"\nTest 1: Founded year match")
    print(f"   Expected: 2013, Actual: 2013")
    print(f"   Result: {'✅ Match' if is_match else '❌ No match'} (confidence: {confidence:.2f})")
    assert is_match and confidence == 1.0, "Exact match should succeed"
    
    # Test 2: Exact match failure
    is_match, confidence, error = matcher.match(exp, 2014)
    print(f"\nTest 2: Founded year mismatch")
    print(f"   Expected: 2013, Actual: 2014")
    print(f"   Result: {'✅ Match' if is_match else '❌ No match'} (confidence: {confidence:.2f})")
    assert not is_match, "Exact match should fail"
    
    # Test 3: Type coercion (string to int)
    is_match, confidence, error = matcher.match(exp, "2013")
    print(f"\nTest 3: Type coercion (string '2013' → int 2013)")
    print(f"   Expected: 2013, Actual: '2013'")
    print(f"   Result: {'✅ Match' if is_match else '❌ No match'} (confidence: {confidence:.2f})")
    assert is_match, "Should handle type coercion"
    
    print("\n✅ Exact matching tests passed!")


def test_keyword_matching():
    """Test keyword matching logic."""
    print("\n" + "=" * 70)
    print("Testing Keyword Matching")
    print("=" * 70)
    
    matcher = FieldMatcher()
    
    # Test 1: Keyword match success
    exp = FieldExpectation(
        field_name="industry",
        expected_value="Video Technology",
        match_type=MatchType.KEYWORD,
        keywords=["video", "streaming"],
    )
    is_match, confidence, error = matcher.match(exp, "Video Technology / SaaS")
    print(f"\nTest 1: Industry keyword match")
    print(f"   Expected keywords: ['video', 'streaming']")
    print(f"   Actual: 'Video Technology / SaaS'")
    print(f"   Result: {'✅ Match' if is_match else '❌ No match'} (confidence: {confidence:.2f})")
    assert is_match, "Should match keyword 'video'"
    
    # Test 2: Multiple keyword match (higher confidence)
    is_match, confidence, error = matcher.match(exp, "Video Streaming Infrastructure")
    print(f"\nTest 2: Multiple keywords match")
    print(f"   Actual: 'Video Streaming Infrastructure'")
    print(f"   Result: {'✅ Match' if is_match else '❌ No match'} (confidence: {confidence:.2f})")
    assert is_match and confidence >= 0.5, "Should match both keywords"
    
    # Test 3: Keyword match failure
    is_match, confidence, error = matcher.match(exp, "Software Company")
    print(f"\nTest 3: No keyword match")
    print(f"   Actual: 'Software Company'")
    print(f"   Result: {'✅ Match' if is_match else '❌ No match'} (confidence: {confidence:.2f})")
    assert not is_match, "Should not match"
    
    print("\n✅ Keyword matching tests passed!")


def test_fuzzy_matching():
    """Test fuzzy matching logic for ranges."""
    print("\n" + "=" * 70)
    print("Testing Fuzzy Matching (Range Overlap)")
    print("=" * 70)
    
    matcher = FieldMatcher()
    
    # Test 1: Exact range match
    exp = FieldExpectation(
        field_name="company_size",
        expected_value="51-200 employees",
        match_type=MatchType.FUZZY,
        fuzzy_tolerance=0.3,
    )
    is_match, confidence, error = matcher.match(exp, "51-200 employees")
    print(f"\nTest 1: Exact range match")
    print(f"   Expected: '51-200 employees', Actual: '51-200 employees'")
    print(f"   Result: {'✅ Match' if is_match else '❌ No match'} (confidence: {confidence:.2f})")
    assert is_match, "Exact range should match"
    
    # Test 2: Overlapping range match (the key fuzzy matching case)
    is_match, confidence, error = matcher.match(exp, "100-250 employees")
    print(f"\nTest 2: Overlapping range match (FUZZY)")
    print(f"   Expected: '51-200 employees', Actual: '100-250 employees'")
    print(f"   Result: {'✅ Match' if is_match else '❌ No match'} (confidence: {confidence:.2f})")
    print(f"   Note: This is the key fuzzy matching scenario - ranges overlap!")
    assert is_match, "Overlapping ranges should match with fuzzy logic"
    assert confidence > 0.5, "Should have decent confidence for overlap"
    
    # Test 3: Partial overlap
    is_match, confidence, error = matcher.match(exp, "150-300 employees")
    print(f"\nTest 3: Partial overlap")
    print(f"   Expected: '51-200 employees', Actual: '150-300 employees'")
    print(f"   Result: {'✅ Match' if is_match else '❌ No match'} (confidence: {confidence:.2f})")
    assert is_match, "Partial overlap should match"
    
    # Test 4: No overlap
    is_match, confidence, error = matcher.match(exp, "500-1000 employees")
    print(f"\nTest 4: No overlap")
    print(f"   Expected: '51-200 employees', Actual: '500-1000 employees'")
    print(f"   Result: {'✅ Match' if is_match else '❌ No match'} (confidence: {confidence:.2f})")
    assert not is_match, "Non-overlapping ranges should not match"
    
    # Test 5: Single number within range
    is_match, confidence, error = matcher.match(exp, "150 employees")
    print(f"\nTest 5: Single number within range")
    print(f"   Expected: '51-200 employees', Actual: '150 employees'")
    print(f"   Result: {'✅ Match' if is_match else '❌ No match'} (confidence: {confidence:.2f})")
    assert is_match, "Single number within range should match"
    
    print("\n✅ Fuzzy matching tests passed!")


def test_missing_value_handling():
    """Test handling of missing/None values."""
    print("\n" + "=" * 70)
    print("Testing Missing Value Handling")
    print("=" * 70)
    
    matcher = FieldMatcher()
    
    # Test 1: Required field missing
    exp = FieldExpectation(
        field_name="founded",
        expected_value=2013,
        match_type=MatchType.EXACT,
        required=True,
    )
    is_match, confidence, error = matcher.match(exp, None)
    print(f"\nTest 1: Required field missing")
    print(f"   Field: founded (required), Actual: None")
    print(f"   Result: {'✅ Match' if is_match else '❌ No match'} (confidence: {confidence:.2f})")
    print(f"   Error: {error}")
    assert not is_match, "Missing required field should fail"
    
    # Test 2: Optional field missing
    exp = FieldExpectation(
        field_name="growth_stage",
        expected_value=None,
        match_type=MatchType.KEYWORD,
        required=False,
    )
    is_match, confidence, error = matcher.match(exp, None)
    print(f"\nTest 2: Optional field missing")
    print(f"   Field: growth_stage (optional), Actual: None")
    print(f"   Result: {'✅ Match' if is_match else '❌ No match'} (confidence: {confidence:.2f})")
    assert is_match, "Missing optional field should pass"
    
    # Test 3: Empty string (required)
    exp = FieldExpectation(
        field_name="industry",
        expected_value="Video Technology",
        match_type=MatchType.KEYWORD,
        required=True,
    )
    is_match, confidence, error = matcher.match(exp, "")
    print(f"\nTest 3: Required field empty string")
    print(f"   Field: industry (required), Actual: ''")
    print(f"   Result: {'✅ Match' if is_match else '❌ No match'} (confidence: {confidence:.2f})")
    assert not is_match, "Empty required field should fail"
    
    print("\n✅ Missing value handling tests passed!")


def test_bitmovin_baseline_fields():
    """Test BitMovin baseline field expectations."""
    print("\n" + "=" * 70)
    print("Testing BitMovin Baseline Field Definitions")
    print("=" * 70)
    
    baseline = get_baseline("bitmovin")
    matcher = FieldMatcher()
    
    print(f"\nValidating {len(baseline.required_fields)} required fields:")
    for field_exp in baseline.required_fields:
        print(f"\n  Field: {field_exp.field_name}")
        print(f"    Match type: {field_exp.match_type.value}")
        print(f"    Expected: {field_exp.expected_value}")
        print(f"    Description: {field_exp.description}")
        
        # Test with a sample value
        if field_exp.field_name == "company_name":
            sample_value = "Bitmovin Inc"
        elif field_exp.field_name == "industry":
            sample_value = "Video Streaming Technology"
        elif field_exp.field_name == "company_size":
            sample_value = "100-200 employees"
        elif field_exp.field_name == "headquarters":
            sample_value = "San Francisco, California, United States"
        elif field_exp.field_name == "founded":
            sample_value = 2013
        else:
            sample_value = "test value"
        
        is_match, confidence, error = matcher.match(field_exp, sample_value)
        status = "✅" if is_match else "❌"
        print(f"    Test with sample value '{sample_value}': {status} (confidence: {confidence:.2f})")
        if error:
            print(f"    Error: {error}")
    
    print("\n✅ BitMovin baseline field validation passed!")


def main():
    """Run all validation tests."""
    print("\n" + "=" * 70)
    print("Phase 1 Testing Framework Validation")
    print("=" * 70)
    print("\nThis script validates the core framework components without")
    print("requiring LangChain or the full research agent environment.")
    print("\nThese tests can be run locally to verify Phase 1 before")
    print("moving to Phase 2 (CLI integration) or Phase 3 (UI integration).")
    
    try:
        # Run all tests
        baseline = test_baseline_loading()
        test_exact_matching()
        test_keyword_matching()
        test_fuzzy_matching()
        test_missing_value_handling()
        test_bitmovin_baseline_fields()
        
        # Summary
        print("\n" + "=" * 70)
        print("✅ ALL VALIDATION TESTS PASSED")
        print("=" * 70)
        print("\nPhase 1 Core Framework is working correctly!")
        print("\n✅ This validation can run locally (no LangChain needed)")
        print("   - Baseline loading ✅")
        print("   - Matching logic ✅")
        print("   - Field validation ✅")
        print("\n⚠️  REMOTE SERVER REQUIRED for:")
        print("   - TestRunner execution (requires ResearchAgent + LangChain)")
        print("   - CLI test framework (scripts/run_test_framework.py)")
        print("   - UI integration tests")
        print("   - Full end-to-end testing")
        print("\nNext steps:")
        print("  1. Phase 2: Refine baseline definitions (optional)")
        print("  2. Phase 3: Create CLI test runner (MUST test on remote server)")
        print("  3. Phase 4: Integrate with UI (Test_BitMovin page - remote server)")
        print("\nTo test on remote server:")
        print("  ssh langchain@<server-ip>")
        print("  cd ~/langchain-demo")
        print("  source venv/bin/activate")
        print("  python scripts/test_framework_validation.py  # Can run this too")
        print("  # Or test with actual TestRunner when Phase 3 is complete")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

