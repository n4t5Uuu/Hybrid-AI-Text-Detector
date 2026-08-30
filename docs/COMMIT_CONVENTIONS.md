# Commit Message Conventions

Quick reference for writing commit messages following conventional commits format.

## Format

```
<type>(<scope>): <short description>

[optional body]
```

## Types

| Type | Use When | Example |
|------|----------|---------|
| `feat` | New feature/function | `feat(cleaning): add code fence regex replacement` |
| `fix` | Bug fix | `fix(regex): correct character class escape in clean_math_texts` |
| `docs` | Documentation only | `docs: update README with setup instructions` |
| `refactor` | Restructure code | `refactor(notebook): extract functions to utils module` |
| `style` | Formatting/spacing | `style: fix indentation in notebook` |
| `test` | Add/update tests | `test(density): add unit tests` |
| `chore` | Dependencies/config | `chore: update requirements.txt` |
| `perf` | Performance | `perf(cleaning): optimize regex patterns` |

## Scopes (for this project)

- `cleaning` - text cleaning functions
- `pipeline` - data processing workflow
- `dataset` - Claude/MGTBench/BAWE functions
- `notebook` - Jupyter notebooks
- `utils` - utility modules
- `docs` - documentation
- `regex` - regex patterns
- `config` - configuration

## Rules

### Subject (first line)
1. **Use imperative** - "add" not "added"
2. **Max 72 chars**
3. **No period at end**
4. **Be specific**

### Body (optional)
- Leave blank line after subject
- Explain WHY if needed
- Use bullet points for lists

## Examples

### Good ✅
```
feat(cleaning): add merge_continuous_equations function

fix(regex): escape special characters in math pattern

docs: create TEXT_CLEANING_API.md reference

refactor(notebook): extract cleaning functions to utils module
- Moved 19 functions to src/utils/text_cleaning.py
- Updated imports in notebook
```

### Bad ❌
```
update data_cleaning.ipynb         ❌ Too vague
added new function                 ❌ Past tense
feat: changes and stuff            ❌ Not specific
```

## Quick Decision Tree

- Added new functionality? → `feat`
- Fixed bug/error? → `fix`
- Updated docs only? → `docs`
- Restructured code? → `refactor`
- Changed formatting? → `style`
- Added/updated tests? → `test`
- Updated dependencies? → `chore`

## Git Commands

```bash
# Single-line
git commit -m "feat(cleaning): add new function"

# Multi-line
git commit -m "feat(cleaning): add new function" -m "Additional explanation here"
```

## Before Committing

1. `git diff --staged` - review what you're committing
2. Ensure message matches ALL changes
3. Split unrelated changes into separate commits
