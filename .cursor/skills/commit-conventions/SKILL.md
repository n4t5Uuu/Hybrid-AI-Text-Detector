---
name: commit-conventions
description: Generate properly formatted commit messages following conventional commits with team standards. Use when the user asks for help writing commit messages, creating commits, or reviewing staged changes.
disable-model-invocation: true
---

# Commit Message Conventions

## Format Structure

```
<type>(<scope>): <short imperative summary>

<optional longer description>
```

## Commit Types

| Type | When to Use | Example |
|------|-------------|---------|
| `feat` | New feature or dataset cleaning method | `feat(cleaning): add code fence regex replacement` |
| `fix` | Bug fix (regex, typo, logic error) | `fix(regex): correct character class escape in clean_math_texts` |
| `docs` | Documentation updates (README, comments, guides) | `docs: populate CONTRIBUTING.md with team git guidelines` |
| `refactor` | Code restructuring without changing functionality | `refactor(pipeline): extract cleaning functions to utils module` |
| `style` | Formatting, spacing, line cleanups | `style: fix indentation in data_cleaning.ipynb` |
| `test` | Adding or updating tests | `test(density): add unit tests for placeholder_density` |
| `chore` | Build tasks, dependency updates, config | `chore: update requirements.txt with langdetect` |
| `perf` | Performance improvements | `perf(cleaning): optimize regex patterns for faster processing` |

## Scope Guidelines

Use the **component or feature** being modified:

**Common scopes for this project:**
- `cleaning` - text cleaning functions
- `pipeline` - data processing workflow
- `dataset` - dataset-specific functions (Claude, MGTBench, BAWE)
- `notebook` - Jupyter notebook changes
- `utils` - utility functions
- `docs` - documentation files
- `regex` - regex pattern fixes
- `config` - configuration files

**Examples:**
```
feat(cleaning): implement regex for LaTeX math expressions
fix(dataset): handle malformed Claude conversation format
docs(readme): add setup instructions for virtual environment
refactor(utils): move cleaning functions to separate module
```

## Message Writing Rules

### Subject Line (First Line)

1. **Use imperative mood** (command form, not past tense)
   - ✅ Good: `add`, `fix`, `update`, `remove`
   - ❌ Bad: `added`, `fixed`, `updated`, `removed`

2. **Keep it short** (50-72 characters max)
   - Focus on WHAT changed, not HOW or WHY

3. **Don't end with a period**

4. **Be specific but concise**
   - ✅ Good: `add placeholder_density_windowed for local density checks`
   - ❌ Bad: `update functions`
   - ❌ Bad: `changes`

### Body (Optional)

- Leave one blank line after subject
- Explain WHY the change was made if not obvious
- Wrap at 72 characters
- Use bullet points for multiple items

## Examples

### Feature Addition
```
feat(cleaning): add merge_continuous_equations function

Consolidates adjacent placeholders separated by non-prose 
fragments into single tags to reduce noise in cleaned text.
```

### Bug Fix
```
fix(regex): escape special characters in math pattern

Parentheses in O(n) notation were being parsed as capture 
groups instead of literal characters.
```

### Documentation
```
docs: create TEXT_CLEANING_API.md reference guide
```

### Refactoring
```
refactor(notebook): extract cleaning functions to utils.text_cleaning

- Moved all 19 cleaning functions to src/utils/text_cleaning.py
- Updated notebook to import from module
- Improved code reusability and maintainability
```

### Style Fix
```
style(cleaning): fix inconsistent indentation
```

## Quick Decision Tree

**Added new functionality?** → `feat`

**Fixed a bug/error?** → `fix`

**Updated docs only?** → `docs`

**Restructured existing code?** → `refactor`

**Changed formatting only?** → `style`

**Added/updated tests?** → `test`

**Updated dependencies/configs?** → `chore`

## Common Mistakes to Avoid

❌ **Vague messages**
```
bad: update data_cleaning.ipynb
bad: fixed stuff
bad: changes
```

✅ **Specific messages**
```
good: feat(cleaning): add code fence regex replacement
good: fix(regex): correct character class escape in clean_math_texts
good: refactor(notebook): extract functions to utils module
```

❌ **Past tense**
```
bad: feat(cleaning): added new function
```

✅ **Imperative mood**
```
good: feat(cleaning): add new function
```

❌ **Too long or rambling**
```
bad: feat: so I added this new function that does cleaning and also I updated the notebook to use it and fixed some bugs
```

✅ **Focused and concise**
```
good: feat(cleaning): add placeholder density calculation
good: fix(notebook): correct import path for utils module
```

## Using in Git Commands

```bash
# Single-line commit
git commit -m "feat(cleaning): add merge_continuous_equations function"

# Multi-line commit with body
git commit -m "feat(cleaning): add merge_continuous_equations function" -m "Consolidates adjacent placeholders separated by non-prose fragments."

# Using heredoc for complex messages
git commit -m "$(cat <<'EOF'
refactor(notebook): extract cleaning functions to utils module

- Moved all 19 cleaning functions to src/utils/text_cleaning.py
- Updated notebook to import from module
- Improved code reusability and maintainability
EOF
)"
```

## Before Committing

1. Review staged changes: `git diff --staged`
2. Ensure message accurately reflects ALL changes
3. If commit contains multiple unrelated changes, split into separate commits
4. Check that type and scope match the changes
