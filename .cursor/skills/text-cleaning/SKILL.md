---
name: text-cleaning
description: Extend and verify academic text cleaning for math, code, citations, and related noise using src/utils/cleaning/. Use when leftover equations, trig, physics formulas, code fragments, or placeholder chains appear in cleaned CSVs, or when the user asks to clean math, mop up noise, or re-run the Claude clean.
disable-model-invocation: true
---

# Text Cleaning

Replace non-prose (math, code, citations, URLs, complexity, music) with placeholder tags. Do not delete academic prose around it.

**Canonical code:** `src/utils/cleaning/` (`cleaning_methods.py`, `placeholder_density.py`, `dataset_cleaning.py`)  
**Team reference:** `docs/TEXT_CLEANING_API.md`  
**Pattern catalog:** [patterns.md](patterns.md)

On leftover-noise or filter work, **read [patterns.md](patterns.md) before editing**.

Always call `clean_pipeline()`. Do not rearrange its order. Do not put new cleaning functions in the notebook.

## Placeholders

| Tag | Replaces |
|-----|----------|
| `[[EQUATION]]` | Math, LaTeX, Greek, trig, physics formulas, algebraic fragments |
| `[[CODE]]` | Fenced/inline code, pseudocode, assignments, return expressions |
| `[[CITATION]]` | `(Smith, 2020)`, `[1]`, `Smith et al. (2020)` |
| `[[COMPLEXITY]]` | `O(n)`, `Θ(n)`, `Ω(n²)` |
| `[[URL]]` | `https://...`, `www....` |
| `[[MUSIC]]` | Chord progressions like `C-G-D-A` |

Same-tag chains collapse to one tag. Exception: `[[CODE]] [[EQUATION]] [[CODE]]` (debugging sandwich) → `[[CODE]]`. Do not merge a lone `[[CODE]]` beside a lone `[[EQUATION]]`.

## Pipeline order (do not reorder)

```
URL → pseudocode/diagrams → markdown code → code assignments → music → complexity
→ strip references → citations → list numbering
→ bare expressions → math texts → residual math
→ merge EQUATION → merge CODE
→ mop-up leftovers → code assignments again
→ merge EQUATION → merge CODE
```

Filter **before** cleaning: `is_academic_content()`, then `contains_foreign_language()`.  
Drop after cleaning if `placeholder_density >= 0.4` or `placeholder_density_windowed()` is true.

Creative filter phrases are matched on the **prompt only** (not the response), so academic answers that mention “vivid scene” in prose are not dropped. Includes `vivid scenes`, `pretend that you are`, `walk a mile in the paws`, `describe an original anime`, sports-drill prompts, and compose-a-symphony tasks. Do not add topic words like `wildlife sanctuary` alone.

## Where to put a new pattern

Pick the existing function. Do not add a new function unless none of these fit.

| Leftover looks like | Put the regex in |
|---------------------|------------------|
| LaTeX, `$...$`, integrals, `dΦ/dt`, `(mv)/dt`, `b = -5` | `clean_math_texts` |
| Factorials, `1/2`, `(x+y)`, `4 * [[EQUATION]]` | `clean_bare_expressions` |
| Greek letters, `f(x)`, `√`, `±`, `m/s²`, `xn+1`, `[[EQUATION]]²` | `clean_residual_math_noise` |
| `[[EQUATION]] + [[EQUATION]]` or `[[CODE]] returns [[CODE]]` | `merge_continuous_equations` |
| Fragment **next to an existing tag**: trig, `= 0`, `2a`, `x + c`, `Mass (m) =` | `mop_up_leftover_math_and_code` |
| `num = -1` next to code / Iteration | `clean_code_assignments` |
| Markdown fences / backticks | `clean_code_texts` |
| Unfenced `def`, `class {}`, `obj.method()`, `[Car] |-- [Dashboard]` | `clean_pseudocode_and_diagrams` |

After adding mop-up or merge patterns, keep the **final merge pass** in `clean_pipeline`.

## Hard rules

1. **Math context for trig.** Use `TRIG_PATTERN` only next to tags, `(`, `=`, Greek, or digits (`cosθ`, `sin30°`). Never wipe English `sin` / `tan` / `sec`.
2. **Do not over-match prose.** `2a` / `4ac` / `f1` only when next to a tag or in a math list. Do not eat `F1 score`.
3. **Merge connectors stay explicit.** Operators, numbers, trig, derivatives, `2a`/`4ac`/`-b`/`bx`/`ac`, unicode superscripts, `kg`/`m/s` for EQUATION; operators + `return`/`returns` for CODE. Do not go back to a generic "non-prose connector".
4. **Both sides of `=`.** `[[EQUATION]] = 0`, `[[EQUATION]] = -N dPhi/dt`, and the left-hand variable all become one `[[EQUATION]]`.
5. **Code stays `[[CODE]]`.** Assignments next to code, `return` tails, and CODE/EQUATION/CODE sandwiches merge into `[[CODE]]`. Short math `b = -5` is `[[EQUATION]]`.
6. **False positives are worse than a leftover.** If a pattern would replace "passion" or "Lymphatic System", tighten it.
7. **`$...$` must be real math.** Require a backslash, `^`, `_`, operator, digit, Greek, or a 1–2 char identifier. Reject 3+ English words (currency spans like `$0.3 trillion ... $19.5`).
8. **Letter list markers** (`a.` / `b.`) only after start, newline, or `:`. Never after `+ - * / =` (`a + b. Step` must keep `b`).
9. **Algebra tails need an operator.** `[[EQUATION]] x + c` is math. Never absorb a lone letter after a tag (`[[EQUATION]] Multiplicative`).
10. **Named quantities.** `Mass (m) = 1,500 kg` and `Velocity (v) = 20 [[EQUATION]]` → `[[EQUATION]]`.

## Workflow when leftover noise shows up

1. Read [patterns.md](patterns.md). Collect real examples from `data/processed/ai/claude_dataset_cleaned.csv` (and screenshots if given). Do not invent samples.
2. Classify each example: missed math, missed code, failed merge, false-positive tag on prose, or non-academic row.
3. Add the smallest regex in the function from the table above. Reuse `TRIG_PATTERN`, `GREEK_CHARS`, and existing mop-up atoms.
4. Verify on those exact strings first, then `clean_claude_dataset(..., sample_size=200)`, then full re-run if the user wants it.
5. Count the target leftovers before vs after (see [patterns.md](patterns.md)). Success = those counts drop, and English prose is still intact.
6. Update `docs/TEXT_CLEANING_API.md` only if you added a function or changed pipeline order.

Use the venv with `langdetect`. Insert `src` on `sys.path` when importing `utils.cleaning`. Set `PYTHONIOENCODING=utf-8` on Windows when printing snippets.

## Do not

- Edit cleaning logic in `data_cleaning.ipynb` — import from `utils.cleaning`
- Rearrange `clean_pipeline` steps
- Merge a lone `[[CODE]]` with a lone `[[EQUATION]]` (sandwich of CODE/EQUATION/CODE is the exception)
- Drop rows to hide leftovers; fix the regex
- Broaden `is_non_prose` merge logic
- Claim the CSV is clean without counting patterns on the actual file
