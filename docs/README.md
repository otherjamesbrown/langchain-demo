# Documentation Organization

This directory contains all project documentation organized by category. 

**📖 For guidelines on categorizing new docs, see [`DOCUMENTATION_GUIDELINES.md`](DOCUMENTATION_GUIDELINES.md)**

Use this README to navigate and understand where to place new documentation.

## Directory Structure

### 📚 `principles/` - Core Architectural Principles

**Purpose**: Foundational concepts and principles that guide all development decisions.

**Contents**:
- Architectural principles and conventions
- System architecture overview
- Core component documentation

**When to use**: Document core architectural decisions, principles, and system design.

**Examples**:
- `ARCHITECTURAL_PRINCIPLES.md` - Core development principles
- `ARCHITECTURE.md` - System architecture overview
- `LLM_COMPONENTS.md` - LLM component architecture

---

### ✅ `implemented/` - Implemented Features

**Purpose**: Documentation of features that have been completed and are in use.

**Contents**:
- Feature implementation guides
- How completed features work
- Integration documentation

**When to use**: Document a feature after it's been implemented and is working in production.

**Examples**:
- `DATABASE_CONSOLIDATION.md` - Database-first approach (implemented)
- `STRUCTURED_OUTPUT_REFACTORING.md` - Refactoring that was completed
- `LLM_LOGGING_GUIDE.md` - Logging system (implemented)

---

### 📋 `plans/` - Plans and Proposals

**Purpose**: Documentation of features or changes that are planned but not yet implemented.

**Contents**:
- Feature proposals
- Implementation plans
- Future enhancements
- Roadmaps

**When to use**: Document something that should be done but hasn't been implemented yet.

**Examples**:
- `TESTING_FRAMEWORK_PLAN.md` - Planned testing framework
- `FILE_ORGANIZATION_PLAN.md` - Proposed file organization
- `UI_OPTIONS.md` - Future UI enhancements

**Note**: Once a plan is implemented, move the doc to `implemented/` or merge into appropriate implemented doc.

---

### 🔧 `infrastructure/` - Infrastructure and Setup

**Purpose**: Documentation for setting up and accessing the development/production environment.

**Contents**:
- Server setup guides
- SSH access instructions
- Authentication setup
- Deployment procedures

**When to use**: Document how to set up, access, or maintain the infrastructure.

**Examples**:
- `SSH_ACCESS_GUIDE.md` - How to SSH to server
- `SERVER_SETUP.md` - Server setup instructions
- `STREAMLIT_WORKFLOW.md` - Deployment workflow

---

### 🐛 `troubleshooting/` - Troubleshooting and Problem Solving

**Purpose**: Documentation of known issues, solutions, and debugging guides.

**Contents**:
- Issue resolution guides
- Debugging procedures
- Known limitations
- Workarounds

**When to use**: Document a problem that was encountered and how it was solved (or why it can't be solved).

**Examples**:
- `REACT_ITERATION_DIFFERENCE.md` - Why local/remote models behave differently
- `LLAMA_TRUNCATION_ISSUE.md` - Truncation problem and resolution
- `GEMINI_TEST_BITMOVIN_ISSUE.md` - Specific issue encountered

---

### 📖 `reference/` - Reference Documentation

**Purpose**: Technical reference, guides, and how-to documentation.

**Contents**:
- How-to guides
- Technical references
- API documentation
- Usage examples

**When to use**: Create step-by-step guides or technical references that don't fit other categories.

**Examples**:
- `DEPLOYMENT_VERIFICATION.md` - How to verify deployments
- `STRUCTURED_OUTPUT_STRATEGIES.md` - Technical reference for strategies
- `FILE_ORGANIZATION_SUMMARY.md` - Reference for file organization

---

## Quick Reference

| Category | When to Use | Examples |
|---------|-------------|----------|
| **principles/** | Core concepts, architecture, design decisions | `ARCHITECTURAL_PRINCIPLES.md` |
| **implemented/** | Completed features, how they work | `DATABASE_CONSOLIDATION.md` |
| **plans/** | Future work, proposals, roadmaps | `TESTING_FRAMEWORK_PLAN.md` |
| **infrastructure/** | Setup, access, deployment | `SSH_ACCESS_GUIDE.md` |
| **troubleshooting/** | Issues, solutions, limitations | `REACT_ITERATION_DIFFERENCE.md` |
| **reference/** | How-to guides, technical refs | `DEPLOYMENT_VERIFICATION.md` |

---

## Documentation Standards

### File Naming
- Use `SCREAMING_SNAKE_CASE.md` for file names
- Be descriptive and specific
- Include date suffix if multiple versions (e.g., `ARCHITECTURE_v2.md`)

### Content Requirements
- **principles/**: Should explain "why" not just "what"
- **implemented/**: Should include code examples and usage
- **plans/**: Should include goals, timeline, and success criteria
- **infrastructure/**: Should be step-by-step and copy-paste ready
- **troubleshooting/**: Should include problem, cause, and solution
- **reference/**: Should be scannable with clear sections

### Status Tracking
- Plans should include implementation status
- Implemented docs should reference related code
- Troubleshooting docs should indicate if issue is resolved

---

## Moving Documents

When a plan becomes implemented:
1. Review the plan document
2. Either:
   - Move to `implemented/` if it's a standalone feature
   - Merge into existing implemented doc if it's an enhancement
   - Update plan doc with completion status and move to implemented

When documenting a solution:
1. If issue is fully resolved → `troubleshooting/`
2. If it's a permanent limitation → `troubleshooting/` with clear "LIMITATION" marker
3. If it's a workaround → `troubleshooting/` with "WORKAROUND" marker

---

## Documentation Guidelines

For detailed guidelines on:
- How to categorize documents
- File naming conventions
- Content requirements by category
- Moving documents between categories
- Cross-reference patterns

See: [`DOCUMENTATION_GUIDELINES.md`](DOCUMENTATION_GUIDELINES.md)

---

**Last Updated**: 2025-01-XX  
**Maintained By**: Project maintainers

