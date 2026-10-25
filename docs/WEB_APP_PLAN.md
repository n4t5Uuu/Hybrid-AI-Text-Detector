# Web app plan: AI-text detector UI with a FastAPI backend

## Goal

A page in the style of public AI detectors. You paste a text and it says how likely it is to be AI-generated, using the study's trained hybrid model (spaCy + ELECTRA + XGBoost).

## Why FastAPI

The detector is Python: `clean_pipeline` → `strip_placeholders` → spaCy features + ELECTRA embedding → fused vector → `xgb_hybrid.json`. The Next.js page can't run that by itself, so a small Python service sits between them. FastAPI fits well:

- It loads spaCy, ELECTRA and the model **once at startup**, so each check takes about a second, even on CPU.
- It validates inputs with pydantic and generates a test page at `/docs`, which is handy for demos.
- It is already in `requirements.txt`.

Flask would also work. Calling Python from a Next.js API route would be slower and more fragile.

## Current state

- `src/app/` (Next.js 16) is still the untouched create-next-app starter.
- There is no backend code yet. The pipeline pieces already exist in `src/utils/`:
  - `clean_pipeline` (`cleaning/cleaning_methods.py`);
  - `strip_placeholders` and `count_words` (`text_prep.py`);
  - `load_spacy_nlp` and `extract_spacy_matrix` (`features/spacy_features.py`);
  - `load_electra` and `extract_electra_embeddings` (`features/electra_features.py`);
  - `fuse_spacy_electra` (`features/late_fusion.py`).
- The trained model is `data/processed/models/xgb_hybrid.json`.

## Architecture

```
Browser (Next.js page)  --POST /api/detect-->  Next.js rewrite  -->  FastAPI :8000
                                                                       |
     clean_pipeline -> strip_placeholders -> spaCy S + ELECTRA E -> H = [S | E] -> xgb_hybrid.json
                                                                       |
                       <-- { ai_probability, label, band, passages, ... } --
```

## Steps

### 1. Backend: new `src/api/`

**`src/api/detector.py`.** A `Detector` class is built once at startup.

- It loads `load_spacy_nlp`, `load_electra` and `xgb_hybrid.json`. It uses the GPU if there is one; otherwise CPU.
- `predict(text)` mirrors training exactly:
  1. Run `clean_pipeline(text)`, then `strip_placeholders`.
  2. Split into passages, since the model was trained on passages capped at 520 words.
  3. For each passage, compute S and E with the existing functions and fuse them with `fuse_spacy_electra`.
  4. Run `predict_proba` per passage, then combine the passages into one score with a mean weighted by word count.
- Reusing the training functions is what keeps the scores valid.

**`src/api/main.py`:**

- `POST /detect` takes `{ "text": "..." }` and returns:
  - `ai_probability`, from 0 to 100;
  - `label`: AI when the probability is 50% or more (the same 0.50 threshold as Table 6), otherwise Human;
  - `band`, from Table 4 of the paper: 0–20 Likely Human, 21–79 Possible AI Assistance / Mixed, 80–100 Highly Likely AI;
  - `word_count`;
  - a score for each passage, so the UI can show which parts look AI-written.
- `GET /health` reports whether the models are loaded.
- Input limits: at least about 50 words, because short texts give unreliable scores, and at most about 5,000 words.

**Run it:**

```bash
uvicorn src.api.main:app --reload --port 8000
```

### 2. Connect the frontend

- In `next.config.ts`, add a rewrite from `/api/:path*` to `http://localhost:8000/:path*`. The browser then calls the same origin, so no CORS setup is needed.
- Following AGENTS.md, read the Next 16 docs in `node_modules/next/dist/docs/` before changing config or routes, because this version may differ from older ones.

### 3. The UI, built with Impeccable (required by CLAUDE.md)

1. Run `/impeccable init` (there is no `PRODUCT.md` yet). Product context: an academic AI-text detector for student writing.
2. Build with `/impeccable craft`, then `/impeccable critique` and `/impeccable polish`. The page:
   - **Input:** a large paste area, a live word count with the minimum enforced, **Check text** and **Clear** buttons.
   - **Result:** a large score (for example "87% AI"), the Table 4 band with matching color, and the binary verdict.
   - **Per-passage view:** the pasted text split into passages, each tinted by its score.
   - **Caveat line:** "Trained on academic English. Results are probabilities, not proof."
   - **Other states:** loading, error (including the backend being down) and too-short.
3. Replace the starter `src/app/page.tsx` and give `src/app/layout.tsx` a proper title.

### 4. Run both together

```bash
# Terminal 1: backend
uvicorn src.api.main:app --port 8000

# Terminal 2: frontend
npm run dev
```

Then open http://localhost:3000. These steps will also go in the README.

### 5. Verification

- **Known texts:** run `/detect` on rows from the test set. A BAWE passage should score low, and MGTBench or Gemini text should score high.
- **Same pipeline:** check that the API's probability for a test passage matches the notebook's `predict_proba` for that row.
- **Edge cases:** empty, too short, very long, and non-English input.
- **Screenshots:** take before and after screenshots of the page, as AGENTS.md requires for UI changes.

## Open choices

1. **Long texts:** split into passages and average them (recommended, because it matches training), or score the whole text at once. Scoring it whole is simpler, but ELECTRA cuts off at 512 tokens.
2. **Baselines in the UI:** show the hybrid only (recommended for a clean demo), or also show spaCy-only, ELECTRA-only and XGBoost-only scores side by side, which is good for the defense but busier.
