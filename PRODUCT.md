# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Educators checking a submission, students checking their own essay before submitting, and the thesis panel watching the study's model work, served equally. No single primary user. Each of them pastes one academic text and needs to know how likely it is to be fully AI-generated.

## Product Purpose

A single-page detector for the UST thesis "A Hybrid Framework for Detecting Fully AI-Generated Academic Text Using spaCy, ELECTRA, and XGBoost". The user pastes a text; the page returns an AI-generation probability, the paper's interpretation band, and a per-passage breakdown. Success means a score people can read correctly: a probability, not proof, with human-written work as rarely misflagged as possible.

## Positioning

The detector runs the study's own trained hybrid model: spaCy stylometric features plus ELECTRA semantic embeddings, fused and classified by XGBoost. It was built for academic writing, with the false positive rate (human text called AI) as the primary metric, unlike general-purpose detectors trained on web text.

## Operating Context

- Paste in, score out. The text goes to a FastAPI service (`src/api/`, exposed to the page as `/api/detect`) that loads the models once at startup.
- The Next.js 16 app in `src/app/` is the only UI.
- It is used locally and for demonstrations, such as the thesis defense.

## Capabilities and Constraints

- **Language and scope:** English academic text only, and fully AI-generated text only, not partly AI-assisted text. The model was trained on GPT-3.5 (MGTBench), Claude and Gemini outputs against human academic writing (BAWE student essays and MGTBench human originals).
- **Input limits:** at least 50 words and at most 5,000. Code, equations, citations and URLs are removed before scoring, as in training.
- **Passages:** long texts are cut into passages of about 200 words (never more than 520), the size the model was trained on. The overall score is the word-weighted mean of the passage scores, and each passage's score is shown.
- **Decision threshold:** 0.55 (agreed with the adviser). At or above it the label is "AI-generated", below it "Human-written".
- **Interpretation bands (paper, Table 4):**
  - 0–20%: Likely Human-Written
  - 21–79%: Possible AI Assistance / Mixed Content
  - 80–100%: Highly Likely AI-Generated
- **Privacy:** nothing is stored. The API keeps no copy of pasted text and writes no logs of it; the page must not either.

## Brand Commitments

- **Name:** "Penned or Prompted?". The user asked for a witty name and left the choice open; it can be renamed.
- **Origin:** a University of Santo Tomas (CICS, Department of Computer Science) thesis project.

## Evidence on Hand

- **Test-set results** (`data/processed/models/table6_performance_t050.csv`, threshold 0.50, 45,148 held-out passages):
  - Hybrid: accuracy 90.7%, ROC-AUC 0.970, FPR 9.3%.
  - FPR on BAWE student essays alone: 1.9% (`test_per_source.csv`).
- **Threshold comparisons:** 0.45 and 0.50 are in `table6_thresholds.csv`.
- **Do not claim** more than these numbers, and do not invent users, testimonials, or institutional adoption.

## Product Principles

- **A probability, not a verdict.** Always show the score and its band. Never present the result as proof of misconduct.
- **Fair to human writers.** Lowering false positives is the study's priority, and the page must not overstate certainty.
- **Show the evidence.** Per-passage scores show where the signal comes from.
- **Honest limits.** State the scope (English, academic, fully AI-generated, these generators) where the result is read.
- **Private by default.** Nothing pasted is stored.
