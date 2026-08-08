# 🤝 Project Contribution & Git Workflow Guide

Welcome to the **Hybrid AI Text Detector** repository! This document outlines our team's standard Git & GitHub workflow to ensure smooth collaboration, maintain code quality, and prevent merge conflicts.

---

## 🚨 The Golden Rules of Collaboration

1. **NEVER push directly to `main`**. All work must be done on a separate local feature branch.
2. **Always pull latest changes before starting work**. Keep your local repository up to date with `main`.
3. **Always submit a Pull Request (PR)** to merge changes into `main` after review.
4. **Never commit large data files or virtual environments (`venv/`)**. Ensure `.gitignore` is respected.

---

## 🔄 Standard 6-Step Git Workflow

### Step 1: Sync Your Local Main Branch
Before creating a new feature or making any edits, make sure your local copy of `main` is completely up to date with the remote repository:

```bash
git checkout main
git pull origin main
```

---

### Step 2: Create a New Feature Branch
Create a descriptive branch for the specific task you are working on. Name your branch using prefixes:

- `feature/` for new features (e.g., `feature/claude-data-cleaning`)
- `fix/` for bug fixes (e.g., `fix/regex-regex-typo`)
- `docs/` for documentation updates (e.g., `docs/contributing-guide`)

```bash
# Create and switch to your new branch
git checkout -b feature/data-cleaning-claude
```

---

### Step 3: Make Your Changes & Commit Locally
Make small, focused commits as you work rather than one massive commit at the end.

Check what files you modified:
```bash
git status
```

Stage your changes:
```bash
# Stage specific files (recommended)
git add src/notebooks/data_cleaning.ipynb

# Or stage all modified tracked files
git add .
```

Commit your changes with a clear message:
```bash
git commit -m "feat(cleaning): implement regex for LaTeX math expressions"
```

---

### Step 4: Keep Your Branch Updated (Prevent Conflicts)
If your teammates have merged new code into `main` while you were working, pull those updates into your branch to resolve any conflicts locally before opening a PR:

```bash
git checkout main
git pull origin main
git checkout feature/data-cleaning-claude
git merge main
```

---

### Step 5: Push Your Branch to GitHub
Push your local branch to the remote repository on GitHub:

```bash
git push -u origin feature/data-cleaning-claude
```

---

### Step 6: Create a Pull Request (PR)
1. Open the repository on **GitHub**.
2. Click **"Compare & pull request"** next to your recently pushed branch.
3. Fill out the PR Title and Description clearly detailing what was added or fixed.
4. Request at least one teammate to review your PR.
5. Once approved, merge the PR into `main` and delete the feature branch.

---

## 📝 Writing Good Commit & Merge Messages

Clear commit messages help everyone understand the project history without digging through code line-by-line.

### Recommended Format: Conventional Commits
Use the format: `<type>: <short imperative summary>`

Common types:
- `feat`: A new feature or dataset cleaning method
- `fix`: A bug fix (e.g., fixing a regex or typo)
- `docs`: Documentation updates (e.g., README, CONTRIBUTING.md)
- `refactor`: Restructuring code without changing functionality
- `style`: Formatting, spacing, line cleanups

### Examples:
| Status | Commit Message |
| :--- | :--- |
| ❌ **Bad** | `fixed stuff` |
| ❌ **Bad** | `changes` |
| ❌ **Bad** | `update data_cleaning.ipynb` |
| ✅ **Good** | `feat(cleaning): add code fence regex replacement` |
| ✅ **Good** | `fix(regex): correct character class escape in clean_math_texts` |
| ✅ **Good** | `docs: populate CONTRIBUTING.md with team git guidelines` |

---

## 🛡️ Best Practices to Avoid & Resolve Merge Conflicts

### How to Avoid Conflicts:
- **Communicate**: Let teammates know which file or dataset function you are currently working on.
- **Small PRs**: Keep Pull Requests small and single-focused so they can be reviewed and merged quickly.
- **Pull Frequently**: Run `git pull origin main` daily to keep your local branch synced.

### What to Do If You Encounter a Merge Conflict:
1. Open the conflicting files in VS Code.
2. Look for Git conflict markers:
   ```text
   <<<<<<< HEAD (Your changes)
   text = re.sub(r'```.*?```', ' <CODE> ', text)
   =======
   text = clean_code_texts(text)
   >>>>>>> main (Incoming changes)
   ```
3. Use VS Code's inline buttons (**"Accept Current Change"**, **"Accept Incoming Change"**, or **"Accept Both Changes"**), or manually edit the file to keep the correct code.
4. Save the file, stage it (`git add .`), and complete the merge commit (`git commit -m "fix: resolve merge conflict with main"`).

---

## 📌 Summary Checklist Before Pushing

- [ ] Am I on a separate branch (NOT `main`)?
- [ ] Did I test my code locally to verify it works without throwing errors?
- [ ] Are my commit messages clear and descriptive?
- [ ] Are heavy data files (`data/raw/`, `data/processed/`) excluded by `.gitignore`?

Happy coding! 🚀
