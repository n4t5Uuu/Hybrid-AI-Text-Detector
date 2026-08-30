---
name: pr-review
description: Create pull request descriptions using the team's PR template. Use when the user asks to create a PR, open a pull request, or review changes for PR submission.
disable-model-invocation: true
---

# Pull Request Review & Description

## Before Creating PR

**NEVER push directly to main!** Always work on a feature branch and create a PR.

1. Review all commits: `git log origin/main..HEAD --oneline`
2. Check diff summary: `git diff origin/main...HEAD --stat`
3. Verify all changes are intentional
4. Ensure tests pass (if applicable)
5. Push your branch: `git push -u origin your-branch-name`

## PR Description Format

Use the team's PR template from `.github/pull_request_template.md`:

```markdown
## Description

- [Brief overview of what this PR does]
- [Why this change is needed]
- Fixes #[issue number] (if applicable)

## What did you do?

### [Feature/Change Category 1]

- [Specific change or addition]
- [Another specific change]
- [Include code snippets or examples if helpful]

### [Feature/Change Category 2]

- [More specific changes]
- [Impact or benefit of the change]

## What to watch out for?

- [Any new dependencies added]
- [Breaking changes or migration notes]
- [Performance considerations]
- [Known limitations or edge cases]
```

## Writing Natural PR Descriptions

**DO:**
- Be direct and specific
- Use active voice
- Focus on what changed and why
- Include concrete examples
- Mention potential issues upfront

**DON'T:**
- Use corporate-speak or buzzwords
- Say "I'm pleased to present" or similar
- Overuse adjectives like "robust", "cutting-edge", "comprehensive"
- Write long introductions
- Be overly formal

## Good vs Bad Examples

### ❌ Bad (AI-sounding)
```markdown
## Description

I'm excited to present this comprehensive refactoring effort that modernizes 
our codebase architecture. This cutting-edge implementation leverages best 
practices to deliver a robust, scalable solution that significantly enhances 
code quality and maintainability.
```

### ✅ Good (Natural)
```markdown
## Description

Moved all cleaning functions from the notebook to a separate Python module. 
Makes the code reusable and easier to maintain. Other notebooks can now 
import these functions instead of copy-pasting.
```

### ❌ Bad (Vague)
```markdown
## What did you do?

### Improvements

- Updated the code
- Fixed some issues
- Made things better
```

### ✅ Good (Specific)
```markdown
## What did you do?

### Code Organization

- Extracted 19 cleaning functions to `src/utils/text_cleaning.py`
- Created `__init__.py` to make utils a proper package
- Updated notebook to import from module (removed 798 lines)

### Documentation

- Added `TEXT_CLEANING_API.md` with function reference
- Created `COMMIT_CONVENTIONS.md` for team standards
- Updated README with links to new docs
```

## Handling Different PR Types

### Feature Addition
Focus on:
- What the feature does
- Why it's needed
- How to use it
- Any limitations

### Bug Fix
Focus on:
- What was broken
- How it manifests
- What caused it
- How the fix works

### Refactoring
Focus on:
- What structure changed
- Why the change improves things
- What stays the same (behavior)
- Migration steps if needed

### Documentation
Focus on:
- What's now documented
- Who it helps
- Where to find it

## Quick Checklist

Before submitting PR:
- [ ] Title follows format: `type(scope): brief description`
- [ ] Description explains WHAT and WHY
- [ ] All sections of template are filled
- [ ] Screenshots/examples included if UI changes
- [ ] "What to watch out for" mentions new dependencies
- [ ] Tone is conversational, not corporate
- [ ] No AI buzzwords or phrases

## Workflow

When the user asks to create a PR:

1. **Review the changes** (show commits and diff summary)
2. **Generate the PR description** following the template
3. **Provide the description as text** for the user to copy-paste
4. **Remind user to push their branch** so they can create the PR

**Important:** Tell the user they need to push their branch first:
```bash
git push -u origin your-branch-name
```

Then they can create the PR on GitHub and paste the description you generated.

## Example Output Format

```markdown
# PR Title
refactor(utils): extract cleaning functions to module

# PR Description (copy this)
## Description
...
```

## Example PR Description Template

```markdown
## Description

Moved all text cleaning functions from notebook to a reusable Python module.
The notebook was getting too long (1000+ lines) and functions couldn't be 
reused by other notebooks.

## What did you do?

### Code Refactoring

- Created `src/utils/text_cleaning.py` with all 19 cleaning functions
- Set up proper imports (re, ast, pandas, langdetect, etc.)
- Added `__init__.py` to make utils a package
- Updated notebook to import functions instead of defining them inline

### Documentation

- Added `TEXT_CLEANING_API.md` - quick reference for all functions
- Created `COMMIT_CONVENTIONS.md` - commit message standards
- Added Cursor skill for commit help
- Updated README with dev guidelines section

### Testing

- Verified notebook cell structure (reduced from 12 to 9 cells)
- Checked imports work correctly
- Confirmed functions maintain same behavior

## What to watch out for?

- New dependency: `langdetect` (already in requirements.txt)
- Notebook now requires `src/` in Python path
- If running notebooks outside project root, imports may fail
```

## Natural Language Patterns

Use these natural patterns instead of formal language:

| Instead of | Use |
|------------|-----|
| "This PR implements..." | "Added...", "Fixed...", "Moved..." |
| "I am pleased to present..." | Just describe what changed |
| "Comprehensive refactoring..." | "Refactored X to make it..." |
| "Leverages cutting-edge..." | "Uses...", "Implements..." |
| "Significantly enhances..." | "Makes it easier to...", "Improves..." |
| "State-of-the-art solution..." | Just explain what it does |
| "Robust architecture..." | "Organized code so that..." |

## Final Reminder

**Keep it real.** Write like you're explaining the changes to a teammate over coffee, not presenting to a board of directors.
