# Prompt Files

## Consolidated Prompt File

**`research-agent-prompt.md`** - This is the main prompt file used by the research agent. All prompts have been consolidated into this single file for easier editing.

### File Structure

The file is organized into sections with clear markers:

1. **`# RESEARCH INSTRUCTIONS`** - Main instructions for the agent
   - Extracted by `_load_instructions()` 
   - Summarized by `_summarise_markdown()` (first 28 lines)
   - Used in the system prompt

2. **`# CLASSIFICATION REFERENCE`** - GTM classification options
   - Extracted by `_build_classification_reference()`
   - Parsed automatically from `## Section Name` headers
   - Used in the system prompt

3. **`# DETAILED CLASSIFICATION DEFINITIONS (Optional)`** - Reference only
   - NOT automatically used by the agent
   - Kept for documentation/reference
   - Can be safely removed

### How to Edit

1. **To simplify research instructions**: Edit the content under `# RESEARCH INSTRUCTIONS`
   - Keep it concise (under 30 lines recommended)
   - Use bullet points or numbered lists
   - The code takes the first 28 lines

2. **To simplify classifications**: Edit the `## Classification Name` sections under `# CLASSIFICATION REFERENCE`
   - Remove entire sections you don't need
   - Reduce options within each section (format: `option1 | option2 | option3`)
   - The code automatically parses these

3. **To remove GTM classifications entirely**: 
   - Delete the entire `# CLASSIFICATION REFERENCE` section
   - The code will fall back to hardcoded defaults (for backward compatibility)
   - Or update `src/tools/models.py` to remove GTM fields from CompanyInfo

### Legacy Files (No Longer Used)

These files are kept for reference but are not loaded by default:

- **`gtm.md`** - Original GTM instructions (content moved to `research-agent-prompt.md`)
- **`company-profiling-guide.md`** - Original classification guide (content moved to `research-agent-prompt.md`)
- **`examples/instructions/research_instructions.md`** - Simple research template (not used)

You can delete these files if you want, but they're kept for reference.

### Code Changes

The code in `src/agent/research_agent.py` has been updated to:

1. Load from `prompts/research-agent-prompt.md` by default
2. Extract sections based on markdown headers (`# SECTION NAME`)
3. Parse classification options from `## Header` sections automatically
4. Fall back gracefully if sections are not found

All changes are backward-compatible - if the consolidated file doesn't exist or sections are missing, it will use hardcoded defaults.

