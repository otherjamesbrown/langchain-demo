# File Organization Plan

**Status**: ✅ COMPLETED  
**Implementation**: See `docs/implemented/FILE_ORGANIZATION.md`  
**Date Completed**: 2025-01-XX

---

## Original Plan (Historical Reference)

### Current Issues

Too many overlapping status/architecture documents in root and docs/ directories, creating confusion about what's current vs. obsolete.

## Proposed Structure

### Root Directory - Current & Active
**KEEP THESE (single source of truth):**
- `README.md` - Main project entry point
- `prd/PRD.md` - Product requirements (source of truth)
- `PROJECT_STRUCTURE.md` - Codebase layout
- `ARCHITECTURE_SUMMARY.md` - Current architecture status
- `DEVELOPMENT_STATUS.md` - Implementation progress tracker
- `INFRASTRUCTURE_STATUS.md` - Server setup status
- `CONTRIBUTING.md` - Contributor guidelines

### Root Directory - Obsolete/Temporary
**MOVE TO temp/ OR ARCHIVE:**
- `PROJECT_STATUS.md` - Redundant with DEVELOPMENT_STATUS.md + INFRASTRUCTURE_STATUS.md
- `SESSION_INFO.md` - Should be in temp/ (temporary connection info)
- `ARCHITECTURE_SUMMARY.md` - Check if redundant

### docs/ Directory - Keep Active Guides
**KEEP THESE (official guides):**
- `docs/ARCHITECTURE.md` - Architecture reference (comprehensive)
- `docs/TWO_PHASE_ARCHITECTURE.md` - Two-phase architecture guide (since it's implemented)
- `docs/SERVER_SETUP.md` - Linode setup guide
- `docs/SERVER_SETUP_GCP.md` - GCP setup guide
- `docs/UI_OPTIONS.md` - UI options guide
- `docs/LLM_LOGGING_GUIDE.md` - Logging guide
- `docs/LLM_COMPONENTS.md` - Components guide

### docs/ Directory - Obsolete/Temporary  
**MOVE TO temp/:**
- `docs/ARCHITECTURE_PROPOSAL.md` - Already moved to temp/
- `docs/GCP_GPU_OPTIONS.md` - Decision already made, should be archived
- `docs/UI_MONITORING.md` - Check if this is implemented or planned
- `docs/TWO_PHASE_ARCHITECTURE.md` - Keep since implemented, but verify it's current

## Temporary Directory Rules

Files in `temp/` are:
- Gitignored
- Disposable
- Not referenced in main docs
- For scratch work and proposals

## Consolidation Plan

### Status Documents
**Goal:** Single status tracker, not multiple overlapping docs

**Decisions:**
1. Keep `DEVELOPMENT_STATUS.md` as main dev tracker
2. Keep `INFRASTRUCTURE_STATUS.md` as main infra tracker  
3. Archive/remove `PROJECT_STATUS.md` (redundant)
4. Move `SESSION_INFO.md` to temp/ (temporary)

### Architecture Documents
**Goal:** Clear separation of current vs. proposals

**Decisions:**
1. `docs/ARCHITECTURE.md` - Main comprehensive reference
2. `docs/TWO_PHASE_ARCHITECTURE.md` - Implementation guide (keep if current)
3. `ARCHITECTURE_SUMMARY.md` - Status summary in root
4. `temp/ARCHITECTURE_PROPOSAL.md` - Historical proposal

## Questions to Resolve

1. Is `TWO_PHASE_ARCHITECTURE.md` current and accurate?
2. Should `UI_MONITORING.md` be kept or moved to temp?
3. Is `GCP_GPU_OPTIONS.md` still relevant or just historical?
4. Can `PROJECT_STATUS.md` be completely replaced by other docs?

## Next Steps

1. Review each questionable file
2. Move obsolete docs to temp/
3. Update references/cross-links
4. Update .cursorrules with organization rules

---

## ✅ Implementation Status

**All steps completed!** See `docs/implemented/FILE_ORGANIZATION.md` for full implementation summary.

**Completed Actions**:
- ✅ Root directory cleaned (obsolete files moved to temp/)
- ✅ docs/ directory organized into 6 categories
- ✅ 31 documentation files categorized
- ✅ Documentation guidelines created
- ✅ .cursorrules updated with categorization rules
- ✅ All cross-references updated

---

**Last Updated**: 2025-01-XX  
**Status**: ✅ COMPLETE

