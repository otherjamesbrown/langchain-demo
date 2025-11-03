# Documentation Guidelines

This document explains how to categorize and organize documentation files in this project.

## Quick Decision Tree

When creating a new `.md` file in `docs/`, ask:

1. **Is it about infrastructure/setup?** → `docs/infrastructure/`
   - Server setup, SSH, deployment, access guides

2. **Is it a completed feature?** → `docs/implemented/`
   - Feature documentation, how things work, integration guides

3. **Is it a plan or proposal?** → `docs/plans/`
   - Future work, roadmaps, feature proposals

4. **Is it troubleshooting?** → `docs/troubleshooting/`
   - Problem/solution, known issues, debugging guides

5. **Is it a core principle?** → `docs/principles/`
   - Architectural principles, design decisions, system design

6. **Is it a reference guide?** → `docs/reference/`
   - How-to guides, technical references, usage examples

**Never create files in `docs/` root** - always use appropriate subdirectory.

## Category Definitions

### 📚 `principles/` - Core Architectural Principles

**Purpose**: Foundational concepts that guide all development.

**Contains**:
- Architectural principles (e.g., "database as source of truth")
- System architecture overview
- Core component design
- Design decision rationale

**Examples**:
- `ARCHITECTURAL_PRINCIPLES.md` - Core development principles
- `ARCHITECTURE.md` - System architecture
- `LLM_COMPONENTS.md` - Component architecture

**When to create here**:
- Documenting a core architectural decision
- Explaining "why" we do things a certain way
- System design documentation

---

### ✅ `implemented/` - Implemented Features

**Purpose**: Documentation of completed, working features.

**Contains**:
- Feature implementation guides
- How completed features work
- Integration documentation
- Refactoring documentation (after completion)

**Examples**:
- `DATABASE_CONSOLIDATION.md` - Database-first approach (implemented)
- `STRUCTURED_OUTPUT_REFACTORING.md` - Completed refactoring
- `LLM_LOGGING_GUIDE.md` - Working logging system

**When to create here**:
- Feature is **completed and working**
- Code is merged and tested
- Feature is in use

**Migration**: When a plan is implemented, move from `plans/` to `implemented/`

---

### 📋 `plans/` - Plans and Proposals

**Purpose**: Documentation of work that is planned but not yet done.

**Contains**:
- Feature proposals
- Implementation plans
- Future enhancements
- Roadmaps
- Planned refactorings

**Examples**:
- `TESTING_FRAMEWORK_PLAN.md` - Planned testing framework
- `FILE_ORGANIZATION_PLAN.md` - Proposed organization
- `UI_OPTIONS.md` - Future UI enhancements

**When to create here**:
- Feature is **not yet implemented**
- Work is proposed or in planning
- Future roadmap item

**Migration**: Once implemented, move to `implemented/` or merge into existing implemented docs

---

### 🔧 `infrastructure/` - Infrastructure and Setup

**Purpose**: How to set up, access, and maintain the environment.

**Contains**:
- Server setup guides
- SSH access instructions
- Authentication setup
- Deployment procedures
- Firewall configuration
- Access guides

**Examples**:
- `SSH_ACCESS_GUIDE.md` - How to SSH to server
- `SERVER_SETUP.md` - Server setup instructions
- `STREAMLIT_WORKFLOW.md` - Deployment workflow
- `GITHUB_AUTH.md` - GitHub authentication

**When to create here**:
- Step-by-step setup instructions
- Access/authentication guides
- Deployment procedures
- Infrastructure configuration

---

### 🐛 `troubleshooting/` - Troubleshooting and Problem Solving

**Purpose**: Known issues, solutions, and debugging guides.

**Contains**:
- Issue resolution guides
- Debugging procedures
- Known limitations
- Workarounds
- Problem analysis

**Examples**:
- `REACT_ITERATION_DIFFERENCE.md` - Why models behave differently
- `LLAMA_TRUNCATION_ISSUE.md` - Truncation problem and resolution
- `GEMINI_TEST_BITMOVIN_ISSUE.md` - Specific issue encountered

**When to create here**:
- Documenting a problem that was encountered
- Explaining why something doesn't work
- Providing workarounds or solutions
- Debugging guides

**Status markers**: Use clear markers:
- `[RESOLVED]` - Issue is fully resolved
- `[LIMITATION]` - Known limitation that cannot be fixed
- `[WORKAROUND]` - Workaround available but not ideal solution

---

### 📖 `reference/` - Reference Documentation

**Purpose**: How-to guides, technical references, and usage examples.

**Contains**:
- Step-by-step how-to guides
- Technical references
- Usage examples
- Verification procedures
- Quick reference cards

**Examples**:
- `DEPLOYMENT_VERIFICATION.md` - How to verify deployments
- `STRUCTURED_OUTPUT_STRATEGIES.md` - Technical reference
- `FILE_ORGANIZATION_SUMMARY.md` - Quick reference

**When to create here**:
- Step-by-step procedure guide
- Technical reference material
- Usage examples
- Quick reference guide
- Doesn't fit other categories

---

## File Naming Convention

- Use `SCREAMING_SNAKE_CASE.md`
- Be descriptive and specific
- Include version suffix if multiple versions exist (e.g., `ARCHITECTURE_v2.md`)

**Examples**:
- ✅ `DEPLOYMENT_VERIFICATION.md`
- ✅ `DATABASE_CONSOLIDATION.md`
- ❌ `deployment-verification.md` (wrong case)
- ❌ `deployment.md` (too vague)

---

## Content Requirements by Category

### `principles/`
- Explain **why** not just **what**
- Include rationale for decisions
- Reference related code and docs
- Should be relatively stable (principles don't change often)

### `implemented/`
- Include code examples
- Show how to use the feature
- Document integration points
- Include "Implementation Status: ✅ COMPLETE" marker

### `plans/`
- Include goals and objectives
- Define success criteria
- Include timeline or priority (if available)
- Mark implementation status: `[PLANNED]`, `[IN PROGRESS]`, `[DEFERRED]`

### `infrastructure/`
- Step-by-step, copy-paste ready
- Include prerequisites
- Show expected output
- Include troubleshooting section

### `troubleshooting/`
- Clearly state the problem
- Explain root cause
- Provide solution or workaround
- Mark status: `[RESOLVED]`, `[LIMITATION]`, `[WORKAROUND]`

### `reference/`
- Scannable with clear sections
- Include examples
- Be concise but complete
- Include cross-references

---

## Moving Documents

### When a Plan Becomes Implemented

1. **Review the plan document**
   - Check if all goals are met
   - Verify implementation is complete

2. **Decide on action**:
   - **Standalone feature** → Move entire doc to `implemented/`
   - **Enhancement** → Merge into existing implemented doc
   - **Partial completion** → Update plan doc status, create implemented doc

3. **Update references**:
   - Fix any links pointing to the moved doc
   - Update cross-references in other docs

### When Documenting a Solution

1. **Issue fully resolved** → `troubleshooting/` with `[RESOLVED]` marker
2. **Permanent limitation** → `troubleshooting/` with `[LIMITATION]` marker
3. **Workaround exists** → `troubleshooting/` with `[WORKAROUND]` marker

---

## Cross-References

### Internal References

Always use relative paths from the document location:

```markdown
# From docs/principles/ARCHITECTURE.md
See `../implemented/DATABASE_CONSOLIDATION.md` for database implementation.

# From docs/implemented/STRUCTURED_OUTPUT_REFACTORING.md
See `../reference/STRUCTURED_OUTPUT_STRATEGIES.md` for strategy details.
```

### External References

From code or root-level files, use full paths:

```python
# In code comments
# See docs/principles/ARCHITECTURAL_PRINCIPLES.md for core principles
```

---

## Documentation Status Tracking

### Status Markers

Use these markers at the top of documents:

- `**Status**: ✅ IMPLEMENTED` - For implemented features
- `**Status**: 📋 PLANNED` - For plans/proposals
- `**Status**: 🐛 [RESOLVED]` - For resolved issues
- `**Status**: ⚠️ [LIMITATION]` - For known limitations
- `**Status**: 🔧 [WORKAROUND]` - For workarounds

### Last Updated

Always include:
- `**Last Updated**: YYYY-MM-DD`
- `**Maintained By**: Owner name (if applicable)`

---

## Common Patterns

### Creating a New Doc

1. Determine category using decision tree above
2. Create file in appropriate subdirectory
3. Include status marker
4. Add to `docs/README.md` if it's a major doc
5. Update cross-references in related docs

### Updating Existing Docs

1. Check if category is still correct
2. Update "Last Updated" date
3. Fix any broken cross-references
4. Update status markers if applicable

### Archiving Old Docs

If a doc becomes obsolete:
1. **Don't delete** - keep for history
2. Mark as `[OBSOLETE]` or `[ARCHIVED]`
3. Move to `docs/archive/` if creating many obsolete docs
4. Update cross-references to point to replacement doc

---

## Examples

### ✅ Good: Correctly Categorized

```
docs/
├── principles/
│   └── ARCHITECTURAL_PRINCIPLES.md  ✅ Core principle
├── implemented/
│   └── DATABASE_CONSOLIDATION.md    ✅ Completed feature
├── plans/
│   └── TESTING_FRAMEWORK_PLAN.md    ✅ Future work
├── infrastructure/
│   └── SSH_ACCESS_GUIDE.md          ✅ Setup guide
└── troubleshooting/
    └── REACT_ITERATION_DIFFERENCE.md ✅ Problem analysis
```

### ❌ Bad: Misplaced Docs

```
docs/
├── ARCHITECTURAL_PRINCIPLES.md      ❌ Should be in principles/
├── DATABASE_SETUP.md                ❌ Should be in infrastructure/
└── NEW_FEATURE.md                    ❌ Should be in plans/ or implemented/
```

---

## Related Documentation

- `docs/README.md` - Directory structure overview
- `.cursorrules` - Code and documentation standards

---

**Last Updated**: 2025-01-XX  
**Maintained By**: Project maintainers

