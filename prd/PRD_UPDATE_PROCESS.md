# PRD Update Process

This document describes the process for keeping Product Requirements Documents (PRDs) in sync with the actual implementation.

---

## Overview

PRDs should accurately reflect what has been built. When changes are made to the system, PRDs must be updated to maintain accuracy.

---

## PRD Documents

### Main PRD

**File:** `prd/PRD_CURRENT_STATE.md`

This is the **primary PRD** that documents the complete current state of the system. It should be updated whenever:

- New features are added
- Existing features are modified or removed
- Architecture changes are made
- Major components are added or removed

### Update Log

**File:** `prd/PRD_UPDATES.md`

This file tracks all changes made to the system and corresponding PRD updates. Use it to:

- Document what changed
- Track when changes were made
- Link to implementation details
- Provide migration notes if needed

---

## Update Process

### When to Update PRDs

Update PRDs when you:

1. ✅ **Add a new feature** - Document the feature in the appropriate section
2. ✅ **Modify existing functionality** - Update the relevant section
3. ✅ **Remove a feature** - Mark as removed/obsolete
4. ✅ **Change architecture** - Update architecture sections
5. ✅ **Add new components** - Document in component sections
6. ✅ **Change configuration** - Update configuration sections
7. ✅ **Update infrastructure** - Update infrastructure sections

### Update Workflow

#### Step 1: Make the Change

1. Make your code changes
2. Test the changes
3. Commit to git

#### Step 2: Document the Change

1. **Open `prd/PRD_UPDATES.md`**
2. **Add a new entry** at the top with:
   - Date
   - Change type (Feature Addition, Modification, Removal, etc.)
   - Description of what changed
   - Which components were affected
   - Link to relevant code/commits

3. **Update `prd/PRD_CURRENT_STATE.md`**:
   - Find the relevant section(s)
   - Update with new information
   - Update status indicators (✅/🔄/❌)
   - Update version number if major change
   - Update "Document Last Updated" date

#### Step 3: Review

1. Review the PRD update for accuracy
2. Ensure all sections are consistent
3. Check that status indicators match reality
4. Verify examples and code snippets still work

#### Step 4: Commit

1. Commit PRD updates with your code changes
2. Use descriptive commit messages
3. Link PRD updates to code changes in commit message

---

## Update Template

### prd/PRD_UPDATES.md Entry Template

```markdown
## [YYYY-MM-DD] - [Change Type]

**Change:** [Brief description of what changed]

**Components Affected:**
- [Component 1]
- [Component 2]

**Details:**
[Detailed description of the change, why it was made, and what it affects]

**PRD Updates:**
- [Section in PRD that was updated]
- [What specifically was updated]

**Implementation:**
- File: `path/to/file.py`
- Commit: `abc1234` (optional)

**Migration Notes:** (if needed)
[Any notes about breaking changes or migration requirements]

---
```

### prd/PRD_CURRENT_STATE.md Update Guidelines

**Status Indicators:**
- ✅ Complete - Feature is fully implemented
- 🔄 In Progress - Feature is partially implemented
- ❌ Not Started - Feature is planned but not implemented

**When Updating:**
- Keep status indicators accurate
- Update version number for major changes
- Update "Document Last Updated" date
- Maintain consistent formatting
- Keep examples up to date

---

## Examples

### Example 1: Adding a New Feature

**Change:** Added support for Google Custom Search API as a third search provider.

**Update Process:**

1. **Code Change:** Modify `src/tools/web_search.py` to add Google Custom Search support

2. **prd/PRD_UPDATES.md Entry:**
```markdown
## [2025-01-03] - Feature Addition

**Change:** Added Google Custom Search API as search provider

**Components Affected:**
- `src/tools/web_search.py`
- Configuration (env.example)

**Details:**
Added Google Custom Search API integration as a third option alongside Tavily and Serper. Users can now configure `GOOGLE_CUSTOM_SEARCH_API_KEY` and `GOOGLE_CUSTOM_SEARCH_ENGINE_ID` to use Google search.

**PRD Updates:**
- Section 3.1 Web Search Tool - Added Google Custom Search to supported APIs
- Configuration section - Added new environment variables

**Implementation:**
- File: `src/tools/web_search.py`
- Commit: `def4567`

---
```

3. **prd/PRD_CURRENT_STATE.md Update:**
```markdown
#### 3.1 Web Search Tool (`web_search.py`)
**Status:** ✅ Complete

**Supported APIs:**
- **Tavily** (primary) - AI-optimized search
- **Serper** (alternative) - Google search API
- **Google Custom Search** (alternative) - Google Custom Search API
```

### Example 2: Modifying Existing Feature

**Change:** Changed default search provider from Tavily to Serper.

**Update Process:**

1. **Code Change:** Modify `src/tools/web_search.py` default provider logic

2. **prd/PRD_UPDATES.md Entry:**
```markdown
## [2025-01-04] - Modification

**Change:** Changed default search provider from Tavily to Serper

**Components Affected:**
- `src/tools/web_search.py`
- `src/research/search_executor.py`

**Details:**
Changed the default search provider selection logic. Previously defaulted to Tavily when no provider specified. Now defaults to Serper. Tavily remains available as explicit option.

**PRD Updates:**
- Section 3.1 Web Search Tool - Updated default provider documentation
- Section 1.2 Search Executor - Updated default behavior

**Implementation:**
- File: `src/tools/web_search.py`
- Commit: `ghi7890`

**Migration Notes:**
Existing code that relied on Tavily as default will now use Serper. To continue using Tavily, explicitly specify `provider="tavily"`.

---
```

3. **prd/PRD_CURRENT_STATE.md Update:**
```markdown
**Supported APIs:**
- **Serper** (default) - Google search API
- **Tavily** (alternative) - AI-optimized search
```

### Example 3: Removing a Feature

**Change:** Removed support for deprecated AgentExecution model (legacy component).

**Update Process:**

1. **Code Change:** Remove AgentExecution table and related code

2. **prd/PRD_UPDATES.md Entry:**
```markdown
## [2025-01-05] - Removal

**Change:** Removed deprecated AgentExecution model and table

**Components Affected:**
- `src/database/schema.py`
- `src/database/operations.py`
- `src/agent/research_agent.py`

**Details:**
Removed the legacy AgentExecution database model and related code. The two-phase architecture (ProcessingRun) has fully replaced this approach. AgentExecution was only used by the educational research_agent.py component.

**PRD Updates:**
- Section 4.1 Database Schema - Removed AgentExecution table documentation
- Section 7 Research Agent - Updated to note legacy status

**Implementation:**
- File: `src/database/schema.py`
- Commit: `jkl0123`

**Migration Notes:**
Existing AgentExecution records will be lost. If data needs to be preserved, export before updating. ProcessingRun is the replacement for tracking agent executions.

---
```

3. **prd/PRD_CURRENT_STATE.md Update:**
```markdown
#### 4.1 Database Schema (`schema.py`)
**Status:** ✅ Complete

**Tables:**
[... other tables ...]

~~**`agent_executions`** - Legacy agent execution tracking (REMOVED)~~

[... rest of tables ...]
```

---

## Best Practices

### Do's ✅

- ✅ Update PRDs **alongside** code changes (not after)
- ✅ Be specific about what changed
- ✅ Update status indicators accurately
- ✅ Include examples when functionality changes
- ✅ Document breaking changes
- ✅ Link PRD updates to code commits
- ✅ Review PRD accuracy regularly

### Don'ts ❌

- ❌ Don't forget to update PRDs when making changes
- ❌ Don't let PRDs get out of sync for long periods
- ❌ Don't mark features as complete until they're actually done
- ❌ Don't remove documentation without noting why
- ❌ Don't update PRDs without updating code (or vice versa)

---

## Regular Maintenance

### Monthly Review

At the beginning of each month:

1. Review `prd/PRD_CURRENT_STATE.md` for accuracy
2. Check that all status indicators are correct
3. Verify examples still work
4. Update "Document Last Updated" date if reviewed
5. Check `prd/PRD_UPDATES.md` for completeness

### Quarterly Review

Every 3 months:

1. Major review of entire PRD
2. Check for obsolete features that should be removed
3. Verify architecture sections match reality
4. Update version number if significant changes
5. Archive old update entries if needed

---

## Versioning

### PRD Version Numbers

Update version numbers for:

- **Major changes**: Architecture changes, major feature additions/removals
- **Minor changes**: New features, significant modifications
- **Patch**: Bug fixes, clarifications, minor updates

**Format:** `MAJOR.MINOR.PATCH`

**Example:**
- `1.0.0` - Initial PRD
- `1.1.0` - Added new major component
- `1.1.1` - Fixed documentation error
- `2.0.0` - Architecture overhaul

---

## Questions?

If unsure about whether to update a PRD:

1. **When in doubt, update it** - Better to have current information
2. **Ask the team** - If working with others, confirm approach
3. **Document the question** - Note uncertainty in `prd/PRD_UPDATES.md`

---

**Last Updated:** 2025-01-02  
**Next Review:** 2025-02-02

