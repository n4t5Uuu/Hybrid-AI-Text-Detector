# Cleaning pattern catalog

What the pipeline already handles, plus leftovers still seen in `claude_dataset_cleaned.csv`. Read this when adding regex or auditing a re-clean.

## Already cleaned

### Math / physics (`[[EQUATION]]`)

- LaTeX: `\begin{...}...\end{...}`, `$$...$$`, `$...$` (math only — not `$perseverance$` or `$0.3 trillion ... $19.5`), `\[...\]`, `\(...\)`, `\[command]{...}`
- Integrals with differentials (`∫ ... dx`)
- Algebraic / comparison equations: `=`, `==`, `!=`, `<`, `>`, `≤`, `≥`, `≈`
- Short assignments: `b = -5`, `c = 2` (1–3 letter LHS)
- Exponents `x^2`, `[[EQUATION]]^2`, unicode `[[EQUATION]]²`, `v²`
- Derivatives `dΦ/dt`, `(mv)/dt`, `d(mv)/dt`, `d<greek-or-letter>/d<letter>`
- Combinatorics `(n choose k)`
- Factorials `n!`, `(n-1)!`
- Fractions `1/2`, parenthesized math `(x+y)`, implicit `(x+y)(x-y)`
- Function calls `f(x)`, absolute values `|x|`, square roots `√`
- Unicode: Greek (`Σ∂Φφθ...`), `∞`, `±`, superscripts `²`, vulgar fractions `½`
- Units with exponents `m/s²`
- Subscripts `xn+1`, `x0`, unicode subscripts on tags
- Trig in math context: `sin`, `cos`, `tan`, `sec`, `csc`, `cot`, hyperbolic and inverse forms; glued `cosθ`, `sin30°`
- Faraday-style `-N dPhi/dt`
- Both sides of equals: `[[EQUATION]] = 0`, `[[EQUATION]] = 0.03`, short LHS variables
- Algebra next to tags: `2a`, `4ac`, `-b`, `b/2a`, `[[EQUATION]] x + c`, `[[EQUATION]] + bx = -c`
- Named quantities: `Mass (m) = 1,500 kg`, `Velocity (v) = 20 [[EQUATION]]`
- Coordinate tuples `(xn, yn, zn)`
- Indexed math lists `f1, f2, f3` (not `F1 score`)
- Unit products `30 cm × 20 cm`, `cm × 30 cm × 20 [[EQUATION]]`
- `[[EQUATION]] / 2`, `[[EQUATION]] ,000 J`
- Fragment-heavy sentences collapsed to one tag

### Merge

- `[[EQUATION]] + [[EQUATION]]` (also `-`, `*`, `/`, `×`, `÷`, `=`, `±`)
- Connectors: numbers, trig names, `dGreek/dt`, `2a` / `4ac` / `-b` / `bx` / `ac`, unicode superscripts, `kg` / `m/s`, `-N`
- `[[CODE]] + [[CODE]]`, `[[CODE]] returns [[CODE]]`
- Sandwich `[[CODE]] [[EQUATION]] [[CODE]]` → `[[CODE]]`

### Code (`[[CODE]]`)

- Markdown fences ` ```...``` ` and inline `` `code` ``
- `[Start] -> [End]` and 2-node trees `[Car] |-- [Dashboard]` (connector must include `| - > /`)
- `[Dashboard] [[EQUATION]] -- Fuel Gauge`
- `class Foo {}`, curly-brace blocks
- `obj.method()`, `def name(...):`, `return ...`
- Named calls `factorial(5)`
- Keywords: `public` / `void` / `int` / `const` / `let` / `var` / `function` ending in `;` or `{`
- Assignments next to code: `num = -1`, `Iteration 1: x = 0, condition false`
- `initialized to 5` → `initialized to [[CODE]]`

### Other tags

- Complexity: `O(n)`, `O(log n)`, `Θ(...)`, `Ω(...)` (not lowercase `o`, not `info(x)`)
- Citations: `[1]`, `(Smith, 2020)`, `Smith et al. (2020)`
- URLs: `http(s)://`, `www.`
- Music: `C-G-D-A`, `F#-Bb-D`
- List markers: `1.`, `a)` / `b.` only after start, newline, or `: ` (not after `a + b. Step`)
- Trailing `References:` / `Bibliography:` / `Sources:` cut off
- Non-academic creative prompts dropped (`is_academic_content` on **prompt only**) — includes `vivid scenes`, `in vivid detail`, `explore the senses`, `run with passion`, `pretend that you are`
- Foreign-language rows dropped (`contains_foreign_language`; loanwords like café kept)

## Verification counts

These should stay at **0** after a re-clean.

| Pattern | Target |
|---------|--------|
| `[[EQUATION]] + [[EQUATION]]` (any `+ - * / ×`) | 0 |
| `[[EQUATION]] = 0` | 0 |
| `[[CODE]] / [[CODE]]` (any operator) | 0 |
| `num = -1` next to code | 0 |
| `dPhi/dt` / Faraday derivative leftovers | 0 |
| `(xn, yn, zn)` | 0 |
| `[[EQUATION]]²` / `[[EQUATION]] ²` | 0 |
| `(mv)/dt` | 0 |
| `Mass (m) =` leftover | 0 |
| `[[EQUATION]] x + c` | 0 |
| `b = -5` leftover | 0 |
| `[Car] |-- [Dashboard]` | 0 |

Re-check on the actual CSV after every regex change. Do not trust a plausible diff.

Prompts that must be **dropped** (not cleaned):
- `Run with passion as you compete...`
- `Explore the senses, thoughts, and experiences of an elderly elephant...`
- `Gently describe the typical day in the life of an elderly elephant...`

## Quick test snippets

Run these through `clean_pipeline` after a change. Expected: one tag, surrounding English kept.

```
[[EQUATION]] + [[EQUATION]] + [[EQUATION]]
[[EQUATION]] = 0
[[EQUATION]] = -N dPhi/dt
[[EQUATION]] ² / 2
(mv)/dt
Mass (m) = 1,500 kg
Velocity (v) = 20 [[EQUATION]]
[[EQUATION]] x + c
a [[EQUATION]] b + ac
[[EQUATION]] + bx = -c
b = -5
cosθ  sin30°  tan [[EQUATION]]
2a  4ac  (xn, yn, zn)  f1, f2, f3
30 cm × 20 cm × 10 [[EQUATION]]
num = -1
[[CODE]] - [[CODE]]
[[CODE]] returns [[CODE]]
[[CODE]] [[EQUATION]] [[CODE]]
[Car] |-- [Dashboard]
a + b. Step 2
```

Must **not** become tags:

```
sin (as in "original sin")
tan (as in "tan leather")
F1 score
passion and perseverance
Lymphatic System
Multiplicative inverse
```

`$perseverance$` and `$0.3 trillion in 1970 to $19.5` must not become `[[EQUATION]]`.
