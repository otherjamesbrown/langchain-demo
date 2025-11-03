# Shared Utilities Refactoring Plan

**Status**: 📋 **PROPOSAL**  
**Priority**: Medium (code quality improvement, not blocking)  
**Related**: `docs/implemented/MODEL_AVAILABILITY_UTILITIES.md`, `docs/principles/ARCHITECTURAL_PRINCIPLES.md`

## Overview

After implementing shared model availability utilities, this document identifies additional opportunities to consolidate duplicate code patterns into reusable utilities. This follows the DRY (Don't Repeat Yourself) principle and improves maintainability.

## Analysis Summary

**Current State:**
- ✅ **Model Availability** - Already consolidated in `src/utils/model_availability.py`
- ❌ **Database Session Management** - Duplicated across `src/research/` modules
- ❌ **Streamlit DB Initialization** - Duplicated across all UI pages
- ❌ **API Key Validation in Tests** - Duplicated in `tests/test_bitmovin_research.py`
- ❌ **Placeholder API Key Checks** - Still duplicated in some UI pages

**Code Reduction Potential**: ~200-300 lines of duplicate code

---

## 1. Database Session Context Manager

### Problem

Multiple files in `src/research/` duplicate the same session management pattern:

```python
if session is None:
    session = get_session()
    should_close = True
else:
    should_close = False

try:
    # ... operations ...
finally:
    if should_close:
        session.close()
```

**Files Affected**:
- `src/research/search_executor.py` - 3 occurrences
- `src/research/llm_processor.py` - 1 occurrence
- `src/research/query_generator.py` - 3 occurrences
- `src/research/validation.py` - 3 occurrences (uses different pattern without proper cleanup)

**Total**: ~70 lines of duplicate code

### Solution

Create a context manager utility in `src/utils/database.py`:

```python
from contextlib import contextmanager
from sqlalchemy.orm import Session
from src.database.schema import get_session

@contextmanager
def get_db_session(session: Optional[Session] = None):
    """
    Context manager for database sessions.
    
    If session is provided, uses it (doesn't close).
    If None, creates new session and closes on exit.
    
    Usage:
        with get_db_session() as session:
            # Use session here
        
        # Or with existing session:
        with get_db_session(existing_session) as session:
            # Uses provided session, won't close it
    """
    if session is None:
        session = get_session()
        should_close = True
    else:
        should_close = False
    
    try:
        yield session
    finally:
        if should_close:
            session.close()
```

**Benefits**:
- Eliminates ~70 lines of duplicate code
- Ensures proper cleanup even if exceptions occur
- Clearer, more Pythonic code
- Prevents leaks in `validation.py` which doesn't always close sessions

**Migration**:
```python
# Before
if session is None:
    session = get_session()
    should_close = True
else:
    should_close = False
try:
    # operations
finally:
    if should_close:
        session.close()

# After
from src.utils.database import get_db_session

with get_db_session(session) as db_session:
    # operations using db_session
```

---

## 2. Streamlit Database Initialization

### Problem

All Streamlit UI pages duplicate the same database initialization pattern:

```python
@st.cache_resource
def init_db():
    """Initialize database connection."""
    create_database()
    return get_session()
```

**Files Affected**:
- `src/ui/pages/1_🤖_Local_LLM.py`
- `src/ui/pages/2_📊_Monitoring.py`
- `src/ui/pages/3_🔬_Agent.py`
- `src/ui/pages/4_🧪_Test_BitMovin.py`
- `src/ui/streamlit_dashboard.py` - 4 occurrences

**Also duplicated**:
- Error handling pattern:
```python
try:
    session = init_db()
except Exception as e:
    st.error(f"Failed to connect to database: {e}")
    st.stop()
```

**Total**: ~40 lines of duplicate code across 8+ occurrences

### Solution

Create shared utility in `src/utils/streamlit_helpers.py`:

```python
import streamlit as st
from src.database.schema import create_database, get_session

@st.cache_resource
def get_streamlit_db_session():
    """
    Get database session for Streamlit pages (cached).
    
    Returns:
        SQLAlchemy Session object
        
    Raises:
        Exception: If database connection fails
    """
    create_database()
    return get_session()


def init_streamlit_db() -> Session:
    """
    Initialize database for Streamlit pages with error handling.
    
    Returns:
        SQLAlchemy Session object
        
    Exits:
        Calls st.stop() if database connection fails
    """
    try:
        return get_streamlit_db_session()
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        st.stop()
        raise  # Will never execute but helps type checkers
```

**Benefits**:
- Single source of truth for Streamlit DB initialization
- Consistent error handling
- Easy to add logging/metrics in one place
- Type hints for better IDE support

**Migration**:
```python
# Before
@st.cache_resource
def init_db():
    create_database()
    return get_session()

try:
    session = init_db()
except Exception as e:
    st.error(f"Failed to connect to database: {e}")
    st.stop()

# After
from src.utils.streamlit_helpers import init_streamlit_db

session = init_streamlit_db()  # Handles errors internally
```

---

## 3. Test Utilities: API Key Validation

### Problem

`tests/test_bitmovin_research.py` duplicates API key validation logic that's already available:

**Current Code** (lines 67-102):
```python
def _check_api_key_available(model_type: str) -> bool:
    """Check if API key is available for the model type."""
    if model_type == "local":
        # Local model path check...
        return False
    
    # Check database first
    try:
        from src.database.operations import get_api_key
        db_key = get_api_key(model_type)
        if db_key and db_key.strip():
            return True
    except Exception:
        pass
    
    # Fallback to environment variables
    env_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GOOGLE_API_KEY",
    }
    api_key_env = env_map.get(model_type)
    api_key = os.getenv(api_key_env)
    return api_key is not None and api_key.strip() != ""
```

**Problem**: This logic duplicates what `src/utils/model_availability.py` already provides:
- `is_remote_model_usable()` - Checks API keys for remote models
- `is_local_model_usable()` - Checks local model paths
- `get_available_models()` - Returns all usable models

**Total**: ~35 lines of duplicate code

### Solution

Replace with shared utilities:

```python
# Before
def _check_api_key_available(model_type: str) -> bool:
    # ... 35 lines of duplicate code ...

# After
from src.utils.model_availability import (
    is_local_model_usable,
    is_remote_model_usable,
    get_available_models
)

# For test filtering
def _check_model_usable(model_type: str, model_path: Optional[str] = None) -> bool:
    """Check if a model is usable (wrapper for shared utilities)."""
    if model_type == "local":
        return is_local_model_usable(model_path)
    else:
        return is_remote_model_usable(model_type)
```

**Benefits**:
- Uses already-tested shared utilities
- Consistent validation logic across codebase
- Reduces maintenance burden

---

## 4. UI Model Filtering Consolidation

### Problem

UI pages still have some inline model filtering that could use `get_available_models()` more consistently:

**Current State**:
- ✅ `src/ui/pages/4_🧪_Test_BitMovin.py` - Uses `get_available_models()` ✅
- ✅ `src/ui/pages/3_🔬_Agent.py` - Uses inline filtering (lines 73-99), but could use utilities
- ✅ `src/ui/pages/1_🤖_Local_LLM.py` - Uses inline filtering (lines 69-76)

**Issue**: While `3_🔬_Agent.py` could use `get_available_models()`, it filters by provider inline and has additional validation that might be UI-specific.

### Assessment

**Recommendation**: **LOW PRIORITY**

The current filtering in UI pages is acceptable because:
1. They filter by provider (`provider="local"`) which `get_available_models()` supports
2. They have UI-specific error messages
3. The logic is simple (just path existence checks)

**However**, we could create a helper:

```python
# src/utils/streamlit_helpers.py

def get_ui_available_models(
    provider_filter: Optional[List[str]] = None,
    session: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """
    Get available models for UI display with UI-friendly formatting.
    
    Returns models with additional metadata for Streamlit widgets.
    """
    models = get_available_models(provider_filter=provider_filter, session=session)
    # Could add UI-specific formatting here
    return models
```

**Priority**: **LOW** - Current implementation is fine, this would be a nice-to-have

---

## 5. Placeholder API Key Detection (Already Addressed)

### Status: ✅ **RESOLVED**

The `is_placeholder_api_key()` function in `src/utils/model_availability.py` already provides this functionality. However, some UI pages still have inline placeholder checks:

**Files with inline checks**:
- `src/ui/pages/3_🔬_Agent.py` (lines 89-95) - Should use `is_placeholder_api_key()`

**Recommendation**: Refactor `3_🔬_Agent.py` to use shared utilities (already partially done via `get_available_models()`, but inline check remains).

---

## Implementation Priority

### Phase 1: High Impact, Low Risk (Recommended First)
1. **Database Session Context Manager** (`src/utils/database.py`)
   - High impact: ~70 lines duplicated across 4 files
   - Low risk: Simple context manager pattern
   - Easy to test and migrate

2. **Streamlit DB Initialization** (`src/utils/streamlit_helpers.py`)
   - High impact: Used in 8+ places
   - Low risk: Simple function extraction
   - Consistent error handling

### Phase 2: Medium Impact (Optional)
3. **Test Utilities Refactoring**
   - Medium impact: Only affects test files
   - Low risk: Tests should use same utilities as production code
   - Good practice: Ensures tests validate production logic

### Phase 3: Low Priority (Nice-to-Have)
4. **UI Model Filtering Helpers**
   - Low impact: Current implementation is acceptable
   - Could improve consistency
   - Not blocking any functionality

---

## Files to Create/Modify

### New Files
1. `src/utils/database.py` - Database session utilities
2. `src/utils/streamlit_helpers.py` - Streamlit-specific utilities

### Files to Modify

**Phase 1**:
- `src/research/search_executor.py` - Use `get_db_session()`
- `src/research/llm_processor.py` - Use `get_db_session()`
- `src/research/query_generator.py` - Use `get_db_session()`
- `src/research/validation.py` - Use `get_db_session()` (also fixes session leaks)
- `src/ui/pages/1_🤖_Local_LLM.py` - Use `init_streamlit_db()`
- `src/ui/pages/2_📊_Monitoring.py` - Use `init_streamlit_db()`
- `src/ui/pages/3_🔬_Agent.py` - Use `init_streamlit_db()`
- `src/ui/pages/4_🧪_Test_BitMovin.py` - Use `init_streamlit_db()`
- `src/ui/streamlit_dashboard.py` - Use `init_streamlit_db()` (4 places)

**Phase 2**:
- `tests/test_bitmovin_research.py` - Replace `_check_api_key_available()` with shared utilities
- `src/ui/pages/3_🔬_Agent.py` - Remove inline placeholder API key check

---

## Testing Strategy

### For Database Session Manager
```python
def test_get_db_session_creates_and_closes():
    """Test that context manager creates and closes session."""
    with get_db_session() as session:
        assert session is not None
        # Session should be closed after exit
    
def test_get_db_session_uses_provided():
    """Test that provided session is not closed."""
    existing = get_session()
    try:
        with get_db_session(existing) as session:
            assert session is existing
        # Session should still be open
        assert existing.is_active
    finally:
        existing.close()
```

### For Streamlit Helpers
- Test that `get_streamlit_db_session()` returns valid session
- Test that `init_streamlit_db()` handles errors gracefully (mock `create_database()` to raise)

---

## Benefits Summary

| Utility | Lines Reduced | Files Affected | Risk Level |
|---------|--------------|----------------|------------|
| Database Session Manager | ~70 | 4 files | Low |
| Streamlit DB Init | ~40 | 8+ places | Low |
| Test Utilities | ~35 | 1 file | Low |
| **Total** | **~145 lines** | **13+ files** | **Low** |

**Additional Benefits**:
- Better error handling (especially in `validation.py`)
- Consistent patterns across codebase
- Easier to add logging/metrics in one place
- Type hints improve IDE support
- Easier to test (test utilities once, use everywhere)

---

## Related Documentation

- `docs/implemented/MODEL_AVAILABILITY_UTILITIES.md` - Previous refactoring example
- `docs/principles/ARCHITECTURAL_PRINCIPLES.md` - DRY principle guidance
- `src/utils/model_availability.py` - Existing shared utilities example

---

## Next Steps

1. **Review this proposal** - Confirm priorities and approach
2. **Implement Phase 1** - Database session manager and Streamlit helpers
3. **Test thoroughly** - Ensure no regressions
4. **Update documentation** - Add utilities to architectural principles
5. **Migrate files** - One file at a time, test after each

---

**Created**: 2025-01-XX  
**Status**: 📋 Proposal - Awaiting approval  
**Priority**: Medium (code quality improvement)

